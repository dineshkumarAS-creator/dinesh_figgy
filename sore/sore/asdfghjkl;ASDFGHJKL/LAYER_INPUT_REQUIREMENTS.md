# FIGGY System - Input Requirements by Layer

## Layer 0: Event Detection
### From External Sources

**Government Feed Connector** needs:
```
1. Government data sources:
   - data.gov.in REST/RSS feeds
   - PIB (Press Information Bureau) RSS feeds
   - State-specific government feeds (configurable URLs)
   
2. Search keywords from config:
   - curfew, strike, bandh, protest, section 144, shutdown
   
3. Parsing parameters:
   - Event title, summary, URL, timestamp
   - Location/zone information (if available)
```

**News Feed Connector** needs:
```
1. News API credentials:
   - NewsAPI.org API key
   - GNews API key
   
2. News search queries:
   - Keywords array: ["curfew", "bandh", "strike", ...]
   
3. Article attributes:
   - Headline, source, URL, published date
   - News content (for keyword matching)
```

**Output**: Kafka `events` topic with:
```json
{
  "event_type": "curfew|strike|bandh|protest",
  "affected_city": "string",
  "affected_zones": ["zone1", "zone2"],
  "severity": 1-5,
  "source": "govt|news",
  "source_url": "string",
  "raw_title": "string",
  "timestamp_utc": "ISO8601",
  "is_trigger_condition": true|false
}
```

---

## Layer 1: Kafka Infrastructure
### Event Topics Require

**From your app**:
```
1. Kafka cluster configuration:
   - Bootstrap servers (localhost:9092 for dev)
   - Number of partitions per topic
   - Retention policies
   
2. Topic creation:
   - events (from Layer 0)
   - weather (from Layer 2)
   - aqi (from Layer 2)
   - worker_telemetry (from your app)
   
3. Dead-letter queues (DLQ):
   - events_dlq, weather_dlq, aqi_dlq, telemetry_dlq
```

**Your app must produce to**:
```
Topic: worker_telemetry
Schema:
{
  "worker_id": "uuid",
  "timestamp": "ISO8601",
  "latitude": float,
  "longitude": float,
  "altitude": float (optional),
  "accuracy_m": float,
  "speed_kmh": float,
  "heading_degrees": float,
  "app_foreground": boolean,
  "battery_percent": int,
  "network_type": "wifi|4g|5g|other"
}
```

---

## Layer 2: External Data Feeds
### APIs to Call

**AQI Connector** needs:
```
1. Government AQI API endpoints:
   - India government environmental data sources
   - City/zone parameters
   
2. Input from your app:
   - Claim location (city, lat/lon)
   - Time window for AQI lookup
   
Returns:
{
  "city": "string",
  "aqi_value": 0-500,
  "pm25": float,
  "pm10": float,
  "o3": float,
  "timestamp": "ISO8601"
}
```

**Weather Connector** needs:
```
1. Weather API keys:
   - OpenWeatherMap OR Indian meteorological dept.
   
2. Input from your app:
   - Claim location (lat/lon, city)
   - Time period (historical + forecast)
   
Returns:
{
  "city": "string",
  "latitude": float,
  "longitude": float,
  "temperature_c": float,
  "humidity_percent": int,
  "rainfall_mm": float,
  "wind_speed_kmh": float,
  "wind_direction_degrees": int,
  "timestamp": "ISO8601"
}
```

---

## Layer 3: Feature Extraction
### From Layer 0-2 + Worker Data

**Feature Extractor Service** needs input from:
```
1. Raw events (from Layer 0):
   - Event type, city, severity, timestamp
   
2. Worker telemetry (from your app via Kafka):
   - GPS tracks, app state, device sensors
   - 30-minute window of data points
   
3. Weather/AQI data (from Layer 2):
   - Temperature, rainfall, wind patterns
   - Air quality indices
   
4. External context (from your databases):
   - Worker ID, worker history
   - Claim timestamp, payout eligibility
```

**Output**: Feature vectors
```json
{
  "worker_id": "uuid",
  "claim_id": "uuid",
  "minute_bucket": 1713081000,
  "feature_vector": {
    "overall_feature_quality": 0.85,
    "motion_continuity_score": 0.88,
    "road_match_score": 0.82,
    "app_foreground_ratio": 0.75,
    "loss_plausibility_score": 0.6,
    "gps_accuracy_meters": 12.5,
    "velocity_variance": 0.15,
    "timestamp_utc": "ISO8601",
    "lstm_sequence": [30-timestep array],
    "disruption_score": 0.9,
    "trigger_types_active": ["curfew", "strike"]
  }
}
```

