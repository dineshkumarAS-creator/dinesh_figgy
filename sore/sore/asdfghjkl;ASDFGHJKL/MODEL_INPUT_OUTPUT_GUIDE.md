# FIGGY Model I/O & UI Components Guide

**Complete Reference for Data Flow, Model Processing, and User Interface Components**

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Input Requirements](#input-requirements)
3. [ML Model Processing](#ml-model-processing)
4. [Output Formats](#output-formats)
5. [UI Components](#ui-components)
6. [Quick Reference](#quick-reference)

---

## Architecture Overview

```
FIGGY End-to-End Data Flow:

📱 WORKER APP (Mobile Sensors)
    ↓
🎯 Layer 1: Kafka (Stream Processing)
    ↓
🌍 External APIs (Weather, AQI, News)
    ↓
🔧 Layer 2-3: Feature Extraction & Normalization
    ↓
🧠 ML Models: LSTM, Isolation Forest, GBM
    ↓
📊 Layer 4: Score Fusion & Routing
    ↓
🔍 Layer 5-6: Verification & Manual Review
    ↓
💰 Layer 7: Payout Calculator
    ↓
⛓️ Layer 7B: NFT Minting (Polygon Blockchain)
    ↓
🏦 Payment Execution
```

---

## Input Requirements

### 1️⃣ Worker Telemetry (Mobile App)

**Endpoint**: `POST /v1/telemetry/batch`

**Payload Structure**:

```json
{
  "events": [
    {
      "event_type": "gps",
      "timestamp_utc": "2026-04-16T10:30:45Z",
      "lat": 19.076,
      "lon": 72.8777,
      "accuracy_m": 12.5,
      "speed_kmh": 25.3,
      "battery_pct": 85
    },
    {
      "event_type": "delivery_attempt",
      "timestamp_utc": "2026-04-16T10:31:00Z",
      "delivery_zone_id": "Mumbai_Zone_5",
      "battery_pct": 84
    },
    {
      "event_type": "app_state",
      "timestamp_utc": "2026-04-16T10:31:15Z",
      "app_state": "foreground"
    },
    {
      "event_type": "imu",
      "timestamp_utc": "2026-04-16T10:31:30Z",
      "accel_x": 0.2,
      "accel_y": -0.15,
      "accel_z": 9.8
    }
  ]
}
```

**Event Types & Validation**:

| Event Type         | Required Fields                     | Optional Fields                      | Constraints                                        |
| ------------------ | ----------------------------------- | ------------------------------------ | -------------------------------------------------- |
| `gps`              | lat, lon, accuracy_m, timestamp_utc | speed_kmh, battery_pct               | lat: [-90,90], lon: [-180,180], accuracy: [0,500)m |
| `imu`              | timestamp_utc                       | accel_x/y/z, gyro_x/y/z, battery_pct | None required (but recommended)                    |
| `app_state`        | app_state, timestamp_utc            | battery_pct                          | app_state: foreground\|background\|offline         |
| `delivery_attempt` | delivery_zone_id, timestamp_utc     | battery_pct                          | Zone must be non-empty string                      |

**Batch Constraints**:

- Max 50 events per batch
- Max 80% failure rate (else HTTP 422)
- All events published to Kafka topic: `worker_telemetry`
- Worker ID extracted from JWT token

---

### 2️⃣ Environmental Data (External APIs)

**Weather Input**:

```json
{
  "weather": {
    "city": "Mumbai",
    "timestamp_utc": "2026-04-16T10:35:00Z",
    "rainfall_mm_per_hr": 25.5,
    "rainfall_30min_trend": "increasing",
    "temperature_c": 32.0,
    "humidity_pct": 78,
    "wind_kmh": 12.5
  }
}
```

**AQI Input**:

```json
{
  "aqi": {
    "city": "Mumbai",
    "timestamp_utc": "2026-04-16T10:35:00Z",
    "aqi_index": 285,
    "pm25": 185,
    "pm10": 320,
    "category": "Severe",
    "aqi_30min_trend": "worsening"
  }
}
```

**Event Input** (from Layer 0 - Event Connectors):

```json
{
  "event": {
    "event_type": "curfew",
    "affected_city": "Mumbai",
    "affected_zones": ["Bandra", "Colaba", "Fort"],
    "severity": 4,
    "source": "govt",
    "source_url": "https://pib.gov.in/alert/123456",
    "raw_title": "Curfew imposed in Mumbai coastal areas",
    "timestamp_utc": "2026-04-16T08:00:00Z",
    "is_trigger_condition": true,
    "triggered_at": "2026-04-16T08:05:00Z"
  }
}
```

---

### 3️⃣ Worker Profile Context

**Input Format**:

```json
{
  "worker_id": "w_12345abc",
  "trust_tier": "silver",
  "base_hourly_rate_inr": 150.0,
  "historical_avg_earnings_per_hr": 120.0,
  "historical_avg_deliveries_per_hr": 10.0,
  "enrollment_date": "2023-01-15",
  "is_active": true
}
```

**Worker Trust Tiers**:

- `new` - No bonus, no penalty (1.0x multiplier)
- `silver` - No bonus, no penalty (1.0x multiplier)
- `gold` - +5% bonus (1.05x multiplier)
- `flagged` - ₹0 payout (0.0x multiplier)

---

## ML Model Processing

### Layer 3: Feature Extraction (1-Minute Windows)

**Raw Input**: Aggregated telemetry, weather, AQI, events for 1-minute bucket

**Process**:

1. Aggregate GPS data into minute window
2. Compute motion/road matching scores
3. Calculate income loss metrics
4. Extract environmental signals
5. Validate data quality (>0.3 threshold on 0-1 scale)

**Feature Vector Output** (45+ features):

```json
{
  "worker_id": "w_12345abc",
  "minute_bucket": 1713081000,
  "feature_pipeline_version": "1.0.0",
  "computed_at": "2026-04-16T10:35:00Z",

  "ENVIRONMENTAL_FEATURES": {
    "rainfall_mm_per_hr": 25.5,
    "rainfall_intensity_class": "heavy",
    "rainfall_30min_trend": "increasing",
    "aqi_index_current": 285,
    "aqi_stdz": 3.2,
    "aqi_category": "Severe",
    "event_severity_score": 0.8,
    "event_type_active": ["curfew", "lockdown"],
    "event_count_active": 2,
    "composite_disruption_index": 0.82,
    "env_feature_quality": 0.92
  },

  "BEHAVIORAL_FEATURES": {
    "gps_displacement_m": 245.3,
    "cumulative_displacement_m": 5421.0,
    "active_zone_minutes": 28,
    "delivery_attempt_count": 3,
    "delivery_attempt_rate_per_hr": 9.2,
    "motion_continuity_score": 0.88,
    "road_match_score": 0.92,
    "app_foreground_ratio": 0.95,
    "speed_anomaly_count": 0,
    "behaviour_feature_quality": 0.85
  },

  "INCOME_FEATURES": {
    "expected_earnings_inr": 2.5,
    "actual_earnings_inr": 0.5,
    "income_loss_inr": 2.0,
    "income_loss_ratio": 0.8,
    "loss_plausibility_score": 0.91,
    "loss_plausibility_suspicious": false,
    "delivery_rate_vs_baseline": 0.32,
    "delivery_rate_suspicious": false,
    "earnings_consistency_score": 0.87,
    "cumulative_loss_session_inr": 480.0,
    "payout_eligible_inr": 270.0,
    "income_feature_quality": 0.89
  },

  "QUALITY_METRICS": {
    "overall_feature_quality": 0.87,
    "env_complete": true,
    "behaviour_complete": true,
    "income_complete": true
  }
}
```

---

### ML Model Scoring (Parallel Processing)

**Timeline**:

- Score collection window: 2 seconds
- If model times out after 2s → use fallback heuristic
- All scores merged for composite calculation

#### Model 1: LSTM (TensorFlow)

**Input**: 60-minute time-series of feature vectors

**Output**:

```json
{
  "lstm_pow_confidence": 0.87,
  "lstm_motion_continuity_score": 0.88,
  "lstm_road_match_score": 0.92,
  "lstm_app_foreground_ratio": 0.95,
  "lstm_inference_latency_ms": 12.4
}
```

**Purpose**: Detects if worker's movement pattern is consistent with legitimate disruption ("stuck at home due to curfew")

**Fallback** (if LSTM times out):

```
fallback = 0.5 × motion_continuity + 0.3 × road_match + 0.2 × app_foreground
```

---

#### Model 2: Isolation Forest (scikit-learn)

**Input**: Current feature window (point anomaly detection)

**Output**:

```json
{
  "if_anomaly_score": -0.15,
  "if_fraud_risk_score": 0.12,
  "if_is_anomalous": false,
  "if_inference_latency_ms": 6.8
}
```

**Purpose**: Detects statistical outliers (GPS spoofing, unrealistic speeds, etc.)

**Score Range**: 0-1 (higher = more risky)

---

#### Model 3: GBM (XGBoost)

**Input**: Session-level aggregated features

**Output**:

```json
{
  "gbm_fraud_probability": 0.08,
  "gbm_fraud_risk_score": 0.08,
  "gbm_feature_importance": {
    "loss_plausibility_score": 0.25,
    "motion_continuity_score": 0.18,
    "road_match_score": 0.15,
    "aqi_index": 0.12,
    "delivery_rate_vs_baseline": 0.1
  },
  "gbm_inference_latency_ms": 9.2
}
```

**Purpose**: Classification fraud using ensemble gradient boosting

**Fallback** (if GBM times out):

```
if IF available: use if_fraud_risk_score
else: gbm_fraud_probability = 1 - loss_plausibility_score (conservative)
```

---

### Layer 4: Score Fusion & Composite Calculation

**Input**: All 3 ML model outputs (or fallback values)

**Fusion Formula**:

```
composite_claim_score = (
  0.35 × lstm_pow_confidence +
  0.30 × (1 - if_fraud_risk_score) +
  0.25 × (1 - gbm_fraud_probability) +
  0.10 × parametric_trigger_signal
)

confidence_level = HIGH if all_3_models_available else MEDIUM
```

**Output**:

```json
{
  "worker_id": "w_12345abc",
  "minute_bucket": 1713081000,

  "composite_scores": {
    "lstm_raw": 0.87,
    "if_raw": 0.12,
    "gbm_raw": 0.08,
    "parametric_trigger": 0.9
  },

  "composite_claim_score": 0.78,
  "confidence_level": "HIGH",
  "anti_spoofing_flag": false,
  "top_risk_signals": []
}
```

**Routing Decision** (Layer 5-6):

- `composite_claim_score >= 0.70` → **APPROVE** (auto-pay eligible)
- `0.50 <= score < 0.70` → **SOFT VERIFY** (challenge window)
- `score < 0.50` → **MANUAL REVIEW** (high risk)

---

## Output Formats

### Payout Calculation (Layer 7)

**6-Step Calculation Breakdown**:

```json
{
  "claim_id": "clm_2026_04_16_001",
  "worker_id": "w_12345abc",

  "STEP_1_gross_loss": {
    "description": "Expected - Actual earnings",
    "expected_earnings_inr": 1200.0,
    "actual_earnings_inr": 240.0,
    "gross_loss_inr": 960.0
  },

  "STEP_2_disruption_severity": {
    "description": "Severity multiplier based on disruption index",
    "composite_disruption_index": 0.82,
    "severe_disruption_threshold": 0.6,
    "severity_multiplier": 1.0,
    "note": "disruption >= 0.6 → 100% multiplier"
  },

  "STEP_3_adjusted_loss": {
    "description": "Gross loss × severity",
    "calculation": "960 × 1.0",
    "adjusted_loss_inr": 960.0
  },

  "STEP_4_coverage": {
    "description": "Apply coverage ratio (67%)",
    "coverage_ratio": 0.67,
    "calculation": "960 × 0.67",
    "covered_amount_inr": 643.2
  },

  "STEP_5_data_quality": {
    "description": "Adjust for data completeness",
    "data_completeness": 0.95,
    "quality_penalty": 1.0,
    "calculation": "643.2 × 0.95",
    "after_quality_inr": 610.04
  },

  "STEP_6_caps_and_adjustments": {
    "description": "Apply all caps simultaneously",
    "daily_cap_remaining_inr": 3000.0,
    "monthly_cap_remaining_inr": 15000.0,
    "claim_cap_inr": 2000.0,
    "capped_amount_inr": 610.04,
    "cap_applied": null,
    "note": "No cap exceeded"
  },

  "TRUST_TIER_ADJUSTMENT": {
    "worker_trust_tier": "silver",
    "trust_multiplier": 1.0,
    "before_trust_inr": 610.04,
    "after_trust_inr": 610.04,
    "note": "Silver tier: no bonus"
  },

  "MINIMUM_THRESHOLD_CHECK": {
    "min_payout_inr": 50.0,
    "final_payout_inr": 610.04,
    "below_minimum": false,
    "eligible": true
  },

  "FINAL_PAYOUT": {
    "final_payout_inr": 610.04,
    "currency": "INR",
    "status": "READY_FOR_PAYMENT",
    "calculated_at": "2026-04-16T11:00:00Z",
    "calculated_by": "auto"
  },

  "LEDGER_TRACKING": {
    "daily_total_after_payout": 610.04,
    "monthly_total_after_payout": 2140.32,
    "claim_total_after_payout": 610.04
  }
}
```

**Key Thresholds**:

- Coverage Ratio: **67%** (COVERAGE_RATIO)
- Minimum Payout: **₹50** (MIN_PAYOUT_INR)
- Max per Claim: **₹2,000** (MAX_PAYOUT_PER_CLAIM_INR)
- Max per Day: **₹3,000** (MAX_PAYOUT_PER_DAY_INR)
- Max per Month: **₹15,000** (MAX_PAYOUT_PER_MONTH_INR)
- Severe Disruption: **≥0.6** (SEVERE_DISRUPTION_THRESHOLD)

---

### Blockchain NFT Token (Layer 7B)

**Smart Contract: FIGGYPoWToken.sol**

```json
{
  "token": {
    "token_id": 42156,
    "token_type": "ERC-721",
    "contract_address": "0x8F3Cf7ad23Cd3CaDbD9735AFf958023D60C95eEE",
    "blockchain_network": "Polygon",
    "chain_id": 137,
    "minted_at": "2026-04-16T11:05:30Z"
  },

  "worker_activity_record": {
    "worker_id_hash": "0xb4c11951957c6f8f642c4af61cd6b182fe5305243601f27aacd2e60db330e5f4",
    "privacy_note": "Hash of worker_id (one-way, cannot reverse)",
    "delivery_zone_id": "Mumbai_Zone_5",
    "active_minutes": 487,
    "delivery_attempts": 12,
    "trigger_type": "curfew",
    "disruption_severity": 85,
    "composite_claim_score": 78,
    "session_timestamp": 1713081600,
    "feature_vector_hash": "0x7c2d4e8f5a3b1c9d8f6e5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c",
    "feature_vector_hash_algo": "SHA-256"
  },

  "payout_info": {
    "payout_released": false,
    "payout_amount_inr": 610.04,
    "payout_vault_address": "0xabc123def456ghi789",
    "eligible_for_release": true
  },

  "token_metadata": {
    "token_uri": "https://ipfs.io/ipfs/QmXxxx...",
    "metadata_hash": "0xixyz...",
    "immutable": true,
    "only_payoutReleased_mutable": true
  }
}
```

**Vault Functions**:

```solidity
// Deposit insurance funds
depositNative()  // Accepts MATIC
depositUsdc(amount)  // Accepts USDC ERC-20

// Release payout (with token verification)
releasePayoutNative(
  tokenId,
  workerIdHash,
  recipient,
  amountWei,
  minTime, maxTime
)

releasePayoutUsdc(...)  // Same for USDC
```

---

## UI Components

### 1️⃣ Worker Mobile App - Claim Submission

```
┌─────────────────────────────────┐
│  ✋ NEW CLAIM                    │
├─────────────────────────────────┤
│                                 │
│  📍 Current Location:           │
│     Mumbai, Bandra              │
│     19.076° N, 72.877° E        │
│                                 │
│  🚨 Active Disruption Detected: │
│  ┌─────────────────────────────┤
│  │ Curfew Alert               │
│  │ ⏰ Active for 4 hours       │
│  │ 📍 Bandra, Colaba          │
│  │ ⚠️ Severity: High (4/5)    │
│  │ 📰 Source: Govt Official   │
│  └─────────────────────────────┘
│                                 │
│  💼 Your Income Impact:         │
│  ┌─────────────────────────────┤
│  │ Normal Earnings Expected:   │
│  │   ₹1,200 (in this window)   │
│  │                             │
│  │ Your Earnings So Far:       │
│  │   ₹240                      │
│  │                             │
│  │ Estimated Loss:             │
│  │   ₹960 (80%)               │
│  │                             │
│  │ Estimated Payout:           │
│  │   ₹610 (67% coverage)       │
│  └─────────────────────────────┘
│                                 │
│  ⚡ Features:                    │
│  • GPS verified ✓               │
│  • Income loss confirmed ✓      │
│  • Ready to submit ✓            │
│                                 │
│  [SUBMIT CLAIM]  [LATER]        │
└─────────────────────────────────┘
```

---

### 2️⃣ Worker Dashboard - Claim Tracking

```
┌────────────────────────────────────────────┐
│ 📱 CLAIM TRACKING DASHBOARD               │
├────────────────────────────────────────────┤
│                                            │
│  Claim ID: CLM-2026-04-16-001             │
│  Status Badge: [⏳ UNDER REVIEW]          │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │ DISRUPTION DETAILS                   │ │
│  ├──────────────────────────────────────┤ │
│  │ Event: Curfew (Severity 4/5)        │ │
│  │ Location: Mumbai, Bandra            │ │
│  │ Duration: 487 minutes (~8 hrs)      │ │
│  │ Trigger Types: [Lockdown]           │ │
│  └──────────────────────────────────────┘ │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │ INCOME IMPACT                        │ │
│  ├──────────────────────────────────────┤ │
│  │ Expected Earnings: ₹1,200           │ │
│  │ Actual Earnings: ₹240               │ │
│  │ Income Loss: ₹960                   │ │
│  │ Loss %: 80%                         │ │
│  └──────────────────────────────────────┘ │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │ CLAIM PROGRESS                       │ │
│  ├──────────────────────────────────────┤ │
│  │ ✅ Step 1: Submitted                │ │
│  │ ✅ Step 2: Feature Extraction       │ │
│  │ ⏳ Step 3: ML Scoring (in progress) │ │
│  │ ⏳ Step 4: Risk Verification        │ │
│  │ ⏳ Step 5: Manual Review            │ │
│  │ ⏳ Step 6: Payout Calculation       │ │
│  │ ⏳ Step 7: Blockchain Confirmation  │ │
│  └──────────────────────────────────────┘ │
│                                            │
│  Estimated Payout: ₹271 INR              │
│  Est. Payment Date: 2026-04-18           │
│                                            │
│  [TRACK DETAILS]  [APPEAL]  [HELP]       │
└────────────────────────────────────────────┘
```

---

### 3️⃣ Admin Dashboard - ML Scoring Results

```
┌────────────────────────────────────────────┐
│ 🔍 CLAIM ANALYSIS DASHBOARD               │
├────────────────────────────────────────────┤
│                                            │
│  Claim ID: CLM-2026-04-16-001             │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │ ML MODEL SCORES                      │ │
│  ├──────────────────────────────────────┤ │
│  │ LSTM Confidence:         ████████░ 87%│
│  │ Isolation Forest Risk:    ██░░░░░░░ 12%│
│  │ GBM Fraud Probability:   ██░░░░░░░░ 8% │
│  │                                       │ │
│  │ COMPOSITE SCORE:         ███████░░ 78% │
│  │ RISK LEVEL: LOW ✅                    │ │
│  └──────────────────────────────────────┘ │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │ FEATURE QUALITY METRICS              │ │
│  ├──────────────────────────────────────┤ │
│  │ Environmental Data:      ████████░ 88% │
│  │ Behavioral Data:         ███████░░ 85% │
│  │ Income Data:             ████████░ 87% │
│  │ Overall Quality:         ████████░ 87% │
│  └──────────────────────────────────────┘ │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │ RISK SIGNALS                         │ │
│  ├──────────────────────────────────────┤ │
│  │ ✅ GPS path coherent (92%)           │ │
│  │ ✅ App engagement high (95%)         │ │
│  │ ✅ Earnings plausible (91%)          │ │
│  │ ✅ No speed anomalies detected       │ │
│  │ ✅ Motion continuity intact (88%)    │ │
│  └──────────────────────────────────────┘ │
│                                            │
│  [APPROVE]  [MANUAL REVIEW]  [REJECT]    │
└────────────────────────────────────────────┘
```

---

### 4️⃣ Admin Dashboard - Payout Calculation

```
┌────────────────────────────────────────────┐
│ 💰 PAYOUT CALCULATION BREAKDOWN            │
├────────────────────────────────────────────┤
│                                            │
│  Claim ID: CLM-2026-04-16-001             │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │ CALCULATION STEPS                    │ │
│  ├──────────────────────────────────────┤ │
│  │                                       │ │
│  │ Step 1 - Gross Loss                 │ │
│  │   Expected Earnings:     ₹1,200     │ │
│  │   Actual Earnings:       ₹240       │ │
│  │   ➜ Gross Loss:          ₹960       │ │
│  │                                       │ │
│  │ Step 2 - Disruption Severity        │ │
│  │   Composite Disruption:   85%       │ │
│  │   Threshold:              60%       │ │
│  │   ➜ Severity Factor:      1.0 (100%)│ │
│  │                                       │ │
│  │ Step 3 - Adjusted Loss              │ │
│  │   Gross × Severity: ₹960 × 1.0      │ │
│  │   ➜ Adjusted Loss:   ₹960           │ │
│  │                                       │ │
│  │ Step 4 - Coverage Ratio             │ │
│  │   Coverage Policy:        67%       │ │
│  │   Adjusted × 0.67:        ₹643.20  │ │
│  │   ➜ Covered Amount:       ₹643.20  │ │
│  │                                       │ │
│  │ Step 5 - Data Quality                │ │
│  │   Data Completeness:      95%       │ │
│  │   Quality Penalty: None   │ │
│  │   ➜ After Quality:        ₹610.04  │ │
│  │                                       │ │
│  │ Step 6 - Apply Caps                 │ │
│  │   Daily Cap:              ₹3,000   │ │
│  │   Monthly Cap:            ₹15,000  │ │
│  │   Claim Cap:              ₹2,000   │ │
│  │   ➜ Final Cap Check:      None      │ │
│  │                                       │ │
│  │ ┌────────────────────────────────┐  │ │
│  │ │ FINAL PAYOUT:     ₹610 INR    │  │ │
│  │ │ Trust Tier:       Silver (1.0x)│  │ │
│  │ │ Calculated By:    Automated     │  │ │
│  │ │ Timestamp:        2026-04-16   │  │ │
│  │ │                   11:00:00 UTC  │  │ │
│  │ └────────────────────────────────┘  │ │
│  └──────────────────────────────────────┘ │
│                                            │
│  [APPROVE PAYOUT]  [EDIT]  [HOLD]         │
└────────────────────────────────────────────┘
```

---

### 5️⃣ Blockchain Explorer - NFT Details

```
┌────────────────────────────────────────────┐
│ ⛓️ PROOF-OF-WORK NFT TOKEN                │
├────────────────────────────────────────────┤
│                                            │
│  Token ID: #42156                         │
│  Status Badge: [NOT CLAIMED YET]          │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │ TOKEN METADATA                       │ │
│  ├──────────────────────────────────────┤ │
│  │ Worker ID Hash:                      │ │
│  │   0xb4c11951957c6f8f642c4af6...    │ │
│  │   (Privacy: non-reversible hash)    │ │
│  │                                       │ │
│  │ Delivery Zone:          Mumbai Zone 5│ │
│  │ Active Minutes:         487          │ │
│  │ Delivery Attempts:      12           │ │
│  │ Trigger Type:           Curfew       │ │
│  │ Disruption Severity:    85/100       │ │
│  │ Composite Claim Score:  78/100       │ │
│  │ Session Timestamp:      2026-04-16   │ │
│  │                         10:30:00 UTC │ │
│  │                                       │ │
│  │ Feature Vector Hash:                 │ │
│  │   0x7c2d4e8f5a3b1c9d...             │ │
│  │   (SHA-256 of features)             │ │
│  │                                       │ │
│  │ Payout Released: NO                 │ │
│  │ Release Amount: ₹610 INR             │ │
│  │                                       │ │
│  └──────────────────────────────────────┘ │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │ BLOCKCHAIN DETAILS                   │ │
│  ├──────────────────────────────────────┤ │
│  │ Network:                Polygon      │ │
│  │ Chain ID:               137          │ │
│  │ Contract:               0x8F3Cf...   │ │
│  │ Tx Hash:                0xab12cd...  │ │
│  │ Block Number:           54321654     │ │
│  │ Confirmed At:           2026-04-16   │ │
│  │                         11:05:30 UTC │ │
│  │ Gas Used:               84,532 wei   │ │
│  │                                       │ │
│  └──────────────────────────────────────┘ │
│                                            │
│  [VIEW ON POLYGON SCAN]  [CLAIM PAYOUT]   │
└────────────────────────────────────────────┘
```

---

### 6️⃣ Admin Dashboard - Appeal Management

```
┌────────────────────────────────────────────┐
│ 🔎 WORKER APPEAL REVIEW                   │
├────────────────────────────────────────────┤
│                                            │
│  Appeal ID: APL-2026-04-16-042            │
│  Claim ID: CLM-2026-04-16-001             │
│  Worker ID: w_12345abc                    │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │ ORIGINAL CLAIM DECISION              │ │
│  ├──────────────────────────────────────┤ │
│  │ Status: SOFT_VERIFY (Score: 0.65)   │ │
│  │ Reason: Below auto-approval threshold│ │
│  │ Calculated Payout: ₹610              │ │
│  │ Decision Date: 2026-04-16 10:50 UTC │ │
│  └──────────────────────────────────────┘ │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │ WORKER APPEAL CONTEXT                │ │
│  ├──────────────────────────────────────┤ │
│  │ Submitted: 2026-04-16 11:15 UTC     │ │
│  │ Reason: "My GPS was poor quality    │ │
│  │         in underground area"         │ │
│  │                                       │ │
│  │ Additional Evidence:                │ │
│  │ • App state logs (foreground 97%)   │ │
│  │ • Delivery zone confirmation        │ │
│  │ • Previous 30-day history (100%)    │ │
│  └──────────────────────────────────────┘ │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │ REVIEWER ANALYSIS                    │ │
│  ├──────────────────────────────────────┤ │
│  │ App engagement high (97%)            │ │
│  │ Income loss plausible (94%)          │ │
│  │ Previous claim history: CLEAN        │ │
│  │ Trust tier: SILVER                   │ │
│  │ Recommended: APPROVE                 │ │
│  └──────────────────────────────────────┘ │
│                                            │
│  [APPROVE]  [REJECT]  [REQUEST_MORE]      │
└────────────────────────────────────────────┘
```

---

## Quick Reference

### Input → Output Mapping

| Layer   | Input Type                | Processing                      | Output Type           |
| ------- | ------------------------- | ------------------------------- | --------------------- |
| **0**   | Event feeds (govt/news)   | NLP extraction + dedup          | Event metadata        |
| **1-2** | Telemetry + Weather/AQI   | Normalization + outlier removal | Cleaned events        |
| **3**   | Cleaned events + profiles | Feature engineering (45+)       | Feature vector        |
| **3**   | Feature vector            | ML models (3 parallel)          | Fraud scores (0-1)    |
| **4**   | 3 ML scores + parametric  | Weighted fusion + fallbacks     | Composite score (0-1) |
| **5-6** | Composite score           | Verification rules + manual     | Approval status       |
| **7**   | Approved claim            | 6-step calculation (Decimal)    | Payout amount (₹)     |
| **7B**  | Payout record             | Smart contract mint             | NFT token ID          |
| **8**   | NFT token                 | Vault verification              | Payment execution     |

---

### Configuration Parameters

**Payout Config** (`income_calculator/config.py`):

```python
COVERAGE_RATIO = 0.67                    # 67% coverage
MIN_PAYOUT_INR = 50                      # Minimum threshold
MAX_PAYOUT_PER_CLAIM_INR = 2000          # Per-claim cap
MAX_PAYOUT_PER_DAY_INR = 3000            # Daily cap
MAX_PAYOUT_PER_MONTH_INR = 15000         # Monthly cap
SEVERE_DISRUPTION_THRESHOLD = 0.6        # Severity cutoff
```

**ML Thresholds** (Layer 4):

```python
LSTM Timeout = 2 seconds
IF Timeout = 2 seconds
GBM Timeout = 2 seconds

Score weights:
  LSTM: 35%
  IF Negation: 30%
  GBM Negation: 25%
  Parametric: 10%

Auto-Approval: >= 0.70
Soft Verify: 0.50-0.70
Manual Review: < 0.50
```

**Trust Tier Multipliers**:

- `new`: 1.0x
- `silver`: 1.0x
- `gold`: 1.05x (+5% bonus)
- `flagged`: 0.0x (no payout)

---

### Telemetry Batch Validation

**Max Constraints**:

- 50 events per batch
- 80% max failure rate
- Event deduplication by (worker_id, timestamp, event_type)

**Event Creation Pipeline**:

```
Raw Batch
  ↓ (per event)
  Schema Validation (Pydantic)
  ↓
  Field Range Checks
  ↓
  Replay Detection (Redis TTL)
  ↓
  Valid → Kafka topic "worker_telemetry"
  Invalid → Log to structlog (not published)
  ↓
  If >80% failed: Publish entire batch to "worker_telemetry_dlq"
```

---

### Feature Vector Quality Thresholds

**Completeness Checks** (>0.3 on 0-1 scale):

- Environmental: rainfall + AQI + disruption
- Behavioral: GPS + motion + road matching
- Income: expected + loss ratio + payout eligible

**Overall Quality** (weighted):

```
overall = 0.3 × env_quality + 0.4 × behavior_quality + 0.3 × income_quality
```

**Minimum Threshold for Publishing**: `overall_feature_quality > 0.3`

---

### Payout Calculation Order

1. Gross Loss = Expected - Actual
2. Severity Factor = min(disruption / 0.6, 1.0)
3. Adjusted Loss = Gross × Severity
4. Coverage = Adjusted × 0.67
5. Data Quality = Coverage × completeness_factor
6. **Apply all caps simultaneously** (daily, monthly, claim)
7. Trust Tier Bonus = final × multiplier
8. Minimum Check = if < ₹50, return ₹0

---

### Blockchain Verification

**PoW Token Verification** (before payout release):

```solidity
function verifyWorkerToken(
  bytes32 workerIdHash,
  uint64 minTime,
  uint64 maxTime
) → (bool exists, uint256 tokenId)
```

**Payout Release Conditions**:

1. Token exists ✓
2. Token not already paid ✓
3. Session within time window ✓
4. Vault has sufficient balance ✓

Result → Transfer funds + Mark token as released

---

**Document Version**: 1.0  
**Last Updated**: 2026-04-16  
**FIGGY V7 - 7-Layer Insurance Pipeline**
