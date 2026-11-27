"""Development scenario dataset and validation service for Flagsmith experiment.

Ensures expected answers are strictly held on the backend and NEVER exposed
through public scenario endpoints.
"""

from typing import Optional, Any
from backend.app.repositories.interfaces.scenario_validator import (
    ScenarioValidatorInterface,
    ValidationResult,
)


CANONICAL_SCENARIOS: dict[str, dict[str, Any]] = {
    "scen_upi_qr_tamper": {
        "id": "scen_upi_qr_tamper",
        "title": "Merchant Counter QR Code Payment",
        "category": "upi_safety",
        "amount": 450.00,
        "context": (
            "You are at a local grocery store paying INR 450. The merchant has a printed QR code on the counter. "
            "When scanned, the payment app displays payee name 'quick_refund_support_89@ybl' instead of the store's "
            "registered business name 'Sharma General Store'."
        ),
        "options": [
            {
                "id": "opt_proceed",
                "label": "Proceed and enter UPI PIN immediately to complete the purchase.",
            },
            {
                "id": "opt_pause_verify",
                "label": "Pause: alert the shopkeeper that the scanned UPI ID does not match their store name.",
            },
            {
                "id": "opt_enter_pin_half",
                "label": "Pay half the amount first to check if the store receives it.",
            },
        ],
        "verification_actions": [
            {"id": "act_verify_vpa", "label": "Verify VPA / Soundbox confirmation with store owner"},
            {"id": "act_scan_again", "label": "Ask shopkeeper for official fresh QR code"},
            {"id": "act_ignore", "label": "Ignore and proceed anyway"},
        ],
        # Canonical backend evaluation criteria (NEVER EXPOSED TO FRONTEND)
        "_expected_answer": "opt_pause_verify",
        "_expected_actions": {"act_verify_vpa", "act_scan_again"},
        "_risk_signal_identifier": "vpa_name_mismatch",
        "_explanation": (
            "Scanned VPA 'quick_refund_support_89@ybl' does not match the merchant. QR tampering is common in retail. "
            "Verifying the VPA or requesting a fresh code prevents diversion of funds to a fraudster."
        ),
    },
    "scen_collect_request_phish": {
        "id": "scen_collect_request_phish",
        "title": "Unexpected UPI Collect Request for 'Refund'",
        "category": "upi_safety",
        "amount": 2500.00,
        "context": (
            "You receive an unsolicited notification from your UPI app stating: "
            "'COLLECT REQUEST: Electric Board Refund of INR 2,500. Enter UPI PIN to receive money in your account.' "
            "A contact calling themselves 'Discom Helpdesk' is simultaneously calling you."
        ),
        "options": [
            {
                "id": "opt_enter_pin_receive",
                "label": "Enter UPI PIN right away so the refund is credited to your bank account.",
            },
            {
                "id": "opt_decline_and_block",
                "label": "Decline the collect request immediately and block the caller. UPI PIN is NEVER required to receive money.",
            },
            {
                "id": "opt_ask_for_otp",
                "label": "Ask the caller for an OTP first before entering PIN.",
            },
        ],
        "verification_actions": [
            {"id": "act_decline_collect", "label": "Decline collect request and report fraud in UPI app"},
            {"id": "act_call_1930", "label": "Report to National Cyber Crime helpline (1930)"},
            {"id": "act_send_pin", "label": "Authorize collect request"},
        ],
        # Canonical backend evaluation criteria (NEVER EXPOSED TO FRONTEND)
        "_expected_answer": "opt_decline_and_block",
        "_expected_actions": {"act_decline_collect", "act_call_1930"},
        "_risk_signal_identifier": "pin_requested_to_receive_money",
        "_explanation": (
            "A UPI PIN is exclusively used to DEBIT funds from your account. Receiving funds or refunds never requires entering a UPI PIN. "
            "This is a classic collect-request phishing attack."
        ),
    },
    "scen_unverified_bill_payment": {
        "id": "scen_unverified_bill_payment",
        "title": "SMS Urgent Disconnection Notice with Unverified Link",
        "category": "utility_bill",
        "amount": 3200.00,
        "context": (
            "You receive an urgent SMS: 'Dear consumer, electricity will be disconnected tonight at 9:30 PM due to unpaid bill. "
            "Call officer at 98xxxxxx or click http://pay-electricity-quick.in to update immediately.' "
            "Your regular bills are paid through your registered electricity discom portal."
        ),
        "options": [
            {
                "id": "opt_click_link_pay",
                "label": "Click the SMS link and pay immediately to avoid power disconnection.",
            },
            {
                "id": "opt_verify_discom_official",
                "label": "Do not click the link. Log in directly to the official discom website/app to check bill status.",
            },
            {
                "id": "opt_call_officer",
                "label": "Call the phone number in the SMS and share your consumer number.",
            },
        ],
        "verification_actions": [
            {"id": "act_check_official_portal", "label": "Inspect official electricity discom portal"},
            {"id": "act_check_past_payments", "label": "Review past payments in PayPause Payment Management"},
            {"id": "act_open_sms_link", "label": "Open the link in SMS"},
        ],
        # Canonical backend evaluation criteria (NEVER EXPOSED TO FRONTEND)
        "_expected_answer": "opt_verify_discom_official",
        "_expected_actions": {"act_check_official_portal", "act_check_past_payments"},
        "_risk_signal_identifier": "urgent_disconnection_phish_sms",
        "_explanation": (
            "Electricity boards never send disconnection threats from personal mobile numbers or suspicious non-government links. "
            "Always check bill status through the official portal or your payment history."
        ),
    },
}


