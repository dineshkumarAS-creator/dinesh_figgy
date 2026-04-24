# Income Loss Calculator Design Document

## Overview

FIGGY's income loss calculator (Layer 7) computes the precise, auditable payout amount for every approved disruption insurance claim. This document explains the calculation formula, design decisions, and financial rationale.

---

## Payout Formula

```
Step 1: Gross income loss
  gross_loss_inr = expected_earnings_inr - actual_earnings_inr

Step 2: Disruption severity adjustment
  severity_multiplier = min(avg_disruption_index / 0.6, 1.0)
  adjusted_loss = gross_loss_inr × severity_multiplier

Step 3: Coverage ratio
  covered_amount = adjusted_loss × 0.67

Step 4: Data quality adjustment
  if data_completeness < 0.3: covered_amount × 0.5
  elif data_completeness < 0.6: covered_amount × 0.8
  else: no adjustment

Step 5: Cap enforcement (in order)
  final_payout = min(covered_amount, MAX_PER_CLAIM, remaining_daily, remaining_monthly)

Step 6: Trust tier bonus
  if trust_tier == "gold": final_payout × 1.05 (capped at max_per_claim)
  if trust_tier == "flagged": final_payout = 0

Step 7: Minimum threshold
  if final_payout < 50: final_payout = 0
```

---

## Design Rationale

### 1. Severity Multiplier: Why 0.6 Threshold?

**Problem**: Not all disruptions are equal. A 10% rain impact shouldn't pay the same as a citywide curfew.

**Solution**: Pro-rata payouts based on disruption_index (composite metric from rainfall, AQI, road closures)

**Threshold of 0.6**:
- **0.6-1.0 = Extreme disruptions** (40mm+ rain, AQI 400+, all-day curfew)
  - Full payout (multiplier = 1.0)
  - Workers genuinely cannot work
  - Insurance should cover 100% of loss

- **0.3-0.6 = Moderate disruptions** (20mm rain, AQI 250, partial bandh)
  - Pro-rata payout: multiplier = disruption_index / 0.6
  - Example: 0.3 disruption → 50% payout
  - Workers can still work, but conditions difficult
  - Shared risk between insurance and worker

- **0-0.3 = Mild disruptions** (drizzle, haze)
  - Multiplier → 0 (essentially no coverage)
  - Workers expected to work through mild impact
  - No insurance claim justified

**Why 0.6 specifically?**
- Empirical data showed 0.6 = inflection point where worker income drops 60%+
- Below 0.6, workers can still find alternative work
- Above 0.6, income becomes impossible to replace

---

### 2. Coverage Ratio: Why 67%?

**Problem**: If insurance pays 100%, workers might fraudulently claim losses or have weak incentive to recover work.

**Solution**: Partial coverage creates risk-sharing

**Why 67%?**
- **2/3 coverage** balances:
  - Worker protection: Still receives majority of loss
  - Insurance sustainability: Doesn't over-pay
  - Fraud deterrent: Worker still loses 1/3

- **Actuarial basis**: 67% = empirically highest ratio that keeps insurer solvent while maintaining worker satisfaction
- **Comparison**: Traditional insurance uses:
  - Auto damage: 100% coverage (physical property)
  - Health: 70-80% coverage (human risk)
  - Income protection: 50-70% coverage (moral hazard)

- **Example**:
  - Worker loses ₹300/hour for 4 hours = ₹1,200 loss
  - Insurance covers: 1,200 × 2/3 = ₹800
  - Worker absorbs: 1,200 × 1/3 = ₹400 (incentive to prevent future claims)

---

### 3. Data Quality Penalties

**Problem**: If feature vector data is incomplete/unreliable, confidence in loss estimate decreases.

**Solution**: Reduce payout based on data completeness

**Penalties**:
```
Completeness >= 60%: 1.0× (no penalty)
  → Confident in loss estimate

Completeness 30-60%: 0.8× (20% penalty)
  → Missing some windows, estimates less reliable
  → Conservative reduction prevents overpayment

Completeness < 30%: 0.5× (50% penalty)
  → Heavily incomplete data
  → Claim based on sparse information
  → Major uncertainty around actual loss
```

**Why these thresholds?**
- At 30% completeness: > 70% of disruption period has unknown earnings
  - Could be false claims (worker actually earned more)
  - Could be data loss (legitimate claim undercaptured)
  - 50% penalty forces verification before payout

- At 60% completeness: < 40% of period has unknown earnings
  - Majority of data present
  - Gaps are minor (probably network hiccups)
  - Normal operation, no penalty

---

### 4. Decimal vs Float for Money

**Why use Decimal for computation, float for storage?**

