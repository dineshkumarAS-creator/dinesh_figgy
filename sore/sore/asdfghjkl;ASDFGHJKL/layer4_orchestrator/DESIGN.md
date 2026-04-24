# Layer 4 Inference Orchestrator: Design Notes

## Overview

Layer 4 is the critical **score fusion and routing service** that:
1. Collects scores from 3 independent ML models (LSTM, Isolation Forest, GBM)
2. Fuses them with parametric trigger signals into a composite claim score
3. Routes to Layer 5 for payout processing with explainability

**Key Design Principle:** Defensive design with fallback heuristics for model timeouts, anti-spoofing overrides, and confidence-based decision gating.

---

## Architecture

```
Layer 3 (ML Inference)
  └─ LSTM (pow_confidence)
  └─ Isolation Forest (fraud_risk_score, anomaly detection)
  └─ GBM (fraud_probability)
  └─ Parametric Trigger (severity_score, trigger_types)
     │
     ├─ Kafka topic: "ml_scores"
     │
     ▼
Layer 4 (Score Orchestrator)
  ├─ Score Collector (buffer by worker_id, minute_bucket)
  ├─ Score Fuser (fusion formula + fallbacks)
  ├─ Claim Router (routing rules)
  └─ Publisher (Kafka + Redis)
     │
     ├─ Kafka topics:
     │  ├─ "composite_scores"
     │  └─ "routing_decisions"
     │
     ├─ Redis keys:
     │  ├─ composite_score:latest:{worker_id}
     │  └─ routing_decision:latest:{worker_id}
     │
     └─ FastAPI Debug API
        ├─ /v1/composite/{worker_id}
        ├─ /v1/routing/{worker_id}
        ├─ /v1/explain/{worker_id}
        └─ /v1/dashboard
```

---

## Design Rationales

### 1. 2-Second Wait Window (Score Collector)

**Why 2 seconds?**

- **Resilience to Model Variance:** Different ML services (LSTM in TensorFlow, IF in scikit-learn, GBM in XGBoost) have varying latencies.
  - Typical latencies: LSTM 8-15ms, IF 3-10ms, GBM 5-12ms
  - Tail latencies (P95): LSTM ~50ms, IF ~30ms, GBM ~40ms
  - 2 seconds provides 40x margin while staying responsive

- **Timeout Signal, Not Failure:** If a model hasn't scored after 2 seconds, it's treated as **lagging** rather than failed.
  - Allows graceful degradation instead of hard failures
  - Triggers fallback heuristics (retain system availability)

- **Balance RTO/RPO:**
  - 2-second wait means minute-level (60-second) buckets can tolerate occasional slow models
  - A minute has 60 seconds; one slow batch (2s) is acceptable overhead

**Timeout Behavior:**
- Emit composite score with sentinel `-1.0` for missing scores
- Log timeout event for monitoring
- Increment `model_timeout_counter` metric per model type
- Trigger fallback heuristic computation

---

### 2. Fallback Hierarchy (Score Fusion)

When a model times out, use:

#### **LSTM Timeout (POW Confidence Fallback)**

Formula: `fallback = 0.5 × motion_continuity_score + 0.3 × road_match_score + 0.2 × app_foreground_ratio`

**Rationale:**
- Motion continuity captures if worker's movement pattern is consistent with "stuck at home due to curfew"
- Road match indicates if GPS traces match actual road network (vs spoofing)
- App foreground is proxy for app engagement (not sleeping through disruption)

**Why these weights?**
- 50% motion: Strongest signal of *legitimate* work disruption
- 30% road matching: Medium-strength anti-spoofing signal
- 20% app foreground: Weaker but still indicative of active usage during disruption

#### **GBM Timeout (Fraud Risk Fallback)**

**Priority:**
1. Use IF fraud_risk_score if available (already calibrated 0-1)
2. If IF also timed out: `fraud_probability = 1 - loss_plausibility_score` (conservative)

**Rationale:**
- IF and GBM are both anomaly/fraud signals; can substitute
- Loss plausibility is from income feature extractor (third independent signal)
- Conservative formula (1 - plausibility) assumes fraud unless proven otherwise

---

### 3. Anti-Spoofing Flag Override

**Override Rule:** If `anti_spoofing_flag=True`, **always route to `manual_flag`** regardless of composite score.

**Scenarios Triggering Anti-Spoofing:**
- `IF.is_anomaly=True`: Anomalous pattern detected (e.g., impossible GPS displacement)
- `GBM.is_fraud_predicted=True`: Model confidently predicts fraud

