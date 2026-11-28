"""Flagsmith integration client for PayPause experiment management.

Uses official Flagsmith Python SDK (v6.x) with robust error handling,
deterministic fallback, and identity-based multivariate variant evaluation.
"""

import hashlib
import logging
from typing import Optional, Any
from flagsmith import Flagsmith
from flagsmith.exceptions import FlagsmithAPIError, FlagsmithClientError

from app.core.config import Settings, get_settings

logger = logging.getLogger("paypause.flagsmith")

EXPERIMENT_FEATURE_NAME = "payment_intelligence_experience"
DEFAULT_EXPERIMENT_NAME = "PayPause Payment Intelligence Experience"
VARIANT_RISK_SCORE_FIRST = "risk_score_first"
VARIANT_PAYMENT_PASSPORT_FIRST = "payment_passport_first"
VALID_VARIANTS = {VARIANT_RISK_SCORE_FIRST, VARIANT_PAYMENT_PASSPORT_FIRST}


class FlagsmithIntegrationService:
    """Service wrapping the official Flagsmith SDK for experimentation."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.is_configured = bool(
            self.settings.flagsmith_environment_key
            and self.settings.flagsmith_environment_key.strip()
        )
        self._client: Optional[Flagsmith] = None

        if self.is_configured:
            try:
                self._client = Flagsmith(
                    environment_key=self.settings.flagsmith_environment_key,
                    api_url=self.settings.flagsmith_api_url,
                    request_timeout_seconds=int(self.settings.flagsmith_request_timeout_seconds),
                    enable_events=True,
                )
                logger.info("Flagsmith client initialized successfully with environment key.")
            except Exception as e:
                logger.error("Failed to initialize Flagsmith client: %s", e)
                self._client = None
                self.is_configured = False
        else:
            logger.warning(
                "Flagsmith environment key not configured. Running in deterministic fallback mode."
            )

    @property
    def client(self) -> Optional[Flagsmith]:
        return self._client

    def get_variant_for_identity(
        self,
        identifier: str,
        feature_name: str = EXPERIMENT_FEATURE_NAME,
        traits: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Evaluate and return the experiment variant for a participant identity.

        Returns a dictionary containing:
        - variant: str ('risk_score_first' or 'payment_passport_first')
        - source: str ('flagsmith_real' or 'deterministic_fallback')
        - enabled: bool
        - raw_value: Any
        - error: Optional[str]
        """
        if not identifier or not identifier.strip():
            raise ValueError("Participant identity must be a non-empty string.")

        clean_id = identifier.strip()

        # 1. Attempt real Flagsmith evaluation if configured
        if self.is_configured and self._client:
            try:
                # Use official get_identity_flags
                identity_flags = self._client.get_identity_flags(
                    identifier=clean_id,
                    traits=traits,
                )
                flag = identity_flags.get_flag(feature_name)

                # Check value / variant
                val = flag.value
                enabled = flag.enabled

                # Resolve variant name
                variant = None
                if isinstance(val, str) and val in VALID_VARIANTS:
                    variant = val
                elif flag.variant and flag.variant in VALID_VARIANTS:
                    variant = flag.variant
                elif enabled:
                    variant = VARIANT_PAYMENT_PASSPORT_FIRST
                else:
                    variant = VARIANT_RISK_SCORE_FIRST

                return {
                    "variant": variant,
                    "source": "flagsmith_real",
                    "enabled": enabled,
                    "raw_value": val,
                    "error": None,
                }
            except (FlagsmithAPIError, FlagsmithClientError, Exception) as exc:
                logger.warning(
                    "Flagsmith live evaluation failed for identity '%s': %s. Falling back to deterministic assignment.",
                    clean_id,
                    exc,
                )
                # Fall through to deterministic assignment
                return self._deterministic_fallback_assignment(clean_id, str(exc))

        # 2. Deterministic assignment when not configured
        return self._deterministic_fallback_assignment(
            clean_id, error="Flagsmith environment key not configured; using deterministic fallback."
        )

    def track_experiment_event(
        self,
        event_name: str,
        identifier: Optional[str] = None,
        value: Optional[float] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Forward an experiment metric event to Flagsmith if configured."""
        if self.is_configured and self._client:
            try:
                self._client.track_event(
                    event=event_name,
                    identifier=identifier,
                    value=value,
                    metadata=metadata,
                )
                return True
            except Exception as e:
                logger.error("Failed to forward event '%s' to Flagsmith: %s", event_name, e)
                return False
        return False

    @staticmethod
    def _deterministic_fallback_assignment(
        identifier: str, error: Optional[str] = None
    ) -> dict[str, Any]:
        """Stable 50/50 hash-based assignment for independent offline/mock development.

        Guarantees that:
        - The exact same identifier always gets the exact same variant.
        - Distribution across many IDs splits 50/50.
        - Participants cannot manually game their variant.
        """
        digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()
        last_byte = int(digest[-2:], 16)
        variant = (
            VARIANT_PAYMENT_PASSPORT_FIRST
            if (last_byte % 2 == 0)
            else VARIANT_RISK_SCORE_FIRST
        )
        return {
            "variant": variant,
            "source": "deterministic_fallback",
            "enabled": True,
            "raw_value": variant,
            "error": error,
        }
