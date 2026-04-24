import os
import logging
from enum import Enum
from datetime import datetime
from flask import current_app
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConfigurationError

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FIGGY_APP")

# Memory Storage for Hackathon Mode (Python List)
memory_workers = [
    {
        "worker_id": "GS-OVVSRL",
        "swiggy_id": "SWIG-1234",
        "phone": "9999999999",
        "tier": "Smart",
        "policy_status": "active",
        "zone": "North",
        "avg_daily_earnings": 600
    }
]

# ---------------------------------------------------------------------------
# Claim In-Memory Store  (mirrors memory_workers — used when USE_DB=False)
# ---------------------------------------------------------------------------
memory_claims = []

# ---------------------------------------------------------------------------
# Claim Document Schema
# All fields with types as comments — use as a template for new claim dicts.
# ---------------------------------------------------------------------------
CLAIM_SCHEMA_TEMPLATE = {
    # ── Identity ──────────────────────────────────────────────────────────
    "claim_id":             "",    # str  — "FIG-" + 4 random digits, e.g. FIG-8821
    "worker_id":            "",    # str  — GS-XXXXXX (from worker registration)
    "claim_source":         "",    # str  — "auto" | "manual"
    "tier":                 "",    # str  — worker's plan tier at time of claim

    # ── Claim Type & Window ───────────────────────────────────────────────
    "claim_type":           "",    # str  — "auto" | "manual" (Matches checklist)
    "disruption_type":      "",    # str  — "Heavy Rain" | "Extreme Heat" | "High AQI"
    "zone":                 "",    # str  — worker's registered delivery zone
    "start_time":           "",    # str  — ISO 8601 or "HH:MM" — disruption start
    "end_time":             "",    # str  — ISO 8601 or "HH:MM" — disruption end
    "time_window_hours":    0.0,   # float — total duration of disruption

    # ── Environmental Trigger Data (auto claims only) ─────────────────────
    "rain_mm_hr":           0.0,   # float — mm/hr at time of trigger
    "temp_c":               0.0,   # float — °C at time of trigger
    "aqi":                  0,     # int   — Air Quality Index at trigger time

    # ── Financial ─────────────────────────────────────────────────────────
    "estimated_loss":       0,     # int   — INR, self-reported or system estimate
    "actual_earnings":      0,     # int   — INR, real earnings during disruption period
    "income_loss":          0,     # int   — INR, validated loss after PoW check
    "eligible_payout":      0,     # int   — INR, min(income_loss * 0.66, tier_max)
    "tier_max_payout":      0,     # int   — INR, derived from worker's plan tier

    # ── Proof / Manual Submission ─────────────────────────────────────────
    "description":          "",    # str   — free-text disruption description
    "proof_urls":           [],    # list[str] — uploaded photo/doc URLs

    # ── Fraud & Verification ──────────────────────────────────────────────
    "fraud_risk":           "",    # str   — "low" | "medium" | "high"
    "fraud_flags":          [],    # list[str] — individual rule violations fired
    "pow_gps_ok":           None,  # bool  — GPS movement within expected range
    "pow_delivery_ok":      None,  # bool  — delivery count plausible for window

    # ── Status Lifecycle ──────────────────────────────────────────────────
    # under_review → verifying → approved | rejected | manual_review
    "status":               "",    # str   — current lifecycle stage
    "rejection_reason":     "",    # str   — populated only when status == "rejected"

    # ── Payout ────────────────────────────────────────────────────────────
    "payout_upi":           "",    # str   — UPI handle (from worker document)
    "payout_status":        "",    # str   — "pending" | "initiated" | "credited" | "failed"
    "razorpay_payout_id":   "",    # str   — returned by Razorpay Payout API
    "retry_eligible":       False, # bool  — if true, payout can be retried
    "last_upi_attempted":   "",    # str   — last UPI ID used for payout attempt

    # ── Timestamps ────────────────────────────────────────────────────────
    "created_at":           "",    # str   — ISO 8601 UTC
    "updated_at":           "",    # str   — ISO 8601 UTC
    "resolved_at":          "",    # str   — ISO 8601 UTC when status is final
}