**Why Override?**
- **Security-first design:** Even 1% false positive on spoofing can cost crores
- **Asymmetric risk:** Auto-paying a fraudster << missing a genuine claim, but >>  paying a spoofed claim
- **Manual review catches nuance:** Human agents can investigate GPS anomalies (sensor errors vs GPS spoofing)

---

### 4. Composite Claim Score Formula

```
composite_claim_score = disruption_score × pow_confidence × (1 − fraud_probability)
```

**Range:** [0.0, 1.0]

| Scenario | disruption | pow_conf | fraud_prob | composite |
|----------|-----------|----------|-----------|-----------|
| No trigger | 0.0 | 0.9 | 0.1 | 0.0 |
| Genuine disruption | 0.9 | 0.9 | 0.1 | 0.729 |
| High fraud risk | 0.9 | 0.9 | 0.8 | 0.162 |
| Inconclusive | 0.7 | 0.5 | 0.5 | 0.175 |

**Interpretation:**
- **0.0-0.2:** No disruption or high fraud → manual_flag
- **0.2-0.65:** Medium confidence → soft_verify
- **0.65-1.0:** High confidence → auto_payout (if high confidence level)

---

### 5. Confidence Level Assessment

Confidence determines whether high scores can auto-payout.

| Confidence | Criteria | Score Auto-Payout? |
|------------|----------|-------------------|
| **high** | All 3 ML scores available + feature_quality > 0.7 | ✅ Yes if score ≥ 0.65 |
| **medium** | 2/3 ML scores available OR feature_quality 0.4-0.7 | ✅ Yes if score ≥ 0.65 |
| **low** | 1/3 ML scores OR feature_quality < 0.4 | ❌ No, soft_verify always |
| **insufficient** | 0/3 scores OR trigger not fired | ❌ No, soft_verify always |

**Rationale:**
- High confidence = enough signals to trust ML ensemble
- Medium confidence = partial data still OK for auto-payout (redundancy in models)
- Low confidence = human review needed
- Insufficient = clear rejection signal

---

### 6. Routing Decision Matrix

```python
if anti_spoofing_flag:
    route = "manual_flag"  # Override all
elif confidence_level == "insufficient":
    route = "soft_verify"  # Can't proceed
elif score >= 0.65 and confidence in ["high", "medium"]:
    route = "auto_payout"  # Confident genuine
elif score < 0.30:
    route = "manual_flag"  # Fraud risk
else:
    route = "soft_verify"  # Medium risk, needs review
```

**Routing Outcomes:**
- **auto_payout:** Pay worker immediately (Layer 5 expedited path)
- **soft_verify:** Layer 5 initiates soft verification (call worker, GPS check, etc.)
- **manual_flag:** Routes to compliance/fraud team for investigation

---

## Implementation Details

### Score Collector

**Architecture:**
- Consumes from Kafka topic "ml_scores"
- One message per model type (0-4 messages per window per worker)
- Buffers in Redis: `score_buffer:{worker_id}:{minute_bucket_epoch}`

**State Management:**
```
{
  "lstm": { MLScore object },
  "isolation_forest": { IF MLScore object },
  "gbm": { GBM MLScore object },
  "parametric_trigger": { Trigger result },
  "feature_vector": { Feature dict for fallbacks }
}
```

**Timeout Handling:**
- 2-second window per worker×minute_bucket
- After 2s, emit composite score with available scores + `-1.0` sentinels
- Redis TTL 10 seconds auto-expires incomplete buffers

### Score Fusion

**Fallback Priority (conservative chain):**
1. Use actual model output if score >= 0
2. For LSTM: compute heuristic from behavior features
3. For GBM: fall back to IF fraud_risk_score
4. For GBM + IF both timeout: use 1 - loss_plausibility_score

**Explainability Merging:**
- Extract top 3 suspicious timesteps from LSTM
- Extract top 3 anomalous features from IF
- Extract top 3 fraud signals from GBM
- Sort combined list by intensity, return top 15

### Claim Router

**Thresholds (from routing_config.yaml):**
```yaml
low_risk_threshold: 0.65      # Auto-payout trigger
high_risk_threshold: 0.30     # Manual-flag trigger
```

**Flexibility:**
- Config-driven → can adjust thresholds without code deployment
- Per-region overrides possible (future)

### Publisher

**Dual Publication:**
1. **Kafka (streaming):** For Layer 5 real-time payout processing
   - Topic `composite_scores`
   - Topic `routing_decisions`

