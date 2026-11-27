"""Business logic service for Recovery Desk incident tracking and deterministic complaint drafts."""

from datetime import datetime, timezone
from typing import Optional, Any

from backend.app.schemas.recovery import (
    IncidentCreate,
    IncidentUpdate,
    IncidentResponse,
    IncidentListResponse,
    ComplaintDraftResponse,
    EvidenceChecklistItem,
)
from backend.app.repositories.interfaces.incident_repo import IncidentRepositoryInterface
from backend.app.core.security import sanitize_payload


CATEGORY_EVIDENCE_MAP: dict[str, list[dict[str, Any]]] = {
    "suspicious_upi": [
        {
            "item_name": "Counterparty VPA / UPI ID",
            "is_mandatory": True,
            "description": "Virtual Payment Address of the suspicious entity (e.g. name@upi).",
            "how_to_obtain": "View transaction details or collect request header in your UPI app.",
        },
        {
            "item_name": "Screenshot of Payment Prompt / QR",
            "is_mandatory": True,
            "description": "Visual proof of QR code, collect request, or scam prompt.",
            "how_to_obtain": "Capture screenshot on your mobile device immediately.",
        },
        {
            "item_name": "Phone / Contact Info of Requester",
            "is_mandatory": False,
            "description": "Mobile number or social handle associated with the request.",
            "how_to_obtain": "Check incoming call log or SMS sender identity.",
        },
    ],
    "unauthorised_transaction": [
        {
            "item_name": "Transaction UTR / Reference Number",
            "is_mandatory": True,
            "description": "12-digit Unique Transaction Reference assigned by NPCI/bank.",
            "how_to_obtain": "Found in debit SMS or account statement.",
        },
        {
            "item_name": "Bank Debit SMS Alert with Timestamp",
            "is_mandatory": True,
            "description": "Official SMS alert from bank confirming funds debit.",
            "how_to_obtain": "Save SMS thread from your bank.",
        },
        {
            "item_name": "Bank Account Statement",
            "is_mandatory": True,
            "description": "Official statement showing the disputed debit entry.",
            "how_to_obtain": "Download PDF from mobile banking or net banking portal.",
        },
        {
            "item_name": "Confirmation of Non-Disclosure of Credentials",
            "is_mandatory": True,
            "description": "Declaration that UPI PIN, OTP, or passwords were never disclosed.",
            "how_to_obtain": "Included in the PayPause generated complaint draft.",
        },
    ],
    "failed_payment": [
        {
            "item_name": "Transaction Reference / UTR",
            "is_mandatory": True,
            "description": "Unique transaction identifier for tracing across banks.",
            "how_to_obtain": "Check transaction history in your UPI/banking app.",
        },
        {
            "item_name": "Merchant Order Failure Screen",
            "is_mandatory": True,
            "description": "Screenshot from merchant indicating payment failed or was not received.",
            "how_to_obtain": "Take screenshot of the order status page.",
        },
        {
            "item_name": "Passbook / Account Statement Entry",
            "is_mandatory": True,
            "description": "Proof of money deducted from sender bank account.",
            "how_to_obtain": "Download recent transactions statement.",
        },
    ],
    "delayed_refund": [
        {
            "item_name": "Order Cancellation / Refund Confirmation",
            "is_mandatory": True,
            "description": "Email or receipt from merchant confirming refund initiated.",
            "how_to_obtain": "Save merchant refund confirmation email or invoice.",
        },
        {
            "item_name": "Merchant Refund ARN / Reference Number",
            "is_mandatory": False,
            "description": "Acquirer Reference Number provided by merchant payment gateway.",
            "how_to_obtain": "Request gateway ARN from merchant customer support.",
        },
        {
            "item_name": "Bank Statement Covering Turnaround Window",
            "is_mandatory": True,
            "description": "Statement showing no refund credit occurred within T+5/T+7 working days.",
            "how_to_obtain": "Download statement for the period following cancellation.",
        },
    ],
    "duplicate_payment": [
        {
            "item_name": "Both Transaction Reference Numbers (UTRs)",
            "is_mandatory": True,
            "description": "UTRs for both debits of the identical payment.",
            "how_to_obtain": "Locate both debit entries in your UPI app or bank statement.",
        },
        {
            "item_name": "Single Merchant Receipt / Order Confirmation",
            "is_mandatory": True,
            "description": "Proof that only one order was placed and fulfilled.",
            "how_to_obtain": "Merchant order invoice or delivery receipt.",
        },
    ],
    "suspected_fraud": [
        {
            "item_name": "Fraud Communication Proof (Call/SMS/Chat)",
            "is_mandatory": True,
            "description": "Screenshots of phishing messages, APK links, or call records.",
            "how_to_obtain": "Preserve WhatsApp, SMS, or Telegram chat exports.",
        },
        {
            "item_name": "Debit Transaction UTR",
            "is_mandatory": True,
            "description": "NPCI 12-digit transaction identifier.",
            "how_to_obtain": "Bank debit SMS or statement.",
        },
    ],
    "other_dispute": [
        {
            "item_name": "Proof of Transaction",
            "is_mandatory": True,
            "description": "Receipt, bank statement, or transaction screenshot.",
            "how_to_obtain": "Export transaction from your banking application.",
        },
        {
            "item_name": "Correspondence with Merchant / Bank",
            "is_mandatory": False,
            "description": "Email thread or support tickets raised previously.",
            "how_to_obtain": "Export customer support emails or chat transcripts.",
        },
    ],
}