# ---------------------------------------------------------------------------
# Claim Status Enum — canonical lifecycle values
# ---------------------------------------------------------------------------
class ClaimStatus(str, Enum):
    """All valid claim statuses in the Figgy pipeline.

    Lifecycle:
        under_review → verifying → approved | rejected | manual_review → paid
    """
    UNDER_REVIEW   = "under_review"
    VERIFYING      = "verifying"
    APPROVED       = "approved"
    REJECTED       = "rejected"
    MANUAL_REVIEW  = "manual_review"
    PAID           = "paid"
    PAYMENT_FAILED = "payment_failed"
    ESCALATED      = "escalated"


class Database:
    """Robust MongoDB handler with Memory Mode fallback."""
    def __init__(self):
        self._client = None
        self._db = None
        # Default fallback to Local for stability
        self.local_uri = os.getenv("MONGO_URI_LOCAL", "mongodb://localhost:27017/figgy")
        self.atlas_uri = os.getenv("MONGO_URI_ATLAS")
        self.db_name = os.getenv("DB_NAME", "figgy")

    @property
    def is_db_enabled(self):
        # We manually toggle this based on the USE_DB config
        # Safe access using current_app.config
        return current_app.config.get('USE_DB', False)

    def connect(self):
        """Attempts to connect to Atlas then Local MongoDB."""
        if not self.is_db_enabled:
            logger.info("⚠️  DEMO MODE: MongoDB is disabled. Using In-Memory Storage.")
            return False

        # 1. Try Atlas
        if self.atlas_uri:
            try:
                temp_client = MongoClient(self.atlas_uri, serverSelectionTimeoutMS=5000)
                temp_client.server_info()
                self._client = temp_client
                logger.info("✅ Connected to MongoDB Atlas.")
                return True
            except (ServerSelectionTimeoutError, ConfigurationError) as e:
                logger.warning(f"❌ Atlas failed: {e}")

        # 2. Try Local
        try:
            temp_client = MongoClient(self.local_uri, serverSelectionTimeoutMS=2000)
            temp_client.server_info()
            self._client = temp_client
            logger.info("✅ Connected to Local MongoDB.")
            return True
        except Exception as e:
            logger.error(f"❌ Local MongoDB failed: {e}")
            return False

    def insert_worker(self, worker_doc: dict):
        """Generic insert that routes to DB or Memory."""
        if self.is_db_enabled and (self._client or self.connect()):
            try:
                res = self.client[self.db_name].workers.insert_one(worker_doc)
                worker_doc.pop("_id", None)
                return True
            except Exception as e:
                logger.error(f"DB Insert Error: {e}. Falling back to Memory.")
        
        # Memory Fallback
        logger.info(f"Storing Worker '{worker_doc.get('worker_id')}' in Memory...")
        memory_workers.append(worker_doc)
        return True

    def get_all_workers(self):
        """Generic fetch all."""
        if self.is_db_enabled and (self._client or self.connect()):
            try:
                # Return list for simplicity
                return list(self.client[self.db_name].workers.find({}, {"_id": 0}))
            except Exception as e:
                logger.error(f"DB Fetch Error: {e}")
        
        return memory_workers

    def get_worker(self, worker_id: str) -> dict | None:
        if self.is_db_enabled and (self._client or self.connect()):
            try:
                return self.client[self.db_name].workers.find_one({"worker_id": worker_id}, {"_id": 0})
            except Exception as e:
                logger.error(f"DB Fetch Error: {e}")
        for w in memory_workers:
            if w.get("worker_id") == worker_id:
                return w
        return None

    def update_worker(self, worker_id: str, update_dict: dict) -> bool:
        if self.is_db_enabled and (self._client or self.connect()):
            try:
                res = self.client[self.db_name].workers.update_one({"worker_id": worker_id}, {"$set": update_dict})
                return res.modified_count > 0
            except Exception as e:
                logger.error(f"DB Update Error: {e}")
        for w in memory_workers:
            if w.get("worker_id") == worker_id:
                w.update(update_dict)
                return True
        return False

    def get_workers_by_zone_and_status(self, zone: str, status: str) -> list[dict]:
        """
        Return all workers matching the given zone and policy_status.

        Parameters
        ----------
        zone   : str — e.g. "North", "South" (case-insensitive match)
        status : str — e.g. "active", "inactive"

        Returns
        -------
        list[dict] — matching worker documents (no MongoDB _id field)
        """
        zone_lower   = zone.lower()
        status_lower = status.lower()

        if self.is_db_enabled and (self._client or self.connect()):
            try:
                cursor = self.client[self.db_name].workers.find(
                    {
                        "zone":          {"$regex": f"^{zone}$", "$options": "i"},
                        "policy_status": status_lower,
                    },
                    {"_id": 0},
                )
                return list(cursor)
            except Exception as e:
                logger.error(f"DB get_workers_by_zone_and_status Error: {e}")

        # Memory fallback — case-insensitive zone + status match
        return [
            w for w in memory_workers
            if w.get("zone", "").lower()          == zone_lower
            and w.get("policy_status", "").lower() == status_lower
        ]

    def get_todays_claim(self, worker_id: str) -> dict | None:
        """
        Return the first claim filed by worker_id today (UTC date), or None.

        Used by the scheduler to prevent duplicate auto-claims within the
        same calendar day (UTC).

        Parameters
        ----------
        worker_id : str — e.g. "GS-123456"

        Returns
        -------
        dict | None — claim document if one exists today, else None
        """
        today_prefix = datetime.utcnow().strftime("%Y-%m-%d")   # "2026-03-30"

        if self.is_db_enabled and (self._client or self.connect()):
            try:
                doc = self.client[self.db_name].claims.find_one(
                    {
                        "worker_id":  worker_id,
                        "created_at": {"$regex": f"^{today_prefix}"},
                    },
                    {"_id": 0},
                )
                return doc
            except Exception as e:
                logger.error(f"DB get_todays_claim Error: {e}")

        # Memory fallback — check created_at prefix
        for claim in memory_claims:
            if (
                claim.get("worker_id") == worker_id
                and claim.get("created_at", "").startswith(today_prefix)
            ):
                return claim
        return None

    def check_duplicate_claim(self, worker_id: str, disruption_type: str, exclude_claim_id: str = None) -> dict | None:
        """
        Step 0 Idempotency Check:
        Query the database for any existing claim where:
        - worker_id == current worker
        - disruption_type == current disruption_type
        - created_at DATE == today's date (UTC)
        - status NOT IN ["rejected", "payment_failed"]
        """
        today_prefix = datetime.utcnow().strftime("%Y-%m-%d")
        
        query = {
            "worker_id": worker_id,
            "disruption_type": disruption_type,
            "created_at": {"$regex": f"^{today_prefix}"},
            "status": {"$nin": ["rejected", "payment_failed"]}
        }
        if exclude_claim_id:
            query["claim_id"] = {"$ne": exclude_claim_id}

        if self.is_db_enabled and (self._client or self.connect()):
            try:
                return self.client[self.db_name].claims.find_one(query, {"_id": 0})
            except Exception as e:
                logger.error(f"DB check_duplicate_claim Error: {e}")

        # Memory fallback
        for c in memory_claims:
            if (c.get("worker_id") == worker_id and 
                c.get("disruption_type") == disruption_type and 
                c.get("created_at", "").startswith(today_prefix) and 
                c.get("status") not in ["rejected", "payment_failed"]):
                if exclude_claim_id and c.get("claim_id") == exclude_claim_id:
                    continue
                return c
        return None

    def get_workers_with_active_claims_today(self, worker_ids: list[str], disruption_type: str) -> list[str]:
        """
        Bulk DB query to find workers who already have an active claim today 
        for the same disruption type.
        """
        today_prefix = datetime.utcnow().strftime("%Y-%m-%d")
        
        if self.is_db_enabled and (self._client or self.connect()):
            try:
                cursor = self.client[self.db_name].claims.find({
                    "worker_id": {"$in": worker_ids},
                    "disruption_type": disruption_type,
                    "created_at": {"$regex": f"^{today_prefix}"},
                    "status": {"$nin": ["rejected", "payment_failed"]}
                }, {"worker_id": 1, "_id": 0})
                return list(set([doc["worker_id"] for doc in cursor]))
            except Exception as e:
                logger.error(f"DB get_workers_with_active_claims_today Error: {e}")

        # Memory fallback
        seen = []
        for c in memory_claims:
            wid = c.get("worker_id")
            if (wid in worker_ids and 
                c.get("disruption_type") == disruption_type and 
                c.get("created_at", "").startswith(today_prefix) and 
                c.get("status") not in ["rejected", "payment_failed"]):
                seen.append(wid)
        return list(set(seen))

    # ===================================================================
    # CLAIM PERSISTENCE  (same pattern as worker methods above)
    # MongoDB collection: "claims"  |  Fallback: memory_claims[]
    # ===================================================================

    def save_claim(self, claim_doc: dict) -> str:
        """Insert a new claim. Returns the claim_id."""
        claim_id = claim_doc.get("claim_id", "")

        if self.is_db_enabled and (self._client or self.connect()):
            try:
                self.client[self.db_name].claims.insert_one(claim_doc)
                claim_doc.pop("_id", None)  # remove Mongo ObjectId from dict
                logger.info(f"Claim '{claim_id}' stored in MongoDB.")
                return claim_id
            except Exception as e:
                logger.error(f"DB Claim Insert Error: {e}. Falling back to Memory.")

        # Memory Fallback
        logger.info(f"Storing Claim '{claim_id}' in Memory...")
        memory_claims.append(claim_doc)
        return claim_id

    def get_claim(self, claim_id: str) -> dict | None:
        """Fetch a single claim by claim_id. Returns None if not found."""
        if self.is_db_enabled and (self._client or self.connect()):
            try:
                doc = self.client[self.db_name].claims.find_one(
                    {"claim_id": claim_id}, {"_id": 0}
                )
                return doc
            except Exception as e:
                logger.error(f"DB Claim Fetch Error: {e}")

        # Memory Fallback
        for c in memory_claims:
            if c.get("claim_id") == claim_id:
                return c
        return None

    def get_claims_by_worker(self, worker_id: str) -> list[dict]:
        """Fetch all claims for a given worker_id, newest-first."""
        if self.is_db_enabled and (self._client or self.connect()):
            try:
                cursor = self.client[self.db_name].claims.find(
                    {"worker_id": worker_id}, {"_id": 0}
                ).sort("created_at", -1)
                return list(cursor)
            except Exception as e:
                logger.error(f"DB Claims-by-Worker Fetch Error: {e}")

        # Memory Fallback — filter + sort newest-first
        worker_claims = [c for c in memory_claims if c.get("worker_id") == worker_id]
        worker_claims.sort(key=lambda c: c.get("created_at", ""), reverse=True)
        return worker_claims

    def get_all_claims(self) -> list[dict]:
        """Fetch all claims, newest-first."""
        if self.is_db_enabled and (self._client or self.connect()):
            try:
                cursor = self.client[self.db_name].claims.find({}, {"_id": 0}).sort("created_at", -1)
                return list(cursor)
            except Exception as e:
                logger.error(f"DB Claims Fetch Error: {e}")

        # Memory Fallback — sort newest-first
        all_claims = list(memory_claims)
        all_claims.sort(key=lambda c: c.get("created_at", ""), reverse=True)
        return all_claims

    def update_claim_status(self, claim_id: str, status: str, extra_fields: dict = None) -> bool:
        """Update a claim's status and optionally merge extra_fields into the doc."""
        if extra_fields is None:
            extra_fields = {}

        update_payload = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat() + "Z",
            **extra_fields,
        }

        if self.is_db_enabled and (self._client or self.connect()):
            try:
                result = self.client[self.db_name].claims.update_one(
                    {"claim_id": claim_id},
                    {"$set": update_payload}
                )
                if result.modified_count > 0:
                    logger.info(f"Claim '{claim_id}' updated to '{status}' in MongoDB.")
                    return True
                else:
                    logger.warning(f"Claim '{claim_id}' not found in MongoDB for update.")
                    return False
            except Exception as e:
                logger.error(f"DB Claim Update Error: {e}. Falling back to Memory.")

        # Memory Fallback — find and mutate in place
        for c in memory_claims:
            if c.get("claim_id") == claim_id:
                c.update(update_payload)
                logger.info(f"Claim '{claim_id}' updated to '{status}' in Memory.")
                return True

        logger.warning(f"Claim '{claim_id}' not found in Memory for update.")
        return False

    @property
    def client(self):
        if self._client is None and self.is_db_enabled:
            self.connect()
        return self._client

