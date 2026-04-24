import sys
import os

# Ensure the app module can be found
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.utils.payout import RazorpayPayoutService
from app import create_app

def run_tests():
    print("Testing Razorpay Payout Edge Cases...")
    app = create_app()
    with app.app_context():
        svc = RazorpayPayoutService()
    
    # Test valid mock payout
    print("\n--- Test 1: Valid Mock Payout ---")
    valid_worker = {"worker_id": "W-123", "upi_id": "success@ybl", "name": "Test User", "phone": "1234567890"}
    res1 = svc.initiate_payout(valid_worker, "FIG-SUCCESS-1", 100.0)
    print(f"Result: {res1}")

    # Test failed mock payout via upi_id
    print("\n--- Test 2: Failed Mock Payout via upi_id (fail@ybl) ---")
    fail_worker = {"worker_id": "W-456", "upi_id": "fail@ybl", "name": "Fail User", "phone": "0987654321"}
    res2 = svc.initiate_payout(fail_worker, "FIG-FAILURE-1", 50.0)
    print(f"Result: {res2}")

    # Test failed mock payout via claim_id containing FAIL
    print("\n--- Test 3: Failed Mock Payout via claim_id (FAIL) ---")
    res3 = svc.initiate_payout(valid_worker, "FIG-FAIL-2", 75.0)
    print(f"Result: {res3}")

if __name__ == "__main__":
    run_tests()
