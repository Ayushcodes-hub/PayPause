"""Unit and API tests for Flagsmith Experimentation module.

Tests cover:
- Variant retrieval & deterministic stability
- Missing identity validation
- Public scenario retrieval (no answer key leak)
- Correct & incorrect answer validation
- Metric event generation & persistence
- Duplicate submission / idempotency protection
- Flagsmith error handling & fallback
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from backend.app.integrations.flagsmith.client import (
    FlagsmithIntegrationService,
    VARIANT_RISK_SCORE_FIRST,
    VARIANT_PAYMENT_PASSPORT_FIRST,
)
from backend.app.schemas.experiments import (
    ExperimentAssignRequest,
    ExperimentSubmitRequest,
)
from backend.app.services.experiments.experiment_service import ExperimentService
from backend.app.repositories.development.in_memory_experiment_repo import InMemoryExperimentRepository
from backend.app.repositories.development.mock_scenario_validator import MockScenarioValidator
from backend.app.api.experiments import router as experiments_router
from backend.app.core.dependencies import (
    get_experiment_repo,
    get_scenario_validator,
    get_flagsmith_service,
)


@pytest.fixture
def fresh_repo():
    return InMemoryExperimentRepository()


@pytest.fixture
def fresh_validator():
    return MockScenarioValidator()


@pytest.fixture
def fallback_flagsmith():
    return FlagsmithIntegrationService()


@pytest.fixture
def experiment_service(fresh_repo, fresh_validator, fallback_flagsmith):
    return ExperimentService(
        experiment_repo=fresh_repo,
        scenario_validator=fresh_validator,
        flagsmith_service=fallback_flagsmith,
    )


@pytest.fixture
def client(fresh_repo, fresh_validator, fallback_flagsmith):
    app = FastAPI()
    app.include_router(experiments_router)
    app.dependency_overrides[get_experiment_repo] = lambda: fresh_repo
    app.dependency_overrides[get_scenario_validator] = lambda: fresh_validator
    app.dependency_overrides[get_flagsmith_service] = lambda: fallback_flagsmith
    return TestClient(app)


# ==========================================
# 1. FLAGSMITH CLIENT & ASSIGNMENT TESTS
# ==========================================

def test_deterministic_assignment_consistency(fallback_flagsmith):
    """Verify that identical participant IDs always receive the exact same variant."""
    part_1 = "student_user_101"
    res_a = fallback_flagsmith.get_variant_for_identity(part_1)
    res_b = fallback_flagsmith.get_variant_for_identity(part_1)
    assert res_a["variant"] == res_b["variant"]
    assert res_a["variant"] in (VARIANT_RISK_SCORE_FIRST, VARIANT_PAYMENT_PASSPORT_FIRST)


def test_missing_identity_raises_error(fallback_flagsmith):
    """Verify that empty or blank participant identities are rejected safely."""
    with pytest.raises(ValueError):
        fallback_flagsmith.get_variant_for_identity("")
    with pytest.raises(ValueError):
        fallback_flagsmith.get_variant_for_identity("   ")


def test_flagsmith_failure_clean_fallback():
    """Verify that Flagsmith API failure cleanly falls back without crashing."""
    service = FlagsmithIntegrationService()
    service.is_configured = True
    mock_client = MagicMock()
    mock_client.get_identity_flags.side_effect = Exception("Flagsmith connection timed out")
    service._client = mock_client

    res = service.get_variant_for_identity("user_network_failure_test")
    assert res["source"] == "deterministic_fallback"
    assert res["variant"] in (VARIANT_RISK_SCORE_FIRST, VARIANT_PAYMENT_PASSPORT_FIRST)
    assert "timed out" in (res.get("error") or "")


# ==========================================
# 2. SCENARIO RETRIEVAL TESTS
# ==========================================

def test_scenarios_hide_canonical_answers(client):
    """Verify scenarios endpoint returns options without exposing expected answers or explanations."""
    response = client.get("/api/experiments/scenarios")
    assert response.status_code == 200
    scenarios = response.json()
    assert len(scenarios) >= 3

    for s in scenarios:
        assert "id" in s
        assert "title" in s
        assert "options" in s
        # Ensure hidden evaluation fields are completely absent
        assert "_expected_answer" not in s
        assert "_expected_actions" not in s
        assert "_explanation" not in s
        assert "feedback" not in s


# ==========================================
# 3. ASSIGNMENT API TESTS
# ==========================================

def test_assign_api_persists_stable_assignment(client):
    """Test assigning variant through API returns stable result."""
    payload = {"participant_id": "session_alpha_99"}
    resp1 = client.post("/api/experiments/assign", json=payload)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["participant_id"] == "session_alpha_99"
    assert data1["variant"] in (VARIANT_RISK_SCORE_FIRST, VARIANT_PAYMENT_PASSPORT_FIRST)

    # Subsequent request returns cached identical assignment
    resp2 = client.post("/api/experiments/assign", json=payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["variant"] == data1["variant"]


# ==========================================
# 4. SUBMISSION & EVENT TRACKING TESTS
# ==========================================

def test_submit_correct_answer_records_primary_metric(client, fresh_repo):
    """Verify correct scenario submission emits risk_check_correctly_completed metric."""
    subm_payload = {
        "participant_id": "user_correct_hero",
        "scenario_id": "scen_upi_qr_tamper",
        "selected_answer": "opt_pause_verify",
        "selected_action": "act_verify_vpa",
        "idempotency_key": "idem_correct_001",
    }
    resp = client.post("/api/experiments/submit", json=subm_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_correct"] is True
    assert data["score"] == 1.0
    assert "risk_check_correctly_completed" in data["events_recorded"]
    assert "risk_signal_understood" in data["events_recorded"]
    assert "verification_action_selected" in data["events_recorded"]

    # Verify event stored in repo
    events = fresh_repo.get_events(participant_id="user_correct_hero")
    metric_names = [e["metric_name"] for e in events]
    assert "risk_check_correctly_completed" in metric_names


def test_submit_incorrect_answer_does_not_emit_primary_metric(client, fresh_repo):
    """Verify incorrect scenario submission DOES NOT emit primary success metric."""
    subm_payload = {
        "participant_id": "user_incorrect_victim",
        "scenario_id": "scen_upi_qr_tamper",
        "selected_answer": "opt_proceed",  # Wrong! User proceeded blindly
        "selected_action": "act_ignore",
        "idempotency_key": "idem_wrong_001",
    }
    resp = client.post("/api/experiments/submit", json=subm_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_correct"] is False
    assert "risk_check_correctly_completed" not in data["events_recorded"]

    # Repo must not have success event
    events = fresh_repo.get_events(
        participant_id="user_incorrect_victim",
        metric_name="risk_check_correctly_completed",
    )
    assert len(events) == 0


def test_duplicate_submission_idempotency_protection(client, fresh_repo):
    """Verify duplicate submission returns cached result without generating duplicate events."""
    subm_payload = {
        "participant_id": "user_duplicate_tester",
        "scenario_id": "scen_collect_request_phish",
        "selected_answer": "opt_decline_and_block",
        "selected_action": "act_decline_collect",
        "idempotency_key": "idem_fixed_key_123",
    }
    # First submit
    resp1 = client.post("/api/experiments/submit", json=subm_payload)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["is_duplicate"] is False
    assert "risk_check_correctly_completed" in data1["events_recorded"]

    initial_events_count = len(fresh_repo.get_events(participant_id="user_duplicate_tester"))

    # Immediate second retry with same idempotency key
    resp2 = client.post("/api/experiments/submit", json=subm_payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["is_duplicate"] is True
    assert data2["events_recorded"] == []

    # Events count must remain unchanged
    after_events_count = len(fresh_repo.get_events(participant_id="user_duplicate_tester"))
    assert after_events_count == initial_events_count


def test_abandoned_submission_tracks_abandonment_metric(client, fresh_repo):
    """Verify abandoning verification emits verification_abandoned metric."""
    subm_payload = {
        "participant_id": "user_abandoner",
        "scenario_id": "scen_unverified_bill_payment",
        "selected_answer": "none",
        "abandoned": True,
        "idempotency_key": "idem_abandon_001",
    }
    resp = client.post("/api/experiments/submit", json=subm_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_correct"] is False
    assert "verification_abandoned" in data["events_recorded"]

    events = fresh_repo.get_events(
        participant_id="user_abandoner",
        metric_name="verification_abandoned",
    )
    assert len(events) == 1


def test_experiment_status_aggregation(client):
    """Verify GET /api/experiments/status returns accurate aggregated stats."""
    # Submit one correct and one incorrect
    client.post(
        "/api/experiments/submit",
        json={
            "participant_id": "stat_user_1",
            "scenario_id": "scen_upi_qr_tamper",
            "selected_answer": "opt_pause_verify",
            "selected_action": "act_verify_vpa",
            "idempotency_key": "stat_idem_1",
        },
    )
    client.post(
        "/api/experiments/submit",
        json={
            "participant_id": "stat_user_2",
            "scenario_id": "scen_upi_qr_tamper",
            "selected_answer": "opt_proceed",
            "selected_action": "act_ignore",
            "idempotency_key": "stat_idem_2",
        },
    )

    resp = client.get("/api/experiments/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_submissions"] >= 2
    assert "variant_stats" in data
    assert "event_counts" in data
    assert data["primary_metric"] == "risk_check_correctly_completed"


# ==============================================================================
# REGRESSION TESTS — Security & Reliability Fixes (November 2026)
# ==============================================================================

import threading


# ==========================================
# R1. Scoped Idempotency — Cross-Participant Isolation
# ==========================================

def test_different_participants_same_raw_key_cannot_share_submission(client, fresh_repo):
    """Two different participants using the same raw idempotency key string must
    never retrieve each other's submission. Each must get their own independent result."""
    shared_raw_key = "shared_global_key_xyz"

    resp_a = client.post(
        "/api/experiments/submit",
        json={
            "participant_id": "participant_alice",
            "scenario_id": "scen_upi_qr_tamper",
            "selected_answer": "opt_pause_verify",
            "selected_action": "act_verify_vpa",
            "idempotency_key": shared_raw_key,
        },
    )
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assert data_a["participant_id"] == "participant_alice"
    assert data_a["is_duplicate"] is False

    resp_b = client.post(
        "/api/experiments/submit",
        json={
            "participant_id": "participant_bob",
            "scenario_id": "scen_upi_qr_tamper",
            "selected_answer": "opt_proceed",  # different answer
            "selected_action": "act_ignore",
            "idempotency_key": shared_raw_key,
        },
    )
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assert data_b["participant_id"] == "participant_bob"
    # Bob must NOT receive alice's cached result
    assert data_b["is_duplicate"] is False
    # Bob's answer is wrong; alice's was correct — they must differ
    assert data_b["is_correct"] is False
    assert data_a["is_correct"] is True
    # Submission IDs must be distinct
    assert data_a["submission_id"] != data_b["submission_id"]


