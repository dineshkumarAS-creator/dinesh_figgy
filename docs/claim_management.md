# Claim Management Documentation

This document outlines the lifecycle of a Figgy GigShield claim, explaining the steps from initialization to final payout processing.

## The Two Paths of Initialization
Claims can be initiated through two distinct channels, but both ultimately converge into the same processing pipeline.

**1. Auto-Trigger (Parametric)**
- Handled by `POST /api/claim/auto_trigger`.
- Instantiated automatically if severe weather is detected.
- The claim starts at `status: verifying` and immediately enters the background worker queue (`verify_and_payout`), making the resolution practically instantaneous.

**2. Manual Submission**
- Handled by `POST /api/claim/manual`.
- Executed by the worker.
- Starts at `status: under_review` and awaits the pipeline worker execution.

## The Pipeline Orchestrator (`claim_processor.py`)
All claims pass through the 10-step Verify-and-Payout Orchestrator:
1. **Load State**: Retrieve claim & worker from database.
2. **Contextualize**: Synthesize telemetry records (GPS km, online mins).
3. **Notify Event**: Dispatch FCM notification indicating processing has started.
4. **Fraud Check**: Score the telemetry context against expected norms (Rule-based constraints).
5. **Route Action**: If High/Medium risk, pause execution and set to `manual_review`.
6. **Quantify Loss**: Calculate `Income Loss` by comparing `Expected` vs `Actual` earnings.
7. **Calculate Payout**: Derive final sum based on tier caps and applicable weather surge multiplier.
8. **Approve State**: Transition claim to `approved` locally.
9. **Dispatch Payment**: Relay standard HTTP instruction to Razorpay Payouts API.
10. **Finalize**: Receive Razorpay confirmation. Update claim to `paid` or `payment_failed`.

## State Polling (Frontend Integration)
The Flutter application is stateless regarding the processing. Instead, it relies on short-polling:
- It repeatedly hits `GET /api/claim/status/<claim_id>`.
- The endpoint returns mapped `ui_message` values depending on the state of the Pipeline orchestrator.

### Supported Terminal States
- `paid`: Successful transaction. Money is in the worker's bank.
- `rejected`: Claim dropped due to complete lack of verifiable disruption context.
- `manual_review`: Paused. The Figgy Admin must manually advance or drop the claim from the Command Center.
- `payment_failed`: The claim was authorized and rules successfully applied, but the Razorpay Bank transfer bounced (e.g., inactive beneficiary UPI, insufficient funds).

## Testing Error States
- Setting a user's UPI ID to `fail@ybl` and submitting a claim will specifically mock-trigger a Razorpay connection error, allowing the `payment_failed` branch to be thoroughly evaluated in demos.
