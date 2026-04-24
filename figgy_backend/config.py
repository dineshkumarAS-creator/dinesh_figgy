import os
from dotenv import load_dotenv

# Load .env from this backend folder reliably (independent of launch cwd)
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DOTENV_PATH = os.path.join(_BASE_DIR, ".env")
load_dotenv(dotenv_path=_DOTENV_PATH)

class Config:
    """Config class for the Flask application."""
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/figgy")
    # Toggle MongoDB: Set to False to use In-Memory storage (Demo Mode)
    USE_DB = os.getenv("USE_DB", "False").lower() == "true"

    # Razorpay Payment Gateway (subscription checkout)
    RAZORPAY_KEY_ID     = os.getenv("RAZORPAY_KEY_ID")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

    # Razorpay X Payout API (UPI disbursement — separate from payment gateway)
    RAZORPAY_ACCOUNT_NUMBER = os.getenv("RAZORPAY_ACCOUNT_NUMBER", "")

    # OpenWeatherMap — parametric trigger engine
    # Sign up free at https://openweathermap.org/api
    # Leave blank to run scheduler in DEMO mode (simulated rain trigger)
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

    # APScheduler — how often to poll weather per zone (minutes)
    SCHEDULER_INTERVAL_MINUTES = int(os.getenv("SCHEDULER_INTERVAL_MINUTES", 15))

    # APScheduler — expose /scheduler/jobs debug endpoint
    SCHEDULER_API_ENABLED = os.getenv("SCHEDULER_API_ENABLED", "True").lower() == "true"

    # Disruption Radar Auto-Protection Thresholds
    INCOME_LOSS_THRESHOLD = 200   # INR — minimum loss to trigger auto-claim
    RISK_SCORE_THRESHOLD = 60     # 0–100 — minimum risk to trigger auto-claim