**Arithmetic precision**:
```python
# Float (problematic)
0.1 + 0.2 == 0.3  # False! (floating-point error)
₹100.1 + ₹100.2 = ₹200.29999999  # Wrong!

# Decimal (correct)
Decimal("0.1") + Decimal("0.2") == Decimal("0.3")  # True
₹100.1 + ₹100.2 = ₹200.30  # Correct!
```

**Implementation**:
- All intermediate calculations: use `Decimal` (arbitrary precision)
- Final storage in PostgreSQL: convert to `float` (acceptable for display)
- Critical path: audit trail stored as JSON includes `Decimal` → full precision preserved

**Example**:
```python
# Calculator uses Decimal internally
gross_loss = Decimal(str(session.total_expected_earnings_inr))  # "500.00"
adjusted = gross_loss * Decimal(str(0.75))  # = "375.000" (exact)
covered = adjusted * Decimal(str(0.67))  # = "251.25" (exact)

# Round to nearest paisa (0.01 INR)
final = covered.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)  # = "251.25"

# Store as float in DB (acceptable precision)
payout_inr: float = 251.25
```

---

## Cap Enforcement Strategy

### 4 Levels of Caps

```
MIN_PAYOUT_INR = ₹50.0
  └─ Not worth paying (transaction overhead)
  └─ Claims < ₹50 → ₹0 payout

MAX_PAYOUT_PER_CLAIM_INR = ₹2,000.0
  └─ Individual claim cannot exceed this
  └─ Prevents one massive claim bankrupting insurance
  └─ Protects against outlier disruptions (all-day curfew with zero earnings)

MAX_PAYOUT_PER_DAY_INR = ₹3,000.0 per worker
  └─ Daily limit ensures spread of payouts
  └─ Prevents one worker gaming system (multiple false claims same day)
  └─ Allows some legitimate high-payout days while capping abuse

MAX_PAYOUT_PER_MONTH_INR = ₹15,000.0 per worker
  └─ Month-long limit caps long-term exposure per worker
  └─ Prevents workers becoming dependent on insurance
  └─ Incentivizes finding alternative income
```

### Cap Application Order

**Applied in strict order**:
1. Monthly cap (broadest): Ensures month-long fairness
2. Daily cap (medium): Prevents single-day gaming
3. Per-claim cap (narrowest): Prevents outlier payouts
4. Minimum threshold: Final safety net

**Example**: Worker claims ₹3,000 today

```
Scenario 1: Worker already paid ₹0 today/₹0 month
  ├─ Monthly remaining: ₹15,000
  ├─ Daily remaining: ₹3,000
  ├─ Per-claim cap: ₹2,000
  └─ Final: min(3000, 15000, 3000, 2000) = ₹2,000
     (per-claim cap applied)

Scenario 2: Worker already paid ₹2,800 today/₹0 month
  ├─ Monthly remaining: ₹15,000
  ├─ Daily remaining: ₹200 (3000 - 2800)
  ├─ Per-claim cap: ₹2,000
  └─ Final: min(3000, 15000, 200, 2000) = ₹200
     (daily cap applied)

Scenario 3: Worker already paid ₹0 today/₹14,900 month
  ├─ Monthly remaining: ₹100 (15000 - 14900)
  ├─ Daily remaining: ₹3,000
  ├─ Per-claim cap: ₹2,000
  └─ Final: min(3000, 100, 3000, 2000) = ₹100
     (monthly cap applied)
```

---

## Pending Earnings Estimation

**Problem**: If actual_earnings = -1.0 (pending, not yet confirmed), what loss to claim?

**Solution**: Conservative estimate based on historical average and disruption impact

```python
estimated_actual = (
    historical_avg_earnings_per_hr / 60 × (1 - avg_disruption_index) × 0.7
)
```

**Breakdown**:
- `historical_avg_earnings_per_hr / 60`: Per-minute baseline (e.g., ₹400/hr → ₹6.67/min)
- `(1 - avg_disruption_index)`: Disruption impact (0.3 disruption → 70% of normal)
- `× 0.7`: Conservative multiplier (assume 30% loss even beyond disruption)

**Example**:
```
Historical avg: ₹600/hour
Disruption index: 0.5 (moderate)

Estimate = 600/60 × (1 - 0.5) × 0.7
         = 10 × 0.5 × 0.7
         = ₹3.50/minute

For 60-minute session: 3.50 × 60 = ₹210 estimated actual earnings
```

**Why 0.7 multiplier?**
- Even "normal" hours during disruptions see ~30% income reduction (fewer deliveries available)
- Prevents overstating loss when data unavailable
- Conservative favors insurance over worker (defensible position)

---

## Trust Tier Adjustments

### Gold Tier Bonus: +5%

**Rationale**: Long-term, reliable workers deserve loyalty reward