---

## Layer 4: ML Scoring & Fusion
### From Layer 3 + ML Models

**Your app must provide**:
```
1. ML model scores (from your ML pipeline):
   
   a) LSTM Score:
   {
     "worker_id": "uuid",
     "pow_confidence": 0.92,  # Power of confidence (0-1)
     "top_suspicious_timesteps": [list],
     "model_version": "v2.1.0",
     "inference_latency_ms": 10.5
   }
   
   b) Isolation Forest Score:
   {
     "fraud_risk_score": 0.12,  # Anomaly strength (0-1)
     "is_anomaly": false,
     "top_anomalous_features": [{feature, value, anomaly_score}],
     "model_version": "v1.5.0"
   }
   
   c) GBM Score:
   {
     "fraud_probability": 0.15,  # Fraud likelihood (0-1)
     "is_fraud_predicted": false,
     "top_fraud_signals": [{signal, importance}],
     "model_version": "v3.0.1"
   }
   
   d) Parametric Trigger:
   {
     "triggered": true,
     "severity_score": 0.9,
     "trigger_types_active": ["curfew"],
     "event_count": 1
   }

2. Feature vector (from Layer 3):
   - Overall quality, motion continuity, road match, etc.

3. Claim metadata:
   - Claim ID, worker ID, payout amount, worker trust tier
```

**Output**: Kafka `manual_review_outcomes` (or routing decision)
```json
{
  "claim_id": "uuid",
  "worker_id": "uuid",
  "routing_decision": "auto_payout|soft_verify|manual_flag",
  "composite_score": 0.75,
  "confidence_level": "high|medium|low",
  "route_reason": "high_confidence_genuine"
}
```

---

## Layer 5: Soft Verification
### From Layer 4 + Worker Device

**Your app must provide**:
```
1. Claims routed to TIER_2 (medium-risk):
   - Claim ID, worker ID, claim amount
   - Risk score and reasons for routing
   
2. Challenge details:
   - Challenge type: location_verification
   - Original claim location (lat/lon)
   - Challenge timestamp
   
3. Worker device info:
   - Phone number (for SMS fallback)
   - Firebase Cloud Messaging (FCM) token
   - Previous SMS delivery success rate
   
4. Response data (when worker responds):
   - Worker's GPS location (lat/lon, accuracy)
   - Response timestamp (seconds since challenge issued)
   - Proof photo/video (optional, for dispute)
```

**Expected inputs from worker**:
```
1. Via mobile app:
   - SMS: "YES" or location link click
   - FCM notification: Tap to confirm location
   - Web: Click link, authorize location access
   
2. Response must arrive within:
   - 30-minute SLA window
   - High-quality location (±2km tolerance zone)
```

**Output**: Decision
```json
{
  "claim_id": "uuid",
  "decision": "APPROVED|REJECTED|BORDERLINE",
  "location_score": 0.95,
  "timing_score": 0.8,
  "confidence": "high",
  "next_layer": "auto_payout|manual_review"
}
```

---

## Layer 6: Manual Review
### From Layer 5 + Claims Database

**Your app must provide**:
```
1. High-risk claims (TIER_3):
   - Claim ID, worker ID, payout amount
   - Trust tier (new, flagged, trusted)
   - Crowd spike indicator
   
2. Claim context (for reviewer):
   - Claimant proof photos/videos
   - GPS traces (worker's location history)
   - Income history (for income loss verification)
   - Previous claims (last 5 similar claims)
   
3. ML explanations:
   - LSTM attention weights (30-timestep visualization)
   - Isolation Forest SHAP values (top 5 signals)
   - GBM SHAP values (top 5 fraud signals)
   - Feature snapshot at time of claim
   
4. Worker profile:
   - Total claims, approval rate
   - Flagged reasons (if any)
   - Geographic specialization
   - Disruption in worker's zone
```

**Your app must support**:
```
1. Reviewer logins (JWT tokens):
   - reviewer_id, name, email, role (junior/senior/lead)
   
2. API endpoints:
   - GET /v1/review/queue - Get pending claims
   - POST /v1/review/claim/{queue_id}/assign - Assign to reviewer
   - GET /v1/review/claim/{claim_id}/context - Get full context
   - POST /v1/review/claim/{queue_id}/decide - Submit decision
   - POST /v1/review/claim/{queue_id}/release - Release back to queue
   - GET /v1/review/stats - Get reviewer stats
   
3. Database persistence:
   - Store review_queue items
   - Store reviewer profiles
   - Store all decisions for audit trail
```

