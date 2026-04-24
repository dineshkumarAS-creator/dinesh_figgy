# Manual Review System Design

## Overview

FIGGY's manual review system handles TIER_3 (high-risk) claims that require human verification before payout. This document explains the architecture, design decisions, and operational considerations.

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 5: Manual Review System                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Queue Management (queue.py)                                 │
│     ├─ Priority calculation (1-3)                               │
│     ├─ Enqueue/assign/release workflow                          │
│     └─ Redis + PostgreSQL persistence                           │
│                                                                  │
│  2. Reviewer Management (reviewers.py)                          │
│     ├─ Reviewer profiles + load tracking                        │
│     ├─ Auto-assignment logic (role, specialisation, load)       │
│     └─ Stats & performance metrics                              │
│                                                                  │
│  3. Claim Context (context_builder.py)                          │
│     ├─ Aggregates: ML, worker history, crowd validation        │
│     ├─ Claude API for human-readable summaries                  │
│     └─ 10-minute cache for performance                          │
│                                                                  │
│  4. Reviewer API (api.py)                                       │
│     ├─ Queue endpoints (GET /v1/review/queue)                   │
│     ├─ Context endpoint (GET /v1/review/claim/{id}/context)    │
│     ├─ Decision endpoint (POST /v1/review/claim/{id}/decide)   │
│     └─ Stats & metrics                                          │
│                                                                  │
│  5. Appeals Flow (appeals.py)                                   │
│     ├─ Appeal submission & 24-hour SLA                          │
│     ├─ State transitions: REJECTED → APPEALED → resolved        │
│     └─ Overturn rate tracking                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Priority Calculation

Priority determines SLA, reviewer assignment eligibility, and routing.

### Tier 1: CRITICAL (2-hour SLA)

**Triggered by any of:**
- Payout amount > ₹1,000
- Worker trust tier == "flagged" (suspicious history)
- Crowd spike detected (unusual crowd activity zone)

**Characteristics:**
- Always assigned to senior/lead reviewers
- Pre-empts all other work
- Monitored for SLA breach every 15 min

**Example:** claim_payout=₹1,500 → priority=1 regardless of worker history

---

### Tier 2: HIGH (4-hour SLA)

**Triggered by any of:**
- Payout amount ₹300–₹1,000
- New worker (first claim) AND disruption_score > 0.7

**Characteristics:**
- Can be assigned to senior/lead (not junior)
- Batched with lower priority items
- Standard SLA monitoring

**Example:** worker_new=true + disruption=0.8 → priority=2

---

### Tier 3: NORMAL (8-hour SLA)

**Default tier for:**
- Payout < ₹300
- Established worker + normal disruption
- Everything not in TIER_1 or TIER_2

**Characteristics:**
- Can be assigned to any reviewer
- Backfilled when higher priorities unavailable
- Longest SLA allows batch processing

**Example:** worker_established=true + payout=₹100 → priority=3

---

## Auto-Assignment Logic

### Decision Tree

```
Incoming high-risk claim (TIER_3)
  ├─ Calculate priority (1, 2, or 3)
  ├─ Find candidate reviewers:
  │  ├─ Filter by role: junior ❌ priority=1 (only senior/lead can take critical)
  │  ├─ Filter by capacity: skip reviewers at max_load
  │  ├─ Filter by specialisation: prefer city/domain match if available
  │  └─ Sort by load ratio (current_load / max_load)
  ├─ Assign to lowest-ratio reviewer
  └─ Update metrics (reviewer.current_load += 1)
```

### Load Balancing Mechanism

**Goal:** Ensure even distribution of claims across reviewers.

**Metric:** `load_ratio = current_load / max_load`

**Example:**
```
Reviewer A (senior):  3/10 = 0.30  ← preferred
Reviewer B (senior):  6/10 = 0.60
Reviewer C (junior):  4/5  = 0.80  (but can't take critical)
```

When claim arrives: assign to Reviewer A (lowest ratio)

**Prevents:**
- One reviewer overloaded while others idle
- Junior reviewers taking high-risk claims
- Specialisation mismatch (city-specific reviewers skip wrong zones)

---

### Role-Based Restrictions

| Role | Max Load | Can Take | Cannot Take |
|------|----------|----------|-------------|
| Junior | 5 | Priority 2, 3 | Priority 1 (CRITICAL) |
| Senior | 10 | All 1, 2, 3 | None |
| Lead | 15 | All 1, 2, 3 | None |

**Rationale:** 
- Juniors are trainees; critical claims need experienced judgment
- Leads can handle most volume + mentor others
- SLA progression ensures complex cases get expert review

---

## Claude API Integration

### Human-Readable Summary Generation

**Use Case:** Reviewers see 30+ ML signals; need plain language explanation.

**Process:**