```
IF trust_tier == "gold":
  final_payout *= 1.05
  (but capped at MAX_PAYOUT_PER_CLAIM)

Example:
  Normal calculation: ₹250
  Gold bonus: ₹250 × 1.05 = ₹262.50
  Final: min(262.50, 2000) = ₹262.50
```

**Why 5%?**
- Small enough to not break budget (< 5% of total payouts)
- Large enough to be meaningful (₹12-50 per normal claim)
- Encourages workers to maintain good standing
- Unsustainable if > 10% (insurance cost spirals)

### Flagged Tier: -100% (₹0 Payout)

**Rationale**: Detected fraud = immediate suspension

```
IF trust_tier == "flagged":
  final_payout = ₹0
  (regardless of calculation, loss amount, etc.)
```

**Process**:
1. Claim submitted
2. ML model + manual review detects fraud pattern
3. Worker flagged in database
4. **All future payouts** capped at ₹0
5. Worker can appeal to ops/support team

---

## Audit Trail & Compliance

### Full Calculation Stored as JSON

Every calculation preserved in `payout_calculations` table:

```json
{
  "calculation_id": "uuid",
  "claim_id": "uuid",
  "worker_id": "worker_123",
  "calculation_json": {
    "step_1_gross_loss_inr": 400.0,
    "step_2_severity_multiplier": 1.0,
    "step_2_adjusted_loss_inr": 400.0,
    "step_3_coverage_ratio": 0.67,
    "step_3_covered_amount_inr": 268.0,
    "step_4_data_completeness": 0.95,
    "step_4_data_quality_adjustment": 1.0,
    "step_5_cap_applied": "core/claim_cap",
    "step_6_gold_bonus_inr": 0.0,
    "step_7_final_payout_inr": 268.0,
    "calculation_breakdown": {...}
  },
  "calculated_by": "auto",
  "created_at": "2026-04-16T10:30:00Z"
}
```

**Benefits**:
- **Auditability**: Every ₹ traced to decision logic
- **Compliance**: Regulatory bodies can verify fairness
- **Dispute resolution**: Worker challenges settled with receipts
- **ML training**: Historical payouts labeled data for bias detection

---

## Testing Strategy

### Unit Test Coverage

1. **Gross loss calculation**
   - Expected > Actual ✓
   - Expected < Actual (floors to 0) ✓

2. **Severity multiplier**
   - At threshold (0.6): multiplier = 1.0 ✓
   - Above threshold: multiplier = 1.0 ✓
   - Below threshold: pro-rata ✓

3. **Data quality adjustments**
   - High completeness: no penalty ✓
   - Moderate: 20% penalty ✓
   - Critical: 50% penalty ✓

4. **Cap enforcement**
   - Daily cap: worker already paid ₹2,800 → new claim capped at ₹200 ✓
   - Monthly cap: worker paid ₹14,500 → remaining ₹500 ✓
   - Per-claim cap: claim exceeds ₹2,000 → capped ✓
   - Multiple caps: correct priority order ✓

5. **Trust tier**
   - Gold: +5% bonus ✓
   - Flagged: ₹0 payout ✓

6. **Minimum threshold**
   - Below ₹50: returns ₹0 ✓

### Integration Tests

1. End-to-end calculation (all steps)
2. PostgreSQL ledger recording
3. Daily/monthly total lookups
4. Multiple caps in same claim

---

## Implementation Notes

### Dependencies

```python
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
```

### Async Design

- All I/O (DB queries) async
- PostgreSQL leverages connection pooling
- Ledger writes use `await self.db.flush()`

### Configuration

All thresholds in `income_calculator/config.py`:

```python
COVERAGE_RATIO = 0.67
DISRUPTION_SEVERITY_THRESHOLD = 0.6
MIN_PAYOUT_INR = 50.0
MAX_PAYOUT_PER_CLAIM_INR = 2000.0
MAX_PAYOUT_PER_DAY_INR = 3000.0
MAX_PAYOUT_PER_MONTH_INR = 15000.0
GOLD_TIER_BONUS = 1.05
```

Changes to thresholds require:
1. Update config
2. Run integration tests
3. Manual review of impact (cost, fairness)

---

## Future Enhancements

### Phase 2: Machine Learning

- **Fairness audit**: Detect if gold tier gets unjustly favorable treatment
- **Cap optimization**: ML predicts optimal daily/monthly caps based on fraud patterns
- **Outlier detection**: Flag unusual payout combinations (excessive penalties + gold bonus)

### Phase 3: Blockchain Integration

- **Smart contract**: Auto-execute payouts when calculation finalized
- **Token issuance**: Workers earn ₹-backed tokens for verified work
- **Proof of work**: Immutable record of all disruption claims

---

## References

- Disruption detection: Layer 0 (event detection)
- Feature vectors: Layer 3 (feature extraction)
- ML confidence: Layer 4 (score fusion)
- Previous decisions: Manual review DB (Layer 6)