2. **Redis (state):** For API queries and dashboard
   - Keys stored with 30-minute TTL
   - Enables quick lookups by worker_id

**Guarantees:**
- Kafka: At-least-once delivery (with retries)
- Redis: Best-effort (expiration acceptable)

### FastAPI Debug API

**Endpoints:**

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `GET /health` | Liveness probe | `{ status, timestamp, version }` |
| `GET /v1/composite/{worker_id}` | Latest fused score | `CompositeClaimScore` JSON |
| `GET /v1/routing/{worker_id}` | Latest routing decision | `RoutingDecision` JSON |
| `GET /v1/explain/{worker_id}` | Merged explainability | Top signals + human explanation |
| `GET /v1/dashboard` | Hour-window stats | Routing breakdown, score distribution, model health |

**Dashboard Metrics (last hour):**
- Auto-payout rate (alert if < 20% → model degradation)
- Soft-verify rate
- Manual-flag rate
- Score percentiles (median, P95, P99)
- Model timeout rate

---

## Metrics & Monitoring

### Key Metrics

1. **composite_score_histogram**
   - Buckets: [0-0.3), [0.3-0.65), [0.65-1.0]
   - Alerts on shift in distribution

2. **routing_decision_breakdown**
   - Counter per route type
   - auto_payout_percent gauge (alert if < 20%)

3. **model_timeout_rate_per_model**
   - Separate counters for lstm, if, gbm
   - Alert if any > 5%

4. **fusion_latency_ms**
   - P50, P95, P99
   - Alert if P95 > 100ms

### Alerting

| Alert | Threshold | Action |
|-------|-----------|--------|
| `auto_payout_rate_low` | < 20% | Investigate model degradation |
| `model_timeout_high` | > 5% | Check ML service health |
| `fusion_latency_high` | P95 > 100ms | Optimize fusion or scale horizontally |

---

## Testing Strategy

### Unit Tests (test_score_fusion.py)

- Boundary value testing (score=1.0 when perfect, 0.0 when no trigger)
- Fallback logic (LSTM timeout → heuristic, GBM timeout → IF)
- Confidence level computation (high/medium/low/insufficient)
- Anti-spoofing flag override behavior
- Risk signal merging from all models

### Routing Tests (test_claim_router.py)

- High score + high confidence → auto_payout
- Low score → manual_flag
- Anti-spoofing=True → manual_flag override
- Insufficient confidence → soft_verify
- Metrics tracking

### Integration Tests (test_layer4_integration.py)

1. **Full pipeline:** All scores collected → fused → routed → published
2. **LSTM timeout:** Fallback heuristic used, still produces valid decision
3. **Spoofing override:** Anomaly detected → manual_flag despite high score
4. **All timeouts:** Conservative fallbacks prevent system failure
5. **Fraud detection:** GBM fraud→anti_spoofing→manual_flag

---

## Future Enhancements

1. **Confidence Interval Estimates:** Bayesian fusion to quantify uncertainty
2. **Model Drift Detection:** Monitor score distribution, alert on shift
3. **A/B Testing Framework:** Compare routing thresholds against holdout
4. **Explainability SHAP Integration:** Deeper feature contribution analysis
5. **Region-Specific Thresholds:** Auto-adjust based on local FPR/FNR
6. **Real-time Retraining Signals:** Send corrected outcomes back to Layer 3

---

## Deployment Notes

### Environment Variables

```bash
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
REDIS_URL=redis://redis:6379/2
LAYER4_LOW_RISK_THRESHOLD=0.65
LAYER4_HIGH_RISK_THRESHOLD=0.30
LAYER4_WAIT_TIMEOUT_SECONDS=2.0
```

### Scaling

- **Stateless design:** ScoreCollector, ScoreFuser, ClaimRouter can scale horizontally
- **Redis sharding:** Use Redis cluster for higher throughput
- **Kafka partitioning:** Partition by worker_id for ordering guarantees

### Performance

- Fusion latency: ~10-20ms per score (sub-100ms guarantee)
- Throughput: ~1000 scores/second per instance (with 8+ cores)
- Memory: ~50MB baseline + buffer for Redis TTL-ed data

---

## References

- **FIGGY Architecture:** Layer 4 orchestrator bridges ML inference (Layer 3) and payout processing (Layer 5)
- **Feature Engineering:** Layer 2 produces work behavior, income, environmental features used for fallbacks
- **Disruption Detection:** Parametric trigger flags curfew/strike/bandh events from external feeds