```
1. Feature extraction: Top 5 IF_signals + Top 5 GBM_signals
2. SHAP importance scores: Why model thinks this is risky
3. Context: Claim amount, worker type, zone disruption
4. Claude request:
   System: "You are a fraud analyst. Summarize risk in 2-3 sentences."
   User: "Signals: motion_continuity=0.45, road_match=0.12, ..."
5. Response: "Worker shows unusual GPS pattern: road match 0.12 vs typical 0.85.
           Motion continuity low for heavy rain zone. High risk."
```

**Why Claude?**
- Faster than training custom model
- Understands context (not just SHAP numbers)
- Explainability matters for disputed decisions
- Can reference real-world constraints (e.g., "typical road_match for zone")

**Fallback:** If API fails, show raw signals + heuristic summary

**Performance:** Expected 2-3s per call; cached for 10 min by claim_id

**Cost:** ~$0.01-0.03 per claim (Sonnet-4); scales with review volume

---

## SLA Breach Detection & Escalation

### Periodic SLA Check (Every 15 minutes)

**Implementation:** APScheduler job calls `queue_service.sla_breach_check()`

**Logic:**
```python
for each assigned item in queue:
    if item.sla_deadline < now and item.status == "assigned":
        mark_as_escalated()
        log_alert(queue_id, reviewer_id, deadline)
```

**After Escalation:**
- Status changes from "assigned" to "escalated"
- Accessible to leads/ops (queue shifts to escalation queue)
- Triggers PagerDuty alert if configured
- Prevents claim aging indefinitely

**Rationale:**
- 15-min check frequency balances responsiveness & compute
- Fast detection prevents SLA violation consequences
- Escalated items removed from reviewer queue

---

## Appeal Flow & Overturn Rate Monitoring

### State Machine

```
Approved/Rejected Claim
  │
  └─ Worker disputes rejection
     │
     ├─ submit_appeal()
     │  ├─ Validate claim status == REJECTED
     │  ├─ Create Appeal record
     │  ├─ Transition: claim.state = APPEALED
     │  └─ Enqueue as PRIORITY=1 (force critical tier)
     │
     ├─ 24-hour SLA for lead reviewer
     │
     └─ decide_appeal()
        ├─ DECISION=APPROVED
        │  └─ claim.state = PAYOUT_PROCESSING
        └─ DECISION=REJECTED
           └─ claim.state = APPEAL_REJECTED (final, non-recoverable)
```

### Overturn Rate Metric

**Definition:** `overturn_rate = approved_appeals / total_decided_appeals`

**Interpretation:**
- **0-5%:** Reviewers validating decisions → OK
- **5-15%:** Healthy range, some appeals justified
- **15-25%:** High; suggests initial reviewers too strict
- **>25%:** Red alert; systematic issue with initial review

**Example:**
- 100 rejections
- 20 appeals submitted
- 16 approved (overturned) + 4 rejected (upheld)
- Overturn rate: 16/20 = **80%** ← 18too high; investigate

### Why Track Overturn Rate?

1. **Quality Control:** Detects reviewer bias/thresholds drift
2. **False Rejection Prevention:** High rate means rejections are questionable
3. **Trends Over Time:** Alert triggers if rate > threshold
4. **Fairness:** Workers shouldn't be denied valid payouts

---

## Reviewer Scoring & Statistics

### Per-Reviewer Metrics

```
ReviewerProfile {
  reviewer_id: UUID,
  name: str,
  role: "junior" | "senior" | "lead",
  total_decided: int = 0,
  approval_rate: float = 0.5,  // % of claims approved
  avg_decision_time_min: float = 0,  // Exponential moving average
  current_load: int = 0,
  max_load: int = 5|10|15,
}
```

### Approval Rate Calculation

Tracks whether reviewer is approving too many (lenient) or too few (strict).

**Formula:** 
```
approval_rate = sum(1 if decision=="approve" else 0) / total_decided
```

**Healthy Range:** 30–70% (depends on domain)
- If <20%: Likely too strict
- If >80%: Likely too lenient

**Usage:**
- Detect biased reviewers
- Balance work assignment
- Performance reviews

### Decision Time Tracking

**Why Track?**
- Reviewers who decide too fast: likely not thorough
- Reviewers who decide too slow: bottleneck risk

**Implementation:** Exponential Moving Average
```
new_avg = 0.9 * old_avg + 0.1 * new_time
```
(Weights recent decisions heavier)

---

## Claim Context Aggregation

### What's Included?

```
ReviewContext {
  claim: full_claim_record,
  claim_history: list[state_transitions],
  feature_snapshot: FeatureVector at claim time,
  risk_breakdown: ML scores from Layer 5,
  ml_explanations: {
    lstm_attention_weights: [30 timesteps],
    if_top_signals: [RiskSignal],
    gbm_top_signals: [RiskSignal],
    human_readable_summary: str  // Claude-generated
  },
  worker_trust_profile: {
    total_claims, approval_rate, flagged_reasons, ...
  },
  crowd_validation: {
    crowd_size, validation_rate, consensus_confidence, ...
  },
  similar_past_claims: [last 5 from worker],
  zone_disruption_map: {city_block: % workers},
  recommended_action: str,  // Auto-generated
  risk_score: float,  // 0-1
}
```