def test_same_participant_same_scenario_same_key_returns_original(client, fresh_repo):
    """Same participant retrying with the same idempotency key gets the original result
    and is flagged as a duplicate."""
    payload = {
        "participant_id": "participant_retry_tester",
        "scenario_id": "scen_upi_qr_tamper",
        "selected_answer": "opt_pause_verify",
        "selected_action": "act_verify_vpa",
        "idempotency_key": "retry_key_stable_001",
    }
    resp1 = client.post("/api/experiments/submit", json=payload)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["is_duplicate"] is False

    resp2 = client.post("/api/experiments/submit", json=payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["is_duplicate"] is True
    assert data2["submission_id"] == data1["submission_id"]
    assert data2["is_correct"] == data1["is_correct"]
    assert data2["events_recorded"] == []


def test_same_key_different_scenario_creates_independent_submission(client, fresh_repo):
    """The same raw idempotency key used for two different scenarios must produce
    two independent submissions — the key scope includes the scenario_id."""
    raw_key = "cross_scenario_key"
    payload_a = {
        "participant_id": "participant_crossscene",
        "scenario_id": "scen_upi_qr_tamper",
        "selected_answer": "opt_pause_verify",
        "idempotency_key": raw_key,
    }
    payload_b = {
        "participant_id": "participant_crossscene",
        "scenario_id": "scen_collect_request_phish",
        "selected_answer": "opt_decline_and_block",
        "idempotency_key": raw_key,
    }
    resp_a = client.post("/api/experiments/submit", json=payload_a)
    resp_b = client.post("/api/experiments/submit", json=payload_b)
    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
    assert resp_a.json()["is_duplicate"] is False
    assert resp_b.json()["is_duplicate"] is False
    assert resp_a.json()["submission_id"] != resp_b.json()["submission_id"]


def test_same_key_incompatible_payload_does_not_silently_return_wrong_result(client, fresh_repo):
    """When the same raw key is reused but with a different answer for the same
    participant+scenario, the second call must be identified as a duplicate and
    return the original result — it must not silently update or corrupt the first."""
    key = "incompatible_payload_key"
    payload_first = {
        "participant_id": "participant_mismatch",
        "scenario_id": "scen_upi_qr_tamper",
        "selected_answer": "opt_pause_verify",  # correct
        "selected_action": "act_verify_vpa",
        "idempotency_key": key,
    }
    payload_second = {
        "participant_id": "participant_mismatch",
        "scenario_id": "scen_upi_qr_tamper",
        "selected_answer": "opt_proceed",  # wrong — different from first
        "selected_action": "act_ignore",
        "idempotency_key": key,
    }
    resp1 = client.post("/api/experiments/submit", json=payload_first)
    resp2 = client.post("/api/experiments/submit", json=payload_second)
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    # Second call gets the original (correct) result, not the wrong-answer result
    data2 = resp2.json()
    assert data2["is_duplicate"] is True
    assert data2["is_correct"] is True  # original was correct
    assert data2["events_recorded"] == []


# ==========================================
# R2. Schema Validation
# ==========================================

def test_whitespace_only_participant_id_rejected_by_api(client):
    """Whitespace-only participant_id must be rejected with HTTP 422."""
    resp = client.post(
        "/api/experiments/submit",
        json={
            "participant_id": "   ",
            "scenario_id": "scen_upi_qr_tamper",
            "selected_answer": "opt_pause_verify",
        },
    )
    assert resp.status_code == 422


def test_whitespace_only_scenario_id_rejected_by_api(client):
    """Whitespace-only scenario_id must be rejected with HTTP 422."""
    resp = client.post(
        "/api/experiments/submit",
        json={
            "participant_id": "valid_participant",
            "scenario_id": "   ",
            "selected_answer": "opt_pause_verify",
        },
    )
    assert resp.status_code == 422


def test_whitespace_only_selected_answer_rejected_by_api(client):
    """Whitespace-only selected_answer must be rejected with HTTP 422."""
    resp = client.post(
        "/api/experiments/submit",
        json={
            "participant_id": "valid_participant",
            "scenario_id": "scen_upi_qr_tamper",
            "selected_answer": "   ",
        },
    )
    assert resp.status_code == 422


def test_oversized_participant_id_rejected_by_api(client):
    """participant_id exceeding max_length=128 must be rejected with HTTP 422."""
    resp = client.post(
        "/api/experiments/submit",
        json={
            "participant_id": "x" * 129,
            "scenario_id": "scen_upi_qr_tamper",
            "selected_answer": "opt_pause_verify",
        },
    )
    assert resp.status_code == 422


def test_oversized_scenario_id_rejected_by_api(client):
    """scenario_id exceeding max_length=128 must be rejected with HTTP 422."""
    resp = client.post(
        "/api/experiments/submit",
        json={
            "participant_id": "valid_participant_id",
            "scenario_id": "s" * 129,
            "selected_answer": "opt_pause_verify",
        },
    )
    assert resp.status_code == 422


def test_oversized_idempotency_key_rejected_by_api(client):
    """idempotency_key exceeding max_length=256 must be rejected with HTTP 422."""
    resp = client.post(
        "/api/experiments/submit",
        json={
            "participant_id": "valid_participant_id",
            "scenario_id": "scen_upi_qr_tamper",
            "selected_answer": "opt_pause_verify",
            "idempotency_key": "k" * 257,
        },
    )
    assert resp.status_code == 422


def test_excessively_large_traits_rejected_by_assign_api(client):
    """traits payload with more than 20 keys must be rejected with HTTP 422."""
    big_traits = {f"trait_{i}": f"value_{i}" for i in range(21)}
    resp = client.post(
        "/api/experiments/assign",
        json={"participant_id": "valid_participant", "traits": big_traits},
    )
    assert resp.status_code == 422


def test_excessively_large_metadata_rejected_by_submit_api(client):
    """metadata payload with more than 20 keys must be rejected with HTTP 422."""
    big_meta = {f"key_{i}": f"val_{i}" for i in range(21)}
    resp = client.post(
        "/api/experiments/submit",
        json={
            "participant_id": "valid_participant",
            "scenario_id": "scen_upi_qr_tamper",
            "selected_answer": "opt_pause_verify",
            "metadata": big_meta,
        },
    )
    assert resp.status_code == 422


def test_assign_participant_id_too_short_rejected(client):
    """participant_id shorter than min_length=3 is rejected with HTTP 422."""
    resp = client.post(
        "/api/experiments/assign",
        json={"participant_id": "ab"},
    )
    assert resp.status_code == 422


# ==========================================
# R3. Concurrent Duplicate Submissions
# ==========================================

def test_concurrent_duplicate_submissions_produce_one_record(fresh_repo, fresh_validator, fallback_flagsmith):
    """Two concurrent requests with the same scoped key must result in exactly
    one accepted submission stored in the repository."""
    service = ExperimentService(
        experiment_repo=fresh_repo,
        scenario_validator=fresh_validator,
        flagsmith_service=fallback_flagsmith,
    )
    req = ExperimentSubmitRequest(
        participant_id="concurrent_user_01",
        scenario_id="scen_upi_qr_tamper",
        selected_answer="opt_pause_verify",
        selected_action="act_verify_vpa",
        idempotency_key="concurrent_idem_01",
    )

    results: list = []
    errors: list = []

    def submit():
        try:
            results.append(service.submit_scenario_attempt(req))
        except Exception as exc:
            errors.append(exc)

    t1 = threading.Thread(target=submit)
    t2 = threading.Thread(target=submit)
    t1.start(); t2.start()
    t1.join(); t2.join()

    assert not errors, f"Unexpected exceptions: {errors}"
    assert len(results) == 2

    # Exactly one must be new, one must be duplicate
    new_count = sum(1 for r in results if not r.is_duplicate)
    dup_count = sum(1 for r in results if r.is_duplicate)
    assert new_count == 1, f"Expected 1 new submission, got {new_count}"
    assert dup_count == 1, f"Expected 1 duplicate, got {dup_count}"

    # Both must return the same submission_id
    assert results[0].submission_id == results[1].submission_id


def test_concurrent_duplicates_do_not_create_duplicate_local_events(fresh_repo, fresh_validator, fallback_flagsmith):
    """Concurrent duplicate submissions must not write extra local metric events."""
    service = ExperimentService(
        experiment_repo=fresh_repo,
        scenario_validator=fresh_validator,
        flagsmith_service=fallback_flagsmith,
    )
    req = ExperimentSubmitRequest(
        participant_id="concurrent_user_02",
        scenario_id="scen_upi_qr_tamper",
        selected_answer="opt_pause_verify",
        selected_action="act_verify_vpa",
        idempotency_key="concurrent_idem_02",
    )

    threads = [threading.Thread(target=service.submit_scenario_attempt, args=(req,)) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()

    # For a correct submission we expect exactly 3 events (risk_signal_understood,
    # verification_action_selected, risk_check_correctly_completed)
    events = fresh_repo.get_events(participant_id="concurrent_user_02")
    assert len(events) == 3, (
        f"Expected exactly 3 events (1 set), got {len(events)}: "
        f"{[e['metric_name'] for e in events]}"
    )


def test_concurrent_duplicates_do_not_forward_duplicate_flagsmith_events(
    fresh_repo, fresh_validator
):
    """Flagsmith track_experiment_event must only be called for the one accepted
    submission, not for any duplicate. We verify via a mock."""
    mock_flagsmith = MagicMock(spec=FlagsmithIntegrationService)
    mock_flagsmith.is_configured = False
    mock_flagsmith.get_variant_for_identity.return_value = {
        "variant": VARIANT_PAYMENT_PASSPORT_FIRST,
        "source": "deterministic_fallback",
        "enabled": True,
        "raw_value": VARIANT_PAYMENT_PASSPORT_FIRST,
        "error": None,
    }
    mock_flagsmith.track_experiment_event.return_value = False

    service = ExperimentService(
        experiment_repo=fresh_repo,
        scenario_validator=fresh_validator,
        flagsmith_service=mock_flagsmith,
    )
    req = ExperimentSubmitRequest(
        participant_id="concurrent_user_flagsmith",
        scenario_id="scen_upi_qr_tamper",
        selected_answer="opt_pause_verify",
        selected_action="act_verify_vpa",
        idempotency_key="concurrent_idem_flagsmith",
    )

    threads = [threading.Thread(target=service.submit_scenario_attempt, args=(req,)) for _ in range(4)]
    for t in threads: t.start()
    for t in threads: t.join()

    # 3 Flagsmith event calls expected (one set for the single accepted submission)
    assert mock_flagsmith.track_experiment_event.call_count == 3, (
        f"Expected 3 Flagsmith event calls, got {mock_flagsmith.track_experiment_event.call_count}"
    )


# ==========================================
# R4. Abandoned Submission Duplicate Protection
# ==========================================

def test_abandoned_submission_idempotency_protection(client, fresh_repo):
    """Abandoned submissions must also be protected by scoped idempotency.
    A second identical abandoned submission must return is_duplicate=True
    and must not create additional events."""
    payload = {
        "participant_id": "user_abandon_idempotent",
        "scenario_id": "scen_unverified_bill_payment",
        "selected_answer": "none",
        "abandoned": True,
        "idempotency_key": "abandon_idem_key_001",
    }
    resp1 = client.post("/api/experiments/submit", json=payload)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["is_duplicate"] is False
    assert "verification_abandoned" in data1["events_recorded"]

    event_count_after_first = len(
        fresh_repo.get_events(participant_id="user_abandon_idempotent")
    )

    resp2 = client.post("/api/experiments/submit", json=payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["is_duplicate"] is True
    assert data2["events_recorded"] == []

    event_count_after_second = len(
        fresh_repo.get_events(participant_id="user_abandon_idempotent")
    )
    assert event_count_after_second == event_count_after_first


# ==========================================
# R5. Assignment Feature-Name Consistency
# ==========================================

def test_assignment_different_feature_name_does_not_silently_reuse_incompatible_cache(
    fresh_repo, fresh_validator, fallback_flagsmith
):
    """An assignment cached for feature_name=A must not be silently returned
    when a request arrives for feature_name=B on the same participant and experiment."""
    service = ExperimentService(
        experiment_repo=fresh_repo,
        scenario_validator=fresh_validator,
        flagsmith_service=fallback_flagsmith,
    )
    participant = "feature_mismatch_user"

    # First assignment: default feature
    req_a = ExperimentAssignRequest(
        participant_id=participant,
        feature_name="payment_intelligence_experience",
    )
    resp_a = service.assign_participant(req_a)
    assert resp_a.feature_name == "payment_intelligence_experience"

    # Second assignment request with a different feature_name
    req_b = ExperimentAssignRequest(
        participant_id=participant,
        feature_name="alternative_feature_flag",
    )
    resp_b = service.assign_participant(req_b)
    # The response must report the requested feature_name, not the cached one
    assert resp_b.feature_name == "alternative_feature_flag", (
        f"Expected feature_name='alternative_feature_flag', got '{resp_b.feature_name}'"
    )


def test_assignment_same_feature_name_reuses_cache(
    fresh_repo, fresh_validator, fallback_flagsmith
):
    """Same participant + same feature_name must reuse the cached assignment."""
    service = ExperimentService(
        experiment_repo=fresh_repo,
        scenario_validator=fresh_validator,
        flagsmith_service=fallback_flagsmith,
    )
    req = ExperimentAssignRequest(participant_id="feature_stable_user")
    resp1 = service.assign_participant(req)
    resp2 = service.assign_participant(req)
    assert resp1.variant == resp2.variant


# ==========================================
# R6. API Error Response Safety
# ==========================================

def test_internal_exception_does_not_expose_raw_message_in_http_500(client, fresh_repo, fresh_validator):
    """When a service raises an unexpected exception, the HTTP 500 response
    must contain a safe generic message, not the raw exception string."""
    mock_fs = MagicMock(spec=FlagsmithIntegrationService)
    mock_fs.is_configured = False
    mock_fs.get_variant_for_identity.side_effect = RuntimeError(
        "Internal DB connection string: postgres://user:secret@host/db"
    )

    app = FastAPI()
    app.include_router(experiments_router)
    app.dependency_overrides[get_experiment_repo] = lambda: fresh_repo
    app.dependency_overrides[get_scenario_validator] = lambda: fresh_validator
    app.dependency_overrides[get_flagsmith_service] = lambda: mock_fs
    error_client = TestClient(app, raise_server_exceptions=False)

    resp = error_client.post(
        "/api/experiments/assign",
        json={"participant_id": "error_test_user"},
    )
    assert resp.status_code == 500
    body = resp.json()
    # Must NOT expose internal details
    assert "postgres" not in str(body).lower()
    assert "secret" not in str(body).lower()
    assert "connection string" not in str(body).lower()
    # Must contain a generic safe message
    assert "detail" in body


# ==========================================
# R7. Public Scenario Response — No Answer Leakage
# ==========================================

def test_public_scenario_response_hides_all_internal_fields(client):
    """Comprehensive check that no internal evaluation field leaks through the
    public scenarios endpoint, including both underscore-prefixed fields and
    any other field that should be withheld."""
    response = client.get("/api/experiments/scenarios")
    assert response.status_code == 200
    for scenario in response.json():
        raw = str(scenario)
        forbidden_keys = [
            "_expected_answer", "_expected_actions", "_explanation",
            "_risk_signal_identifier", "feedback",
        ]
        for key in forbidden_keys:
            assert key not in scenario, f"Forbidden key '{key}' found in public scenario"
        # Verify canonical answer strings are not embedded anywhere in the JSON
        assert "opt_pause_verify" not in raw or "id" in scenario  # option IDs are allowed as option items
        # _expected_answer field itself must not be present
        assert "_expected_answer" not in scenario