# Singleton
db_handler = Database()

class PolicyTermsStore:
    """Handles Terms & Conditions data with multiregional support."""
    def __init__(self):
        self._terms = [
            {
                "id": 1,
                "version": "1.0",
                "effective_from": "2026-03-01",
                "language": "English",
                "sections": [
                    {"title": "1. Introduction", "content": "GigShield is a parametric micro-insurance product designed exclusively for food delivery partners (Zomato, Swiggy, etc.). It provides weekly protection against loss of income caused by external disruptions like heavy rain, extreme heat, or severe pollution."},
                    {"title": "2. Coverage", "content": "We cover only loss of income due to defined parametric triggers in your registered delivery zone. Payout is fixed and automatic — no need to file a claim or prove your loss."},
                    {"title": "3. What is NOT Covered (Exclusions)", "content": "Any health-related issues, medical expenses, accidents or vehicle damage, or loss due to personal reasons are not covered."},
                    {"title": "4. Policy Period & Premium", "content": "Your policy is valid for 7 days (weekly cycle). Premium is charged weekly and auto-renews unless you cancel."},
                    {"title": "5. Claim Process", "content": "Claims are fully automatic (zero-touch). When a trigger is detected, payout is processed automatically within 24–48 hours."},
                    {"title": "6. Your Responsibilities", "content": "Keep your location and contact details updated. GPS spoofing will lead to policy cancellation."},
                    {"title": "7. Fraud Prevention", "content": "We use AI + location validation to prevent fraudulent claims. Detected fraud will result in immediate cancellation."},
                    {"title": "8. Cancellation & Refund", "content": "You can cancel anytime before renewal. No refund for the current active week once payment is made."},
                    {"title": "9. Dispute Resolution", "content": "Any disputes will be subject to the laws of India and resolved through arbitration in Chennai."},
                    {"title": "10. Important Note", "content": "This is a parametric product — payout depends only on objective weather/pollution data, not on your actual earnings loss."}
                ],
                "is_active": True
            },
            {
                "id": 2,
                "version": "1.0",
                "effective_from": "2026-03-01",
                "language": "Hindi",
                "sections": [
                    {"title": "1. परिचय", "content": "GigShield एक पैरामीट्रिक माइक्रो-इंश्योरेंस उत्पाद है जो विशेष रूप से फूड डिलीवरी पार्टनर्स के लिए बनाया गया है।"},
                    {"title": "2. कवरेज", "content": "हम केवल आपके पंजीकृत डिलीवरी क्षेत्र में परिभाषित पैरामीट्रिक ट्रिगर्स के कारण आय की हानि को कवर करते हैं।"},
                    {"title": "3. क्या कवर नहीं है (अपवाद)", "content": "स्वास्थ्य संबंधी समस्याएं, चिकित्सा व्यय, दुर्घटनाएं या वाहन की मरम्मत कवर नहीं है।"},
                    {"title": "4. पॉलिसी अवधि और प्रीमियम", "content": "आपकी पॉलिसी 7 दिनों (साप्ताहिक चक्र) के लिए वैध है। प्रीमियम साप्ताहिक रूप से लिया जाता है।"},
                    {"title": "5. दावा प्रक्रिया", "content": "दावे पूरी तरह से स्वचालित (जीरो-टच) हैं।"},
                    {"title": "6. आपकी जिम्मेदारियां", "content": "अपनी लोकेशन और संपर्क विवरण अपडेट रखें।"},
                    {"title": "7. धोखाधड़ी रोकथाम", "content": "धोखाधड़ी के परिणामस्वरूप पॉलिसी तुरंत रद्द कर दी जाएगी।"},
                    {"title": "8. रद्दीकरण और धनवापसी", "content": "आप नवीनीकरण से पहले किसी भी समय रद्द कर सकते हैं।"},
                    {"title": "9. विवाद समाधान", "content": "कोई भी विवाद भारत के कानूनों के अधीन होगा।"},
                    {"title": "10. महत्वपूर्ण नोट", "content": "यह एक पैरामीट्रिक उत्पाद है - भुगतान केवल वस्तुनिष्ठ मौसम/प्रदूषण डेटा पर निर्भर करता है।"}
                ],
                "is_active": True
            }
        ]

    def get_terms(self, language="English", version="1.0"):
        """Fetch active terms for a given language and version."""
        for t in self._terms:
            if t["language"] == language and t["version"] == version and t["is_active"]:
                return t
        # Fallback to English 1.0
        return self._terms[0]

    def get_current_version(self):
        return "1.0"

# Terms Storage Singleton
terms_store = PolicyTermsStore()