### Performance Optimization

**Caching:** ReviewContext cached in Redis for 10 minutes
- Claim context page slow (~2-3s due to Claude call)
- Cache hit avoids redundant API calls
- Next reviewer sees instant context

**Key:** `review_context:{claim_id}` with 10-min TTL

---

## Kafka Integration

### Published Topics

#### `manual_review_outcomes`
Consumed by Layer 6 (ML model improvement) as ground truth labels.

```json
{
  "queue_id": "uuid",
  "claim_id": "uuid",
  "reviewer_id": "uuid",
  "decision": "approve|reject|request_more_info",
  "rejection_reason": "string|null",
  "payout_override_inr": 500.0,
  "notes": "string|null",
  "confidence": 4,
  "decided_at": "2026-04-15T19:48:31Z",
  "decision_time_min": 8.5
}
```

#### `claim_state_events`
All claim state transitions for audit trail.

```json
{
  "claim_id": "uuid",
  "old_state": "TIER_3_REVIEW",
  "new_state": "PAYOUT_PROCESSING",
  "event_type": "manual_approval",
  "reviewer_id": "uuid",
  "timestamp": "2026-04-15T19:48:31Z"
}
```

---

## Monitoring & Alerts

### Key Metrics

| Metric | Target | Alert If |
|--------|--------|----------|
| Critical queue depth | <10 | >20 |
| Priority 1 SLA breach rate | <2% | >5% |
| Manual approval rate | 30-70% | <20% or >80% |
| Avg review time | <10 min | >20 min |
| All reviewers at max load | Rare | Percentage >50% |
| Appeal overturn rate | <15% | >25% |

### Alert Examples

```
CRITICAL: Priority=1 queue > 20 items
  → Trigger: Insufficient senior/lead capacity
  → Action: Call on-call lead + page escalation team

WARNING: Reviewer A approval rate > 85%
  → Trigger: Possible lenient reviewer
  → Action: QA review sample of approvals

ERROR: SLA breach rate > 5%
  → Trigger: Claims aging in queue
  → Action: Check for stuck assignments + escalate aged items
```

---

## Edge Cases & Special Handling

### Multi-Reviewer Appeals

**Problem:** Appeal overturns initial rejection; what if 3+ reviewers already saw claim?

**Solution:** 
- Appeals are always routed to lead reviewer (different person if possible)
- Decision note must explain why previous review was wrong
- Prevents groupthink; fresh perspective required

### Load Balancing During Shortage

**Problem:** All reviewers at max load; new CRITICAL claim arrives.

**Solution:**
1. Queue remains pending (no assignment)
2. Alert triggered: "All reviewers at capacity"
3. On-call lead called to decide: approve/reject without assignment
4. Or: release lower-priority work to free capacity

### Reviewer Lunch/Break

**Solution:** `release()` endpoint allows reviewer to unassign claim without deciding
- Claim returns to queue with same priority
- Counters reviewer fatigue/burnout

---

## Testing Strategy

### Unit Tests

✅ **Priority Calculation:** All 6 boundary cases tested
✅ **Auto-Assignment:** Load balancing, role filtering, specialisation match
✅ **SLA Breach:** Past deadline detection, escalation marking
✅ **Appeals:** REJECTED→APPEALED→resolved state transitions

### Integration Tests

⏳ **E2E Flow:** Claim → Queue → Assign → Context → Decide → Kafka publish
⏳ **Appeal Flow:** REJECTED → APPEALED → overturned → PAYOUT_PROCESSING
⏳ **Load Test:** 1000 concurrent claims, verify SLA maintained

---

## Appendix: Why These Choices?

### Why 24-hour Appeal SLA?

- **Too short (<12h):** Appeals need thorough re-investigation; leads unavailable 4pm-8am
- **Too long (>48h):** Workers frustrated; extends resolution timeline
- **24h sweet spot:** Business hours + 1 day buffer; human pace

### Why Claude for Summaries?

- **Not fine-tuned LSTM:** Domain-specific, expensive, slow
- **Not hardcoded rules:** Brittle to new features; maintenance burden
- **Claude:** General, fast, explainable, handles edge cases

### Why Redis + PostgreSQL?

- **Redis:** Fast queue operations, expiry support, cache layer
- **PostgreSQL:** Persistent audit trail, complex queries, backup/recovery

### Why Load Ratio (not absolute count)?

- **Absolute:** junior with 5/5 seems full, but senior with 15/15 OK
- **Ratio:** 1.0 = full regardless of role; fair comparison
- **Result:** Balanced workload across all reviewer levels
