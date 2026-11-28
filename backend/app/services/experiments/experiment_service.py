"""Service implementing Flagsmith experimentation workflows.

Handles participant variant assignment, scenario evaluation, duplicate protection,
and verifiable metric event tracking.

Event-ordering guarantee:
    Local submission persistence and local metric-event persistence are performed
    atomically inside save_submission_atomic. Flagsmith events are forwarded only
    after the repository confirms the submission is newly accepted (is_new=True).
    Duplicate submissions (is_new=False) never forward events to Flagsmith.
"""

from datetime import datetime, timezone
from typing import Optional, Any
import logging
import uuid

from backend.app.schemas.experiments import (
    ExperimentAssignRequest,
    ExperimentAssignResponse,
    ExperimentScenarioResponse,
    ExperimentSubmitRequest,
    ExperimentSubmitResponse,
    ExperimentStatusResponse,
)
from backend.app.repositories.interfaces.experiment_repo import ExperimentRepositoryInterface
from backend.app.repositories.interfaces.scenario_validator import ScenarioValidatorInterface
from backend.app.integrations.flagsmith.client import (
    FlagsmithIntegrationService,
    EXPERIMENT_FEATURE_NAME,
    DEFAULT_EXPERIMENT_NAME,
)

logger = logging.getLogger("paypause.experiment_service")


def _build_scoped_key(participant_id: str, scenario_id: str, raw_key: str) -> str:
    """Compose an idempotency key scoped to participant + scenario + raw key.

    This prevents two different participants who happen to supply the same
    raw idempotency key string from ever retrieving each other's submission.
    """
    return f"{participant_id}|{scenario_id}|{raw_key}"