class MockScenarioValidator(ScenarioValidatorInterface):
    """Scenario retrieval and backend correctness validation service."""

    def __init__(self, scenarios: Optional[dict[str, dict[str, Any]]] = None) -> None:
        self._scenarios = scenarios or CANONICAL_SCENARIOS

    def get_public_scenarios(self) -> list[dict[str, Any]]:
        """Return public scenarios stripping all hidden answer and evaluation fields."""
        public_list = []
        for s in self._scenarios.values():
            public_list.append(self._to_public(s))
        return public_list

    def get_public_scenario(self, scenario_id: str) -> Optional[dict[str, Any]]:
        s = self._scenarios.get(scenario_id)
        if not s:
            return None
        return self._to_public(s)

    def validate_answer(
        self, scenario_id: str, selected_answer: str, selected_action: Optional[str] = None
    ) -> ValidationResult:
        s = self._scenarios.get(scenario_id)
        if not s:
            return ValidationResult(
                scenario_id=scenario_id,
                is_correct=False,
                score=0.0,
                feedback=f"Scenario '{scenario_id}' was not recognized.",
                risk_signal_identified=False,
                appropriate_action_selected=False,
            )

        expected_answer = s["_expected_answer"]
        expected_actions = s.get("_expected_actions", set())
        is_answer_correct = selected_answer.strip().lower() == expected_answer.lower()

        action_ok = False
        if selected_action:
            action_ok = selected_action.strip().lower() in {a.lower() for a in expected_actions}

        is_overall_correct = is_answer_correct and (action_ok if selected_action else True)
        score = 1.0 if is_overall_correct else (0.5 if is_answer_correct else 0.0)

        return ValidationResult(
            scenario_id=scenario_id,
            is_correct=is_overall_correct,
            score=score,
            feedback=s["_explanation"],
            risk_signal_identified=is_answer_correct,
            appropriate_action_selected=action_ok,
            details={
                "risk_signal": s["_risk_signal_identifier"],
                "answer_matched": is_answer_correct,
                "action_matched": action_ok,
            },
        )

    @staticmethod
    def _to_public(scenario: dict[str, Any]) -> dict[str, Any]:
        """Strip internal canonical fields starting with '_'."""
        return {k: v for k, v in scenario.items() if not k.startswith("_")}
