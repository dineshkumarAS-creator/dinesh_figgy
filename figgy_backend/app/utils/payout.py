"""
figgy_backend/app/utils/payout.py
====================================
Razorpay UPI Payout Integration — Figgy GigShield.

Handles outgoing money transfers TO delivery workers after a claim is approved.
Uses Razorpay Payouts API (X product) — separate from the payment gateway used
for premium collection.

Razorpay Payout Flow (one-time setup per worker, then reuse)
-------------------------------------------------------------
1. POST /v1/contacts         — create a Razorpay Contact for the worker
2. POST /v1/fund_accounts    — link worker's UPI VPA to the contact
3. POST /v1/payouts          — initiate money transfer (per approved claim)

Mock / Test Mode
----------------
Activated automatically when RAZORPAY_KEY_ID starts with "rzp_test_".
No real money moves; all API calls are skipped and deterministic mock
responses are returned. A 2-second simulated delay is applied to
mimic real processing latency so the UI demo looks realistic.

Usage
-----
    from app.utils.payout import RazorpayPayoutService

    svc = RazorpayPayoutService()

    # One-time setup per worker (saves fund_account_id back to DB)
    fa_id = svc.create_worker_fund_account(worker_doc)

    # Per-claim payout
    result = svc.initiate_payout(worker_doc, "FIG-8821", amount_inr=218)
    # → { status, payout_id, payout_status, amount_inr, upi_id, narration }

    # Poll status
    status = svc.get_payout_status("pout_abc123")
    # → "processing" | "processed" | "failed"
"""

import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

import razorpay

from app.models import db_handler

logger = logging.getLogger("FIGGY_PAYOUT")

# ---------------------------------------------------------------------------
# Known Razorpay error codes → friendly messages
# ---------------------------------------------------------------------------
_RAZORPAY_ERROR_MAP: dict[str, str] = {
    "INSUFFICIENT_FUNDS":        "Payout account has insufficient balance. Queued for retry.",
    "INVALID_VPA":               "Worker's UPI ID is invalid or inactive.",
    "VPA_NOT_REGISTERED":        "UPI VPA not registered with any bank.",
    "BANK_ACCOUNT_CLOSED":       "Linked bank account is closed.",
    "BENEFICIARY_BANK_DOWN":     "Worker's bank is temporarily unreachable. Will retry.",
    "REQUEST_TIMEOUT":           "Razorpay API timed out. Payout queued.",
    "BAD_REQUEST_ERROR":         "Malformed payout request — check fund_account_id.",
}

_MOCK_DELAY_SECONDS = 2   # simulates processing latency in demo mode


# ---------------------------------------------------------------------------
# RazorpayPayoutService
# ---------------------------------------------------------------------------

