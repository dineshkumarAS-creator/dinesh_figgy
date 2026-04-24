# Business Logic Architecture

The Figgy GigShield backend is driven by deterministic, rule-based micro-services designed to handle policy lifecycles and autonomous claims.

## 1. Automated Weather Polling & Auto-Triggers
The backend operates an `APScheduler` cron job (`app/utils/scheduler.py`). Every 15 minutes, it:
1. Checks weather conditions against defined thresholds (e.g., Rain > 40 mm/hr, AQI > 400).
2. Identifies all subscribed workers in the affected `zone`.
3. Calls the internal `POST /api/claim/auto_trigger` to instantiate a pending claim for those workers.

## 2. Fraud & Proof-of-Work (PoW) Engine
When a claim is processed, the backend queries the worker's recent telemetry logs to build a "Proof of Work" (PoW) context.
The `fraud.py` module applies a rules-based scoring system:
- **Claimed Loss Constraint:** Flags if the claimed loss exceeds 2x the daily average.
- **Activity Velocity:** Flags if there's a highly anomalous delivery count during the disruption.
- **GPS Distance Validation:** Flags if tracked GPS distances denote regular movement despite a claimed "blockage".

Based on these flags, the claim receives a risk score:
- **LOW**: Instantly proceeds to payout.
- **MEDIUM / HIGH**: Diverted to the Manual Review queue (Admin Dashboard).

## 3. Parametric Payout Calculation
If approved, the platform calculates dynamic compensation within `calculations.py`:
- `Expected Earnings` = (Avg Daily Earnings) / (Daily Hours) * (Disruption Window Hours).
- `Actual Earnings` = Telemetry delivery count * rate.
- `Income Loss` = Expected - Actual.
- `Eligible Payout` = Income Loss capped by the user's Tier Level (Lite, Smart, Elite).

Additionally, Elite tier users may receive a **Surge Bonus** (10-20%) if the disruption is categorized as extreme.

## 4. Payment Integrations
- **Premium Collection**: Handled on the Flutter frontend via Razorpay Standard checkouts (or Subscriptions API).
- **Disbursements**: Handled on the backend via Razorpay X (Payouts API). The system creates a Fund Account attached to the worker's UPI ID and processes the payout synchronously.

## 5. Security & Idempotency
All claim records guarantee idempotency. A worker cannot be auto-triggered twice in the same day for the same disruption. Payout instructions to Razorpay include a unique `claim_id` reference key to prevent double settlements during network retries.
