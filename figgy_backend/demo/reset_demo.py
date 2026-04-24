import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app
from app.models import db

def reset_demo():
    load_dotenv()
    app = create_app()
    with app.app_context():
        worker_id = "ravi_demo_123"
        print(f"Rolling back all Demo Sandbox Data for '{worker_id}'...")
        
        claims_deleted = db.claims.delete_many({"worker_id": worker_id}).deleted_count
        workers_deleted = db.workers.delete_many({"worker_id": worker_id}).deleted_count
        
        print(f"Purged {claims_deleted} demo claims from MongoDB.")
        print(f"Purged {workers_deleted} demo workers from MongoDB.")
        print("\n\033[92mDemo environment reset successfully. Ready for next run.\033[0m")

if __name__ == "__main__":
    reset_demo()
