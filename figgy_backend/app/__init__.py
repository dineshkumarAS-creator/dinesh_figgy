from flask import Flask, jsonify
from flask_cors import CORS
from app.routes.worker import worker_bp
from app.routes.terms import terms_bp
from app.routes.payment import payment_bp
from app.routes.payout import payout_bp
from app.routes.claims import claims_bp
from app.routes.weather import weather_bp
from app.routes.demo import demo_bp
from app.routes.admin import admin_bp
from app.routes.telemetry_routes import telemetry_bp
from app.routes.demand import demand_bp
from app.routes.radar import radar_bp
from app.utils.scheduler import init_scheduler

def create_app():
    """App factory function to initialize Flask application."""
    app = Flask(__name__)
    
    # Configure CORS explicitly for all routes and origins
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Load settings from config object
    app.config.from_object('config.Config')

    app.register_blueprint(worker_bp)
    app.register_blueprint(terms_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(payout_bp)
    app.register_blueprint(claims_bp)
    app.register_blueprint(weather_bp)
    app.register_blueprint(demo_bp)
    app.register_blueprint(telemetry_bp)
    app.register_blueprint(demand_bp)
    app.register_blueprint(radar_bp)
    
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Ensure MongoDB indexes for claims (only runs when USE_DB=True)
    with app.app_context():
        _ensure_claim_indexes(app)

    # Start APScheduler — parametric weather trigger engine
    from app.utils.scheduler import scheduler
    init_scheduler(app)
    
    # Register shutdown cleanup
    import atexit
    atexit.register(lambda: scheduler.shutdown())

    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({"status": "ok"}), 200

    return app


def _ensure_claim_indexes(app: Flask):
    """Create MongoDB indexes for the claims collection on startup.
    Runs only when USE_DB=True. Safe to call on every startup (idempotent).
    """
    from app.models import db_handler
    import logging
    logger = logging.getLogger("FIGGY_APP")

    if not app.config.get("USE_DB", False):
        return  # in-memory mode — no indexes needed

    try:
        client = db_handler.client
        if client is None:
            return
        db = client[db_handler.db_name]
        # Unique index on claim_id
        db.claims.create_index("claim_id", unique=True, background=True)
        # Non-unique index on worker_id (for get_claims_by_worker queries)
        db.claims.create_index("worker_id", background=True)
        logger.info("✅ MongoDB claim indexes ensured (claim_id unique, worker_id).")
    except Exception as e:
        logger.warning(f"⚠️  Could not create claim indexes: {e}")
