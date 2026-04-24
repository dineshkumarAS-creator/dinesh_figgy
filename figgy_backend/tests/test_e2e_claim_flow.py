import pytest
from app import create_app
from app.models import db_handler

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['USE_DB'] = False  # Force in-memory for predictable tests
    
    with app.test_client() as client:
        with app.app_context():
            # Inject mock worker GS-OVVSRL
            worker_doc = {
                "worker_id": "GS-OVVSRL",
                "phone": "+919876543210",
                "swiggy_id": "SW-11223",
                "zone": "North",
                "tier": "Smart",
                "policy_status": "active",
                "avg_daily_earnings": 800,
                "daily_hours": 8,
                "daily_deliveries": 15,
                "upi_id": "ravi@okicici"
            }
            # Avoid inserting duplicate if tests run multiple times
            if not any(w["worker_id"] == "GS-OVVSRL" for w in db_handler.get_all_workers()):
                db_handler.insert_worker(worker_doc)
            yield client


def test_manual_claim_e2e(client):
    # Step 1: POST /api/claim/manual
    response = client.post('/api/claim/manual', json={
        "worker_id": "GS-OVVSRL",
        "claim_type": "Heavy Rain",
        "description": "Stuck under a bridge for 2 hours.",
        "start_time": "14:00",
        "end_time": "16:00",
        "estimated_loss": 200,
        "proof_urls": ["http://example.com/proof.jpg"]
    })
    
    assert response.status_code == 201
    data = response.get_json()
    assert data["status"] == "success"
    
    claim_id = data["claim"]["claim_id"]
    assert claim_id.startswith("FIG-")
    
    # Step 2: GET status
    status_response = client.get(f'/api/claim/status/{claim_id}')
    assert status_response.status_code == 200
    status_data = status_response.get_json()
    assert status_data["claim"]["status"] in ["under_review", "verifying", "approved", "paid", "rejected", "manual_review"]
    
    # Step 4: List claims
    list_response = client.get('/api/claim/list/GS-OVVSRL')
    assert list_response.status_code == 200
    list_data = list_response.get_json()
    assert any(c["claim_id"] == claim_id for c in list_data["claims"])
    
    # Assert specific required fields exist
    claim_doc = next(c for c in list_data["claims"] if c["claim_id"] == claim_id)
    assert "estimated_loss" in claim_doc
    assert "claim_type" in claim_doc


def test_auto_trigger_e2e(client):
    # Trigger demo endpoint
    response = client.post('/api/demo/trigger_rain', json={
        "zone": "North",
        "rain_mm_hr": 52
    })
    assert response.status_code == 200
    data = response.get_json()
    assert len(data.get("claims_created", [])) > 0
    
    # Verify orchestrated completion
    claim_id = data["claims_created"][0]
    status_resp = client.get(f'/api/claim/status/{claim_id}')
    assert status_resp.status_code == 200
    claim_data = status_resp.get_json()["claim"]
    
    assert claim_data["status"] in ["verifying", "approved", "paid", "manual_review", "rejected"]
    # The sync trigger flow should score fraud natively
    assert claim_data.get("fraud_risk") is not None


def test_fraud_high_risk():
    from app.utils.fraud import score_fraud_risk
    
    # Submit claim with impossible delivery_rate (50 deliveries in 1 hour)
    claim = {
        "claim_id": "FIG-FRAUD",
        "time_window_hours": 1.0,
    }
    worker = {
        "worker_id": "GS-OVVSRL",
        "tier": "Smart"
    }
    proof = {
        "delivery_count": 50,  
        "gps_distance_km": 0.5
    }
    
    fraud_result = score_fraud_risk({**claim, **proof}, worker)
    assert fraud_result["risk_level"] == "high"
    assert "Impossible delivery rate (50.0/hr)" in fraud_result["flags"]


def test_payout_calculation():
    from app.utils.calculations import calculate_expected_earnings, calculate_income_loss, calculate_eligible_payout
    
    # Worker: avg_daily_earnings=800, tier=Smart
    # Claim: time_window_hours=4, actual_earnings=50
    # Expected: expected_earnings=400, loss=350, payout=min(231, 500)=231
    expected = calculate_expected_earnings({"avg_daily_earnings": 800, "daily_hours": 8}, 4.0)
    assert expected == 400
    
    loss = calculate_income_loss(400, 50)
    assert loss == 350
    
    # Eligible payout for Smart is 66% of loss up to Rs. 500
    payout = calculate_eligible_payout(350, tier="Smart")
    assert payout == 231


def test_all_endpoints_respond(client):
    # GET /health → 200
    health = client.get('/health')
    assert health.status_code == 200
    
    # POST /api/claim/manual with bad data → 400 (not 500)
    bad_post = client.post('/api/claim/manual', json={})
    assert bad_post.status_code == 400
    
    # GET /api/claim/status/FIG-9999 → 404 (not 500)
    missing_status = client.get('/api/claim/status/FIG-999999')
    assert missing_status.status_code == 404
    
    # GET /api/claim/list/nonexistent → 200 with empty list (not 500)
    empty_list = client.get('/api/claim/list/GS-NONEXISTENT')
    assert empty_list.status_code == 200
    assert empty_list.get_json().get("claims") == []