class RecoveryService:
    """Service for managing incidents, checklists, and statutory complaint drafts."""

    def __init__(self, repo: IncidentRepositoryInterface) -> None:
        self.repo = repo

    def create_incident(self, user_id: str, payload: IncidentCreate) -> IncidentResponse:
        """Create a new recovery incident and attach relevant evidence checklist."""
        data = sanitize_payload(payload.model_dump())
        data["user_id"] = user_id
        data["status"] = "reported"

        created = self.repo.create_incident(data)
        return self._format_incident_response(created)

    def get_incident_by_id(self, incident_id: str, user_id: str) -> Optional[IncidentResponse]:
        """Retrieve single recovery incident ensuring user ownership."""
        record = self.repo.get_incident_by_id(incident_id, user_id)
        if not record:
            return None
        return self._format_incident_response(record)

    def list_incidents(
        self,
        user_id: str,
        category: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> IncidentListResponse:
        """Retrieve filtered recovery incidents for authenticated user."""
        items, total = self.repo.list_incidents(
            user_id=user_id,
            category=category,
            status=status,
            limit=limit,
            offset=offset,
        )
        return IncidentListResponse(
            items=[self._format_incident_response(inc) for inc in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    def update_incident(
        self, incident_id: str, user_id: str, payload: IncidentUpdate
    ) -> Optional[IncidentResponse]:
        """Update mutable incident fields or append evidence items."""
        update_data = sanitize_payload(payload.model_dump(exclude_unset=True))
        if not update_data:
            existing = self.repo.get_incident_by_id(incident_id, user_id)
            return self._format_incident_response(existing) if existing else None

        existing = self.repo.get_incident_by_id(incident_id, user_id)
        if not existing:
            return None

        # If adding evidence items, merge with existing evidence list
        if "add_evidence" in update_data:
            new_evidence = update_data.pop("add_evidence")
            current_evidence = list(existing.get("evidence_references", []))
            existing_ids = {e.get("id") for e in current_evidence}
            for item in new_evidence:
                item_dict = item if isinstance(item, dict) else item.model_dump()
                # Update existing if same id, otherwise append
                if item_dict.get("id") in existing_ids:
                    current_evidence = [e for e in current_evidence if e.get("id") != item_dict["id"]]
                current_evidence.append(item_dict)
                existing_ids.add(item_dict.get("id"))
            update_data["evidence_references"] = current_evidence

        updated = self.repo.update_incident(incident_id, user_id, update_data)
        if not updated:
            return None
        return self._format_incident_response(updated)

    def remove_evidence(
        self, incident_id: str, user_id: str, evidence_id: str
    ) -> tuple[bool, bool, Optional[IncidentResponse]]:
        """Remove an evidence item from an incident by its ID.

        Returns:
            (incident_found: bool, evidence_found: bool, updated_incident: Optional[IncidentResponse])
        """
        incident_found, evidence_found, updated = self.repo.remove_evidence(
            incident_id=incident_id, user_id=user_id, evidence_id=evidence_id
        )
        if not incident_found or not evidence_found or not updated:
            return incident_found, evidence_found, None
        return True, True, self._format_incident_response(updated)


    def generate_complaint_draft(
        self, incident_id: str, user_id: str
    ) -> Optional[ComplaintDraftResponse]:
        """Generate a deterministic, statutory complaint draft for bank and cybercrime reporting.

        Never invents transaction references, never guarantees recovery, and clearly labels output.
        """
        incident = self.repo.get_incident_by_id(incident_id, user_id)
        if not incident:
            return None

        cat = incident.get("category", "other_dispute")
        tx_ref = incident.get("transaction_ref") or "NOT_AVAILABLE_OR_NOT_ISSUED"
        amt = incident.get("amount", 0.0)
        curr = incident.get("currency", "INR")
        provider = incident.get("provider", "Payment Service Provider")
        incident_dt = incident.get("incident_datetime", "Recent")
        desc = incident.get("description", "")

        statutory_guidance = {
            "immediate_action": "Contact your bank's 24x7 fraud reporting helpline immediately.",
            "national_cyber_helpline": "1930",
            "official_cyber_portal": "https://cybercrime.gov.in/",
            "rbi_protection_circular": (
                "RBI Circular RBI/2017-18/15 DBR.No.Leg.BC.78/09.07.005/2017-18 on "
                "'Customer Protection – Limiting Liability of Customers in Unauthorised Electronic Banking Transactions'."
            ),
            "zero_liability_window": (
                "Zero liability applies where customer notifies the bank within 3 working days of receiving the notification."
            ),
            "banking_ombudsman_link": "https://cms.rbi.org.in/",
        }

        # Deterministic credential disclosure declaration based on user explicit response
        cred_status = incident.get("credentials_disclosed")
        if cred_status == "no":
            cred_declaration = (
                "2. I affirm that no confidential authentication credentials (such as UPI PIN, "
                "Netbanking password, or card CVV) were voluntarily disclosed for authorizing this transaction."
            )
        elif cred_status == "yes":
            cred_declaration = (
                "2. I report that authentication credentials may have been compromised or disclosed "
                "under deception/duress during this incident, and I request urgent tracing of funds, "
                "account security review, and immediate preventive freezing of the beneficiary account."
            )
        elif cred_status in ("not_sure", "prefer_not_to_say"):
            cred_declaration = (
                "2. I request a thorough technical investigation of the transaction authorization logs "
                "by the bank and service provider, as the circumstances of authentication remain unverified or disputed."
            )
        else:
            # Unanswered: neutral wording without making assumptions
            cred_declaration = (
                "2. I request the bank and service provider to thoroughly investigate the authorization logs "
                "and technical circumstances surrounding this disputed transaction without prejudice."
            )

        formal_body = f"""DRAFT COMPLAINT LETTER (CITIZEN PREPARATION DRAFT)
--------------------------------------------------------------------------------
To:
The Nodal Grievance Redressal Officer / Branch Manager,
{provider}

Date of Notice: {datetime.now(timezone.utc).strftime('%d %B %Y')}

Subject: Formal Grievance & Dispute Notice Regarding Disputed Transaction
Category: {cat.replace('_', ' ').upper()}
Transaction Reference / UTR: {tx_ref}
Disputed Amount: {curr} {amt:,.2f}
Incident Occurrence Timestamp: {incident_dt}

Dear Sir/Madam,

I am writing to formally report an unauthorized / disputed electronic payment transaction that occurred on my account linked with {provider}.

INCIDENT DETAILS:
- Transaction Identifier (UTR / Ref): {tx_ref}
- Disputed Amount: {curr} {amt:,.2f}
- Date and Time: {incident_dt}
- Payment Service Provider / Channel: {provider}

DESCRIPTION OF EVENT:
{desc}

STATUTORY DECLARATION & RELIEF SOUGHT:
1. I hereby invoke protection under Reserve Bank of India Circular RBI/2017-18/15 (DBR.No.Leg.BC.78/09.07.005/2017-18) on Customer Protection – Limiting Liability of Customers in Unauthorised Electronic Banking Transactions, and request that this grievance be treated with urgency under its provisions.
{cred_declaration}
3. I request your immediate intervention to trace the beneficiary account, place a temporary freeze on the credited funds, and reverse the disputed debit of {curr} {amt:,.2f} to my original funding account.
4. If this grievance is not resolved satisfactorily within 30 days, I reserve the right to escalate this complaint to the RBI Ombudsman under the Reserve Bank – Integrated Ombudsman Scheme.

I intend to report this incident through the National Cybercrime Reporting Portal (Helpline 1930 / https://cybercrime.gov.in/).

Sincerely,
Account Holder / Complainant (User ID: {user_id})
Contact: Available on registered account profile
--------------------------------------------------------------------------------
DISCLAIMER: This document was deterministically compiled by PayPause Recovery Desk to assist citizens in drafting complaints. Generating this draft does NOT file an official grievance or guarantee recovery."""

        checklist = self._get_checklist_for_category(cat)

        draft_response = ComplaintDraftResponse(
            incident_id=incident_id,
            is_draft=True,
            draft_title=f"Dispute Notice - {cat.replace('_', ' ').title()}",
            disclaimer="This is an automated citizen preparation draft and does not constitute an officially filed complaint.",
            formal_letter_body=formal_body,
            recommended_evidence_checklist=checklist,
            statutory_guidance=statutory_guidance,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        # Save draft metadata to repository
        self.repo.save_complaint_draft(
            incident_id=incident_id,
            user_id=user_id,
            draft_data=draft_response.model_dump(),
        )

        return draft_response

    def _format_incident_response(self, record: dict[str, Any]) -> IncidentResponse:
        """Enrich incident record with relevant checklist and structure."""
        cat = record.get("category", "other_dispute")
        checklist = self._get_checklist_for_category(cat)
        data = dict(record)
        data["evidence_checklist"] = checklist
        return IncidentResponse(**data)

    @staticmethod
    def _get_checklist_for_category(category: str) -> list[EvidenceChecklistItem]:
        raw_items = CATEGORY_EVIDENCE_MAP.get(category, CATEGORY_EVIDENCE_MAP["other_dispute"])
        return [EvidenceChecklistItem(**item) for item in raw_items]