**Reviewer decision inputs**:
```json
{
  "queue_id": "uuid",
  "decision": "approve|reject|request_more_info",
  "confidence": 1-5,
  "rejection_reason": "string (if reject)",
  "payout_override_inr": 500.0 (optional),
  "notes": "string (optional)"
}
```

**Appeals input** (from rejected workers):
```json
{
  "claim_id": "uuid",
  "appeal_reason": "string",
  "evidence_urls": ["photo_url1", "video_url1"],
  "worker_testimony": "string"
}
```

---

## Layer 7: Payout Processing
### From Layer 6 Approved Claims

**Your app must handle**:
```
1. Approved claims input:
   - Claim ID, worker ID, approved amount
   - Reviewer decision ID, reviewed at timestamp
   - Worker payment method (bank, UPI, etc.)
   
2. Process:
   - Validate payout eligibility
   - Process refund/transfer
   - Update claim status to PAYOUT_PROCESSING
   - Send notification to worker
   
3. Appeals overturned:
   - Claim status: REJECTED → APPEAL_APPROVED → PAYOUT_PROCESSING
   - Process refund same as auto-approved
```

**Output**: Payout confirmation
```json
{
  "claim_id": "uuid",
  "worker_id": "uuid",
  "amount_inr": 1500.0,
  "status": "PAYOUT_PROCESSING|PAID|FAILED",
  "transaction_id": "string",
  "processed_at": "ISO8601"
}
```

---

## Layer 8: Data Generation & Testing
### For Development/Testing

**Your app must provide**:
```
1. Configuration:
   - Number of genuine workers to generate
   - Number of fraud workers to generate
   - Claim volume (medium: 5000, full: 50000)
   - Date range for generated data
   
2. Synthetic data parameters:
   - Worker ID seeds
   - Geographic zones (cities, lat/lon ranges)
   - Disruption event dates/locations
   - Payout amount distributions
   
3. Output paths:
   - Where to store generated datasets
   - File format (CSV, JSON, Parquet)
```

**Generated outputs**:
```
- workers.csv (worker_id, trust_tier, location, history)
- genuine_claims.csv (realistic legitimate claims)
- fraud_claims.csv (simulated fraud scenarios)
- events.csv (simulated disruption events)
- telemetry.csv (simulated GPS traces)
```

---

## Summary Table: Input Sources

| Layer | Needs From Your App | Needs From External | Needs From Workers |
|-------|-------------------|-------------------|-------------------|
| **0** | Config keywords | Govt/news APIs | Direct feed URLs |
| **1** | Kafka cluster config | Topic schemas | - |
| **2** | API keys | Weather/AQI APIs | - |
| **3** | Claim metadata | Worker telemetry (Kafka) | GPS data |
| **4** | ML scores | Feature vectors | Model outputs |
| **5** | Claims to verify | Device info, FCM token | Location response, SMS |
| **6** | High-risk claims | Context data, ML explanations | Appeal reasons + evidence |
| **7** | Approved claims | Payout methods | - |
| **8** | Config parameters | Seed data | - |

---

## Critical Input Data Flow

```
Your App → Kafka Topics:
  ├── worker_telemetry (GPS, app state, battery)
  ├── claims (new claims, payout amounts)
  └── events (from Layer 0)

Your App ← Kafka Topics:
  ├── manual_review_outcomes (Layer 6 decisions)
  └── claim_state_events (state transitions)

Your App ↔ APIs (Required):
  ├── GET /v1/review/queue (Layer 6)
  ├── POST /v1/review/claim/{id}/decide (Layer 6)
  ├── POST /v1/verification/challenge/{id}/respond (Layer 5)
  └── GET /health (all services)
```

---

## Implementation Checklist

- [ ] Kafka producer: `worker_telemetry` messages
- [ ] Kafka consumer: `manual_review_outcomes` decisions
- [ ] API: Reviewer authentication (JWT tokens)
- [ ] API: Decision submission endpoints
- [ ] Database: Claims table with status tracking
- [ ] Database: Workers table with trust tiers
- [ ] Mobile: SMS/FCM response handlers (Layer 5)
- [ ] Mobile: Location permission + GPS capture (Layer 5)
- [ ] Dashboard: Claim tracking UI
- [ ] Dashboard: Reviewer dashboard (Layer 6)
- [ ] Webhooks: Appeal notifications
- [ ] Payout service: Process approved refunds