class RazorpayPayoutService:
    """
    Wraps the Razorpay Payouts API (X product) for GigShield claim disbursements.

    Instantiation reads credentials from environment (or Flask app config).
    Mock mode activates automatically when key_id starts with "rzp_test_".

    Thread-safety: the razorpay.Client is stateless per-call — safe to share
    across APScheduler threads.
    """

    def __init__(
        self,
        key_id: Optional[str]     = None,
        key_secret: Optional[str] = None,
        account_number: Optional[str] = None,
    ):
        self._key_id    = key_id     or os.getenv("RAZORPAY_KEY_ID",     "")
        self._secret    = key_secret or os.getenv("RAZORPAY_KEY_SECRET", "")
        self._account   = (
            account_number
            or os.getenv("RAZORPAY_ACCOUNT_NUMBER", "FIGGY_DEMO_ACCOUNT")
        )

        self._mock_mode: bool = (
            not self._key_id
            or not self._secret
            or self._key_id.startswith("rzp_test_")
        )

        if self._mock_mode:
            logger.warning(
                "[PAYOUT] Running in MOCK/TEST mode — "
                "no real money will be transferred."
            )
        else:
            logger.info("[PAYOUT] RazorpayPayoutService initialised (LIVE mode).")

        # Lazily instantiated — avoids import-time crash when keys are absent
        self._client: Optional[razorpay.Client] = None

    # -----------------------------------------------------------------------
    # Internal: get or build Razorpay client
    # -----------------------------------------------------------------------

    def _get_client(self) -> razorpay.Client:
        if self._client is None:
            self._client = razorpay.Client(auth=(self._key_id, self._secret))
        return self._client

    # -----------------------------------------------------------------------
    # Internal: generate mock IDs
    # -----------------------------------------------------------------------

    @staticmethod
    def _ts() -> int:
        return int(datetime.now(timezone.utc).timestamp())

    # -----------------------------------------------------------------------
    # METHOD 1 — create_worker_fund_account
    # -----------------------------------------------------------------------

    def create_worker_fund_account(self, worker: dict) -> str:
        """
        One-time setup: create a Razorpay Contact + UPI Fund Account for a worker.
        Persists the fund_account_id back to the worker record in DB / memory.

        Parameters
        ----------
        worker : dict — worker document (must have worker_id, name, phone, upi_id)

        Returns
        -------
        str — fund_account_id (e.g. "fa_..." or "fa_mock_GS-123456")

        Raises
        ------
        Does NOT raise — returns empty string on failure (caller should check).
        """
        worker_id = worker.get("worker_id", "?")
        upi_id    = worker.get("upi_id",    "")
        name      = worker.get("name",      worker.get("full_name", "GigShield Worker"))
        phone     = worker.get("phone",     worker.get("mobile", "9999999999"))

        # ── Mock mode ────────────────────────────────────────────────────────
        if self._mock_mode:
            mock_fa_id = f"fa_mock_{worker_id}"
            logger.info(
                f"[PAYOUT] MOCK: fund account for worker '{worker_id}' → {mock_fa_id}"
            )
            self._save_fund_account_id(worker_id, mock_fa_id)
            return mock_fa_id

        # ── Live: Step 1 — Create Razorpay Contact ───────────────────────────
        try:
            client = self._get_client()

            contact_payload = {
                "name":         name,
                "contact":      phone,
                "type":         "employee",       # closest category for gig workers
                "reference_id": worker_id,
                "notes": {
                    "worker_id": worker_id,
                    "platform":  "figgy_gigshield",
                },
            }
            contact = client.contact.create(contact_payload)
            contact_id = contact.get("id", "")
            logger.info(
                f"[PAYOUT] Contact created for worker '{worker_id}': {contact_id}"
            )

            # ── Live: Step 2 — Create Fund Account (UPI VPA) ─────────────────
            fund_payload = {
                "contact_id":    contact_id,
                "account_type":  "vpa",
                "vpa": {
                    "address": upi_id,
                },
            }
            fund_account = client.fund_account.create(fund_payload)
            fa_id = fund_account.get("id", "")
            logger.info(
                f"[PAYOUT] Fund account created for worker '{worker_id}': "
                f"{fa_id} (UPI: {upi_id})"
            )

            self._save_fund_account_id(worker_id, fa_id)
            return fa_id

        except razorpay.errors.BadRequestError as exc:
            friendly = self._razorpay_error_msg(exc)
            logger.error(
                f"[PAYOUT] Bad request creating fund account for '{worker_id}': {friendly}"
            )
            return ""

        except Exception as exc:
            logger.error(
                f"[PAYOUT] Unexpected error creating fund account for '{worker_id}': {exc}",
                exc_info=True,
            )
            return ""

    # -----------------------------------------------------------------------
    # METHOD 2 — initiate_payout
    # -----------------------------------------------------------------------

    def initiate_payout(
        self,
        worker: dict,
        claim_id: str,
        amount_inr: float,
    ) -> dict:
        """
        Initiate a UPI payout to the worker for an approved claim.

        Parameters
        ----------
        worker     : dict  — worker document (must have razorpay_fund_account_id, upi_id)
        claim_id   : str   — e.g. "FIG-8821"
        amount_inr : float — INR amount (will be converted to paise internally)

        Returns
        -------
        dict with keys:
            status        – "success" | "error"
            payout_id     – str, Razorpay payout ID (or mock ID)
            payout_status – "processing" | "processed" | "failed"
            amount_inr    – float, echoed
            upi_id        – str, destination UPI handle
            narration     – str, txn description on worker's bank statement
            error_message – str (only present on error)
        """
        worker_id     = worker.get("worker_id", "?")
        upi_id        = worker.get("upi_id", "")
        fa_id         = worker.get("razorpay_fund_account_id", "")
        amount_paise  = int(amount_inr * 100)
        narration     = f"GigShield claim {claim_id}"

        # ── Guard: fund account must exist ───────────────────────────────────
        if not fa_id:
            logger.warning(
                f"[PAYOUT] Worker '{worker_id}' has no fund_account_id. "
                "Attempting to create one now …"
            )
            fa_id = self.create_worker_fund_account(worker)
            if not fa_id:
                return self._error_response(
                    "Worker fund account could not be created. "
                    "Check UPI ID validity.",
                    amount_inr,
                    upi_id,
                    narration,
                )

        # ── Mock / Test mode ─────────────────────────────────────────────────
        if self._mock_mode:
            mock_payout_id = f"pout_mock_{self._ts()}"
            
            # Simulated Mock Failures
            if upi_id == "fail@ybl" or "FAIL" in claim_id.upper():
                logger.info(
                    f"[PAYOUT] DEMO MODE: Simulated FAILED payout of ₹{amount_inr} "
                    f"to {upi_id} for claim {claim_id} ({mock_payout_id})"
                )
                time.sleep(_MOCK_DELAY_SECONDS)
                return self._error_response(
                    "Simulated bank failure (Insufficient funds or bank offline)",
                    amount_inr,
                    upi_id,
                    narration
                )

            logger.info(
                f"[PAYOUT] DEMO MODE: Simulated payout of ₹{amount_inr} "
                f"to {upi_id} for claim {claim_id} ({mock_payout_id})"
            )
            time.sleep(_MOCK_DELAY_SECONDS)   # realistic feeling delay
            return {
                "status":        "success",
                "payout_id":     mock_payout_id,
                "payout_status": "processed",
                "amount_inr":    amount_inr,
                "upi_id":        upi_id,
                "narration":     narration,
                "mode":          "mock",
            }

        # ── Live: POST /v1/payouts ────────────────────────────────────────────
        try:
            client = self._get_client()

            payout_payload = {
                "account_number":       self._account,
                "fund_account_id":      fa_id,
                "amount":               amount_paise,
                "currency":             "INR",
                "mode":                 "UPI",
                "purpose":              "payout",
                "queue_if_low_balance": True,
                "narration":            narration,
                "reference_id":         claim_id,   # idempotency key
                "notes": {
                    "claim_id":  claim_id,
                    "worker_id": worker_id,
                },
            }

            response   = client.payout.create(payout_payload)
            payout_id  = response.get("id",     "")
            raw_status = response.get("status", "processing")

            # Razorpay statuses → our simplified set
            payout_status = self._normalise_status(raw_status)

            logger.info(
                f"[PAYOUT] ✅ Payout initiated: {payout_id} | "
                f"worker={worker_id} | ₹{amount_inr} → {upi_id} | "
                f"status={payout_status}"
            )

            return {
                "status":        "success",
                "payout_id":     payout_id,
                "payout_status": payout_status,
                "amount_inr":    amount_inr,
                "upi_id":        upi_id,
                "narration":     narration,
            }

        except razorpay.errors.BadRequestError as exc:
            friendly = self._razorpay_error_msg(exc)
            logger.error(
                f"[PAYOUT] ❌ BadRequest for claim '{claim_id}': {friendly}"
            )
            return self._error_response(friendly, amount_inr, upi_id, narration)

        except razorpay.errors.ServerError as exc:
            msg = "Razorpay server error — payout queued for retry."
            logger.error(f"[PAYOUT] ❌ ServerError for claim '{claim_id}': {exc}")
            return self._error_response(msg, amount_inr, upi_id, narration)

        except Exception as exc:
            logger.error(
                f"[PAYOUT] ❌ Unexpected error for claim '{claim_id}': {exc}",
                exc_info=True,
            )
            return self._error_response(
                f"Unexpected payout error: {exc}", amount_inr, upi_id, narration
            )

    # -----------------------------------------------------------------------
    # METHOD 3 — get_payout_status
    # -----------------------------------------------------------------------

    def get_payout_status(self, payout_id: str) -> str:
        """
        Fetch the current status of a payout from Razorpay.

        Parameters
        ----------
        payout_id : str — Razorpay payout ID (e.g. "pout_abc123")
                          or a mock ID (e.g. "pout_mock_1711820400")

        Returns
        -------
        str — "processing" | "processed" | "failed"
        """
        # ── Mock IDs ─────────────────────────────────────────────────────────
        if "mock" in payout_id or self._mock_mode:
            logger.debug(
                f"[PAYOUT] MOCK status check for '{payout_id}' → processed"
            )
            return "processed"

        # ── Live fetch ────────────────────────────────────────────────────────
        try:
            client   = self._get_client()
            response = client.payout.fetch(payout_id)
            raw      = response.get("status", "processing")
            status   = self._normalise_status(raw)
            logger.debug(f"[PAYOUT] Status for '{payout_id}': {raw} → {status}")
            return status

        except razorpay.errors.BadRequestError:
            logger.warning(f"[PAYOUT] Payout '{payout_id}' not found on Razorpay.")
            return "failed"

        except Exception as exc:
            logger.error(f"[PAYOUT] Error fetching status for '{payout_id}': {exc}")
            return "processing"   # assume still in flight; caller should retry

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _save_fund_account_id(self, worker_id: str, fa_id: str) -> None:
        """Persist fund_account_id into the worker document (DB or memory)."""
        workers = db_handler.get_all_workers()
        for w in workers:
            if w.get("worker_id") == worker_id:
                w["razorpay_fund_account_id"] = fa_id
                break

        # MongoDB update (no-op in memory mode since we mutated the dict in place)
        if db_handler.is_db_enabled and db_handler.client:
            try:
                db_handler.client[db_handler.db_name].workers.update_one(
                    {"worker_id": worker_id},
                    {"$set": {"razorpay_fund_account_id": fa_id}},
                )
                logger.debug(
                    f"[PAYOUT] fund_account_id '{fa_id}' saved to MongoDB "
                    f"for worker '{worker_id}'."
                )
            except Exception as exc:
                logger.warning(
                    f"[PAYOUT] Could not persist fund_account_id to MongoDB: {exc}"
                )

    @staticmethod
    def _normalise_status(raw: str) -> str:
        """Map Razorpay's verbose statuses to our three-state model."""
        _MAP = {
            "created":    "processing",
            "processing": "processing",
            "processed":  "processed",
            "reversed":   "failed",
            "failed":     "failed",
            "cancelled":  "failed",
            "rejected":   "failed",
        }
        return _MAP.get(raw.lower(), "processing")

    @staticmethod
    def _razorpay_error_msg(exc: Exception) -> str:
        """Extract a friendly message from a Razorpay exception."""
        try:
            code = exc.error.get("code", "")           # type: ignore[attr-defined]
            return _RAZORPAY_ERROR_MAP.get(code, str(exc))
        except Exception:
            return str(exc)

    @staticmethod
    def _error_response(
        message: str,
        amount_inr: float,
        upi_id: str,
        narration: str,
    ) -> dict:
        return {
            "status":        "error",
            "payout_id":     "",
            "payout_status": "failed",
            "amount_inr":    amount_inr,
            "upi_id":        upi_id,
            "narration":     narration,
            "error_message": message,
        }
