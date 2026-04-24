# Figgy GigShield - Comprehensive Documentation

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Business Logic & Architecture](#2-business-logic--architecture)
3. [Claim Management Lifecycle](#3-claim-management-lifecycle)
4. [UI Screen Documentation](#4-ui-screen-documentation)
5. [API Reference](#5-api-reference)
6. [Local Environment & Setup](#6-local-environment--setup)

---

## 1. Project Overview

**Figgy GigShield** is an innovative, parametric micro-insurance platform designed specifically for delivery gig workers in India (e.g., those working for Zomato, Swiggy, Zepto). It provides instant financial protection against involuntary income loss caused by external disruptions such as severe weather, floods, extreme heat, or strikes.

### The Problem
Gig workers face daily uncertainties. A traditional insurance model takes weeks to process a claim, requires manual adjustments, and involves significant paperwork, making it completely unviable for daily wage earners.

### The Solution
Figgy GigShield uses **parametric triggers** (e.g., rainfall > 40mm/hr) integrated with **Proof-of-Work (PoW)** telemetry to automatically initiate, verify, and disburse payouts within minutes, without human intervention.

### Supported Tiers
Workers can subscribe to one of three tiers based on their daily earning averages:
- **Lite (₹29/week)**: Covers basic rain disruptions. Up to ₹300 max payout.
- **Smart (₹49/week)**: Covers rain, heat, and strikes. Up to ₹500 max payout.
- **Elite (₹89/week)**: Premium coverage, highest payouts (up to ₹750), includes surge bonuses.

---

## 2. Business Logic & Architecture

The Figgy GigShield backend is driven by deterministic, rule-based micro-services designed to handle policy lifecycles and autonomous claims.

### Core Tech Stack
1. **Frontend**: Flutter (Web/Android). High-performance reactive UI.
2. **Backend**: Python / Flask. RESTful JSON API.
3. **Database**: MongoDB (with fallback in-memory dicts for demo modes).
4. **Third-Party Services**: Razorpay Subscriptions, Razorpay Payouts, Firebase FCM.

### Automated Weather Polling & Auto-Triggers
The backend operates an `APScheduler` cron job (`app/utils/scheduler.py`). Every 15 minutes, it:
1. Checks weather conditions against defined thresholds (e.g., Rain > 40 mm/hr, AQI > 400).
2. Identifies all subscribed workers in the affected `zone`.
3. Calls the internal `POST /api/claim/auto_trigger` to instantiate a pending claim for those workers.

### Fraud & Proof-of-Work (PoW) Engine
The `fraud.py` module applies a rules-based scoring system:
- **Claimed Loss Constraint:** Flags if the claimed loss exceeds 2x the daily average.
- **Activity Velocity:** Flags if there's a highly anomalous delivery count during the disruption.
- **GPS Distance Validation:** Flags if tracked GPS distances denote regular movement despite a claimed "blockage".

Based on these flags, the claim receives a risk score:
- **LOW risk**: Instantly proceeds to calculated payout.
- **HIGH / MEDIUM risk**: Diverted to the Manual Review queue (Admin Dashboard).

### Parametric Payout Calculation
If approved, dynamic compensation is derived within `calculations.py`:
- `Expected Earnings` = (Avg Daily Earnings) / (Daily Hours) * (Disruption Window Hours).
- `Actual Earnings` = Telemetry delivery count * rate.
- `Income Loss` = Expected - Actual.
- `Eligible Payout` = Income Loss capped by the user's Tier Level.

Elite tier users may receive a **Surge Bonus** (10-20%) if the disruption is categorically extreme.

---

## 3. Claim Management Lifecycle

This outlines the steps from initialization to final payout processing within a Figgy claim.

### A. Initialization (Two Paths)
**1. Auto-Trigger (Parametric)**
- Handled by `POST /api/claim/auto_trigger`.
- Instantiated automatically. The claim starts at `status: verifying` and immediately enters the background worker queue (`verify_and_payout`).

**2. Manual Submission**
- Handled by `POST /api/claim/manual`. Executed by the worker.
- Starts at `status: under_review` and awaits the pipeline worker execution.

### B. The 10-Step Pipeline Orchestrator (`claim_processor.py`)
All claims pass through the Verify-and-Payout Orchestrator:
1. **Load State**: Retrieve claim & worker from database.
2. **Contextualize**: Synthesize telemetry records (GPS km, online mins).
3. **Notify Event**: Dispatch FCM notification.
4. **Fraud Check**: Score the telemetry context.
5. **Route Action**: If High/Medium risk, set to `manual_review` and pause.
6. **Quantify Loss**: Calculate `Income Loss` (Expected vs Actual).
7. **Calculate Payout**: Derive sum based on tier caps and weather surge multiplier.
8. **Approve State**: Transition claim to `approved` locally.
9. **Dispatch Payment**: Relay HTTP instruction to Razorpay Payouts API.
10. **Finalize**: Receive Razorpay confirmation. Update claim to `paid` or `payment_failed`.

### C. State Polling
The Flutter application is stateless regarding processing logic. It relies on short-polling:
- Repeatedly hits `GET /api/claim/status/<claim_id>`.
- Supports terminal states: `paid`, `rejected`, `manual_review`, and `payment_failed`.
- *Mocking Hack*: Setting a user's UPI ID to `fail@ybl` simulates a Razorpay connection error for testing the `payment_failed` branch.

---

## 4. UI Screen Documentation

The Flutter frontend maintains an ultra-premium, modern, and engaging user interface specifically optimized for high visual fidelity in outdoor dark-mode environments.

### Core Navigation Architecture
Connected via an animated Bottom Navigation Bar:
1. **Radar Screen**: Acts as the operational center. Displays live, location-aware weather and disruption alerts using a dynamic Glassmorphism UI.
2. **Earnings / Home Screen**: Overview of daily metrics (Deliveries done, Income generated) predicting delays.
3. **Insurance Dashboard**: Shows the active policy details, daily premium deductions, and a paginated list of payout history.
4. **Profile Screen**: Manages user details and linked UPI configurations.

### Secondary Modals & Wizards
1. **Manual Claim Submission (`manual_claim_screen.dart`)**: A step-by-step form allowing workers to report localized localized street flooding or blockades.
2. **Claim Processing Screen (`claim_processing_screen.dart`)**: The emotional centerpiece. Locks the screen and smoothly transitions via animations through `Receiving` → `Verifying` → `Calculating`.
3. **Claim Details / Receipt Screen (`claim_details_screen.dart`)**: Distinctly shows a massive bold "PAID" validation checkmark. Breaks down the income calculation, surge bonuses applied, and final payout references in a receipt format.
4. **Policy Registration Wizard (`registration_screen.dart`)**: A seamless onboarding carousel for new workers.

---

## 5. API Reference

All requests must route through `server_url/api/...`

### `POST /api/claim/manual`
Submit a new manual claim based on localized disruptions.
- **Body**: `worker_id`, `claim_type`, `start_time`, `end_time`, `description`, `estimated_loss`.
- **Response**: `201 Created` with `claim_id`.

### `GET /api/claim/status/<claim_id>`
Polled endpoint. Retrieves the real-time processing outcome string.
- **Response**: `200 OK` housing a dynamically mapped `ui_message` and standard state object.

### `GET /api/claim/list/<worker_id>`
Retrieves a worker-specific history representation of active and previous claims.
- **Response**: `200 OK` returning an array of `{claim_id, date, compensation, status}`.

---

## 6. Local Environment & Setup

To launch the Figgy stack locally for demonstrations:

1. **Set up Python Backend**
   ```bash
   cd figgy_backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   
   # Add keys to .env (RAZORPAY_KEY_ID, FCM keys, OPENWEATHER_API_KEY)
   # Run the server
   python run.py
   ```
   > The backend will run on `http://127.0.0.1:5000`

2. **Set up Flutter Frontend**
   ```bash
   cd Figgy-main
   flutter pub get
   flutter run -d chrome
   ```
   > Ensure you have `flutter` installed. The app will open optimally in Chrome.

3. **Admin Dashboard**
   Navigate to `http://localhost:5000/admin/` to view the comprehensive, Flask-based operations command center.
