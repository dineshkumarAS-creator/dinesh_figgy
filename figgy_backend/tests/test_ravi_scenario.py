import os
import pytest
from app import create_app
from app.models import db
from app.utils.claim_processor import verify_and_payout

@pytest.fixture
def client():
    os.environ['DEMO_MODE'] = 'true'
    app = create_app()
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        with app.app_context():
            # Teardown before just in case
            db.workers.delete_many({"worker_id": "ravi_test"})
            db.claims.delete_many({"worker_id": "ravi_test"})
            
            # Setup Ravi Data
            db.workers.insert_one({
                "worker_id": "ravi_test",
                "name": "Ravi",
                "phone": "9999912345",
                "selected_tier": "Smart",
                "avg_daily_earnings": 600,
                "daily_hours": 8,
                "avg_deliveries": 18,
                "upi_id": "ravi@paytm",
                "zone_id": "koramangala_3",
                "last_session_gps_km": 1.2,
                "last_session_deliveries": 2,
                "last_session_online_mins": 30
            })
            yield client
            
            # Final Teardown
            db.workers.delete_many({"worker_id": "ravi_test"})
            db.claims.delete_many({"worker_id": "ravi_test"})

def test_ravi_auto_trigger_pipeline(client):
    # a. POST /api/claim/auto_trigger with zone_id
    res = client.post('/api/claim/auto_trigger', json={
        "zone_id": "koramangala_3",
        "trigger_type": "RAIN",
        "detected_value": 52
    })
    
    # We will assume this route exists or we pass checking 200/201.
    assert res.status_code in [200, 201], f"Expected success but got {res.status_code}. Route might be missing."
    
    # b. Assert 1 claim created with status verifying
    claim = db.claims.find_one({"worker_id": "ravi_test"})
    assert claim is not None, "Claim not successfully triggered from API"
    assert claim["status"] == "verifying", "Initial claim DB state is not 'verifying'"
    
    claim_id = claim["claim_id"]
    
    # c. Manually call verify_and_payout synchronously
    verify_and_payout(claim_id)
    
    updated_claim = db.claims.find_one({"claim_id": claim_id})
    assert updated_claim is not None
    
    # d. Assert fraud_check is LOW risk
    fraud_check = updated_claim.get("fraud_check", {})
    assert fraud_check.get("risk_level") == "LOW", "Ravi's claim was falsely flagged for high risk"
    
    # e. Assert payout_amount > 0 and <= 500 (Smart Tier cap)
    payout = updated_claim.get("payout_amount", 0)
    assert payout > 0, "Payout amount didn't populate"
    assert payout <= 500, "Payout amount breached Smart Tier protection cap"
    
    # f. Assert claim status is "paid"
    assert updated_claim.get("status") == "paid", "Claim pipeline failed to reach terminal 'paid' state"
    
    # g. Expected earnings is pytest.approx(225, abs=10)
    breakdown = updated_claim.get("breakdown", {})
    from pytest import approx
    assert breakdown.get("expected_earnings", 0) == approx(225, abs=10), "Calculated expected earnings don't map to 600/8*3 formula"
