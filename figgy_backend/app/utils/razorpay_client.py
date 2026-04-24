import os
import time
import requests
import logging

logger = logging.getLogger("RAZORPAY_CLIENT")

# Idempotency cache: claim_id -> {success: bool, rrn: str, message: str}
_payout_cache = {}

def send_payout(upi_id: str, amount: float, claim_id: str) -> dict:
    if claim_id in _payout_cache:
        logger.info(f"[PAYOUT] Returning cached result for claim {claim_id}")
        return _payout_cache[claim_id]

    demo_mode = str(os.getenv("DEMO_MODE", "false")).lower() == "true"
    
    if demo_mode:
        if upi_id == "fail@ybl":
            time.sleep(2)
            result = {"success": False, "rrn": None, "message": "UPI transfer rejected — inactive VPA"}
        elif upi_id.endswith("@ybl") or upi_id.endswith("@paytm"):
            time.sleep(1.5)
            result = {"success": True, "rrn": f"RRN{claim_id[:8].upper()}", "message": "Transfer successful"}
        else:
            time.sleep(1)
            result = {"success": True, "rrn": f"DEMO{claim_id[:6].upper()}", "message": "Demo payout simulated"}
        
        _payout_cache[claim_id] = result
        return result

    # REAL MODE
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    account_number = os.getenv("RAZORPAY_ACCOUNT_NUMBER")
    
    if not all([key_id, key_secret, account_number]):
        result = {"success": False, "rrn": None, "message": "Razorpay keys not configured"}
        _payout_cache[claim_id] = result
        return result

    try:
        # Create a contact
        contact_payload = {
            "name": f"Worker_{claim_id}",
            "reference_id": claim_id
        }
        contact_res = requests.post(
            "https://api.razorpay.com/v1/contacts",
            json=contact_payload,
            auth=(key_id, key_secret)
        )
        if not contact_res.ok:
            logger.error(f"[PAYOUT] Contact creation failed: {contact_res.text}")
            result = {"success": False, "rrn": None, "message": f"Contact creation failed: {contact_res.text}"}
            _payout_cache[claim_id] = result
            return result
        
        contact_id = contact_res.json().get("id")

        # Create fund account
        fund_account_payload = {
            "contact_id": contact_id,
            "account_type": "vpa",
            "vpa": {
                "address": upi_id
            }
        }
        fa_res = requests.post(
            "https://api.razorpay.com/v1/fund_accounts",
            json=fund_account_payload,
            auth=(key_id, key_secret)
        )
        if not fa_res.ok:
            logger.error(f"[PAYOUT] Fund account creation failed: {fa_res.text}")
            result = {"success": False, "rrn": None, "message": f"Fund account failed: {fa_res.text}"}
            _payout_cache[claim_id] = result
            return result
            
        fund_account_id = fa_res.json().get("id")

        # Initiate payout
        payout_payload = {
            "account_number": account_number,
            "fund_account_id": fund_account_id,
            "amount": int(amount * 100),
            "currency": "INR",
            "mode": "UPI",
            "purpose": "payout",
            "reference_id": claim_id
        }
        
        payout_res = requests.post(
            "https://api.razorpay.com/v1/payouts",
            json=payout_payload,
            auth=(key_id, key_secret)
        )
        
        if payout_res.ok:
            data = payout_res.json()
            result = {"success": True, "rrn": data.get("id"), "message": "Transfer initiated"}
        else:
            logger.error(f"[PAYOUT] Payout failed: {payout_res.text}")
            result = {"success": False, "rrn": None, "message": f"Payout failed: {payout_res.text}"}

    except Exception as e:
        logger.error(f"[PAYOUT] Error: {e}")
        result = {"success": False, "rrn": None, "message": str(e)}

    _payout_cache[claim_id] = result
    return result
