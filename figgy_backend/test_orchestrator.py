import time
import logging
from app import create_app
from app.models import db_handler
from app.utils.scheduler import _trigger_zone

logging.basicConfig(level=logging.INFO)

app = create_app()
with app.app_context():
    print("\n--- 1. INSERTING MOCK WORKER ---")
    worker = {
        "worker_id": "GS-DEMO123",
        "zone": "T Nagar",
        "avg_daily_earnings": 800,
        "daily_hours": 8,
        "policy_status": "active",
        "tier": "Smart",
        "daily_deliveries": 15,
        "gps_distance_today_km": 10,
        "recent_deliveries_today": 5
    }
    db_handler.insert_worker(worker)

    print("\n--- 2. TRIGGERING WEATHER DISRUPTION ---")
    demo_weather = {"rain_mm_hr": 60.0, "temp_c": 30.0, "aqi": 100}
    _trigger_zone(app, "T Nagar", demo_weather)

    print("\n--- 3. WAITING FOR APSCHEDULER TO VERIFY AND PAYOUT ---")
    time.sleep(5)
    
    # Check claim updates
    claims = db_handler.get_claims_by_worker("GS-DEMO123")
    if claims:
        print("\n--- FINAL CLAIM STATUS ---")
        for k, v in claims[0].items():
            if v is not None and v != "":
                print(f"{k}: {v}")