class ExperimentService:
    """Core experimentation business logic."""

    def __init__(
        self,
        experiment_repo: ExperimentRepositoryInterface,
        scenario_validator: ScenarioValidatorInterface,
        flagsmith_service: FlagsmithIntegrationService,
    ) -> None:
        self.experiment_repo = experiment_repo
        self.scenario_validator = scenario_validator
        self.flagsmith_service = flagsmith_service

    # ------------------------------------------------------------------
    # Assignment
    # ------------------------------------------------------------------

    def assign_participant(self, req: ExperimentAssignRequest) -> ExperimentAssignResponse:
        """Assign or retrieve a stable experiment variant for the participant.

        Assignment identity is (participant_id, experiment_name, feature_name).
        A cached assignment is only reused when all three values match, ensuring
        a request with a different feature_name is not silently served a cached
        assignment that was evaluated for a different feature.
        """
        participant_id = req.participant_id.strip()
        experiment_name = req.experiment_name or DEFAULT_EXPERIMENT_NAME
        feature_name = req.feature_name or EXPERIMENT_FEATURE_NAME

        # 1. Check existing assignment — must match all three identity fields
        existing = self.experiment_repo.get_assignment(participant_id, experiment_name)
        if existing and existing.get("feature_name") == feature_name:
            return ExperimentAssignResponse(
                participant_id=participant_id,
                experiment_name=experiment_name,
                feature_name=feature_name,
                variant=existing["variant"],
                source=existing.get("source", "cached_assignment"),
                is_live_flagsmith=existing.get("source") == "flagsmith_real",
                assigned_at=existing.get("assigned_at", datetime.now(timezone.utc).isoformat()),
                error=existing.get("error"),
            )

        # 2. Evaluate with Flagsmith (or deterministic fallback)
        eval_result = self.flagsmith_service.get_variant_for_identity(
            identifier=participant_id,
            feature_name=feature_name,
            traits=req.traits,
        )

        assignment_data = {
            "participant_id": participant_id,
            "experiment_name": experiment_name,
            "feature_name": feature_name,
            "variant": eval_result["variant"],
            "source": eval_result["source"],
            "error": eval_result.get("error"),
            "assigned_at": datetime.now(timezone.utc).isoformat(),
        }

        # 3. Persist assignment
        saved = self.experiment_repo.save_assignment(assignment_data)

        return ExperimentAssignResponse(
            participant_id=participant_id,
            experiment_name=experiment_name,
            feature_name=feature_name,
            variant=saved["variant"],
            source=saved["source"],
            is_live_flagsmith=saved["source"] == "flagsmith_real",
            assigned_at=saved["assigned_at"],
            error=saved.get("error"),
        )

    # ------------------------------------------------------------------
    # Public scenarios
    # ------------------------------------------------------------------

    def get_public_scenarios(self) -> list[ExperimentScenarioResponse]:
        """Retrieve all experiment scenarios without canonical answer keys."""
        raw_scenarios = self.scenario_validator.get_public_scenarios()
        return [ExperimentScenarioResponse(**s) for s in raw_scenarios]

    # ------------------------------------------------------------------
    # Submission
    # ------------------------------------------------------------------

    def submit_scenario_attempt(
        self, req: ExperimentSubmitRequest
    ) -> ExperimentSubmitResponse:
        """Process an experiment scenario submission.

        Idempotency is scoped to (participant_id, scenario_id, raw_key) so
        different participants using the same raw key cannot see each other's
        results, and incompatible payloads cannot silently reuse a cached result
        for a different scenario.

        Local submission persistence and local event persistence are atomic
        (single lock acquisition inside save_submission_atomic). Flagsmith
        events are forwarded only after the repository confirms is_new=True.
        """
        participant_id = req.participant_id.strip()
        scenario_id = req.scenario_id.strip()

        # Build raw idempotency key (default: participant + scenario)
        raw_key = (
            req.idempotency_key.strip()
            if req.idempotency_key and req.idempotency_key.strip()
            else f"{participant_id}_{scenario_id}"
        )
        scoped_key = _build_scoped_key(participant_id, scenario_id, raw_key)

        # 1. Retrieve variant (stable assignment)
        assign_res = self.assign_participant(
            ExperimentAssignRequest(participant_id=participant_id)
        )
        variant = assign_res.variant

        submitted_at = datetime.now(timezone.utc).isoformat()
        submission_id = f"subm_{uuid.uuid4().hex[:12]}"

        # 2. Build submission record and events list (not yet persisted)
        if req.abandoned:
            subm_data = {
                "id": submission_id,
                "scoped_key": scoped_key,
                "participant_id": participant_id,
                "scenario_id": scenario_id,
                "experiment_name": DEFAULT_EXPERIMENT_NAME,
                "variant": variant,
                "selected_answer": req.selected_answer,
                "selected_action": req.selected_action,
                "is_correct": False,
                "score": 0.0,
                "feedback": "Scenario verification was abandoned prior to completion.",
                "submitted_at": submitted_at,
                "start_timestamp": req.start_timestamp,
            }
            pending_events = [
                self._build_event(
                    event_name="verification_abandoned",
                    participant_id=participant_id,
                    variant=variant,
                    scenario_id=scenario_id,
                    submission_id=submission_id,
                )
            ]
        else:
            # 3. Canonical backend validation
            val_result = self.scenario_validator.validate_answer(
                scenario_id=scenario_id,
                selected_answer=req.selected_answer,
                selected_action=req.selected_action,
            )

            # 4. Build ordered list of events to persist
            pending_events: list[dict[str, Any]] = []
            if val_result.risk_signal_identified:
                pending_events.append(
                    self._build_event("risk_signal_understood", participant_id, variant, scenario_id, submission_id)
                )
            if val_result.appropriate_action_selected:
                pending_events.append(
                    self._build_event("verification_action_selected", participant_id, variant, scenario_id, submission_id)
                )
            if val_result.is_correct:
                pending_events.append(
                    self._build_event("risk_check_correctly_completed", participant_id, variant, scenario_id, submission_id, value=1.0)
                )

            subm_data = {
                "id": submission_id,
                "scoped_key": scoped_key,
                "participant_id": participant_id,
                "scenario_id": scenario_id,
                "experiment_name": DEFAULT_EXPERIMENT_NAME,
                "variant": variant,
                "selected_answer": req.selected_answer,
                "selected_action": req.selected_action,
                "is_correct": val_result.is_correct,
                "score": val_result.score,
                "feedback": val_result.feedback,
                "submitted_at": submitted_at,
                "start_timestamp": req.start_timestamp,
                "details": val_result.details,
            }

        # 5. Atomic persist: submission + events in a single lock acquisition.
        #    If the scoped key already exists, nothing is written and is_new=False.
        result = self.experiment_repo.save_submission_atomic(
            scoped_key=scoped_key,
            submission_data=subm_data,
            events=pending_events,
        )

        if not result.is_new:
            # Duplicate: return cached result, zero events, do NOT forward to Flagsmith
            existing = result.submission
            return ExperimentSubmitResponse(
                submission_id=existing["id"],
                participant_id=existing["participant_id"],
                scenario_id=existing["scenario_id"],
                variant=existing["variant"],
                is_correct=existing["is_correct"],
                score=existing["score"],
                feedback=existing["feedback"],
                is_duplicate=True,
                events_recorded=[],
                submitted_at=existing["submitted_at"],
            )

        # 6. Submission was newly accepted — forward events to Flagsmith
        events_emitted = [ev["metric_name"] for ev in result.events]
        for ev in result.events:
            self._forward_event_to_flagsmith(
                event_name=ev["metric_name"],
                participant_id=participant_id,
                variant=variant,
                scenario_id=scenario_id,
                value=ev.get("value"),
            )

        return ExperimentSubmitResponse(
            submission_id=result.submission["id"],
            participant_id=participant_id,
            scenario_id=scenario_id,
            variant=variant,
            is_correct=result.submission["is_correct"],
            score=result.submission["score"],
            feedback=result.submission["feedback"],
            is_duplicate=False,
            events_recorded=events_emitted,
            submitted_at=result.submission["submitted_at"],
        )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_experiment_status(self) -> ExperimentStatusResponse:
        """Return aggregated stats and recorded metrics for the experiment."""
        stats = self.experiment_repo.get_experiment_stats(DEFAULT_EXPERIMENT_NAME)
        return ExperimentStatusResponse(
            experiment_name=DEFAULT_EXPERIMENT_NAME,
            feature_name=EXPERIMENT_FEATURE_NAME,
            is_flagsmith_configured=self.flagsmith_service.is_configured,
            total_assignments=stats.get("total_assignments", 0),
            total_submissions=stats.get("total_submissions", 0),
            variant_stats=stats.get("variants", {}),
            event_counts=stats.get("event_metrics", {}),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_event(
        self,
        event_name: str,
        participant_id: str,
        variant: str,
        scenario_id: str,
        submission_id: str,
        value: Optional[float] = None,
    ) -> dict[str, Any]:
        """Build an event record dict ready for atomic persistence."""
        return {
            "metric_name": event_name,
            "experiment_name": DEFAULT_EXPERIMENT_NAME,
            "participant_id": participant_id,
            "variant": variant,
            "scenario_id": scenario_id,
            "submission_id": submission_id,
            "value": value,
        }

    def _forward_event_to_flagsmith(
        self,
        event_name: str,
        participant_id: str,
        variant: str,
        scenario_id: str,
        value: Optional[float] = None,
    ) -> None:
        """Forward a confirmed new event to Flagsmith (best-effort, never raises)."""
        try:
            self.flagsmith_service.track_experiment_event(
                event_name=event_name,
                identifier=participant_id,
                value=value,
                metadata={"variant": variant, "scenario_id": scenario_id},
            )
        except Exception as exc:
            logger.warning(
                "Failed to forward event '%s' to Flagsmith for participant '%s': %s",
                event_name, participant_id, exc,
            )
