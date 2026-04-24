# Figgy — GigShield Platform Documentation

> **Version:** 1.0 · **Last Updated:** March 2026 · **Status:** Active Development (Hackathon Build)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Project Structure](#3-project-structure)
4. [Technology Stack](#4-technology-stack)
5. [Environment Setup](#5-environment-setup)
6. [Running the Application](#6-running-the-application)
7. [Backend — Flask API](#7-backend--flask-api)
8. [Frontend — Flutter Web & Mobile](#8-frontend--flutter-web--mobile)
9. [GigShield Registration Flow (4-Step Wizard)](#9-gigshield-registration-flow-4-step-wizard)
10. [Razorpay Payment Integration](#10-razorpay-payment-integration)
11. [Insurance Policy Lifecycle](#11-insurance-policy-lifecycle)
12. [Insurance Tiers & Pricing](#12-insurance-tiers--pricing)
13. [Key Files Reference](#13-key-files-reference)
14. [Known Limitations & TODOs](#14-known-limitations--todos)

---

## 1. Project Overview

**Figgy** is a parametric micro-insurance platform for gig workers (food delivery riders on Swiggy, Zomato, Zepto, Dunzo). The product — **GigShield** — provides automatic weekly income protection triggered by adverse weather (heavy rain, extreme heat, severe pollution) without requiring riders to file claims manually.

### Core Value Proposition
- **Rs.49–Rs.99/week** premiums for full income protection
- **Zero-touch claims** — payouts triggered by real weather/pollution data
- **One-Tap Activation** via UPI / Razorpay
- **Multi-language support** — English, Hindi, Marathi, Tamil
- Works on **mobile** (Android/iOS) and **web** (Chrome)

---

## 2. Architecture Diagram

```
+--------------------------------------------------------------+
|                        USER DEVICE                           |
|                                                              |
|   Flutter App (Web: localhost:8080 / Mobile: APK)           |
|   +-----------+  +----------+  +----------+  +----------+   |
|   |Onboarding |  | Register |  |  Demand  |  | Profile  |   |
|   |  Screen   |  |  Wizard  |  |  Screen  |  |  Screen  |   |
|   +-----+-----+  +----+-----+  +----+-----+  +----+-----+   |
|         +---------------+----------+---------------+         |
|                         |                                    |
|                HTTP (localhost:5000)                         |
+-------------------------+---------+--------------------------+
                          |
+--------------------------v---------------------------------------+
|              Flask Backend (Python 3.x)                         |
|                                                                  |
|  +--------------+  +-------------+  +--------------------+      |
|  | /api/worker  |  | /api/payment|  |    /api/terms      |      |
|  | fetch        |  | create_order|  |    /current        |      |
|  | register     |  | verify      |  |    /               |      |
|  | list         |  +------+------+  +--------------------+      |
|  | cancel_policy|         |                                      |
|  +--------------+         v                                      |
|                    +------------+                                |
|  +--------------+  | Razorpay   |                               |
|  | In-Memory    |  | Python SDK |                               |
|  | (Demo Mode)  |  +------------+                               |
|  +------+-------+       |                                       |
|         |               v                                       |
|  +------v-------+  Razorpay Servers (api.razorpay.com)         |
|  |   MongoDB    |                                               |
|  |  (Optional)  |                                               |
|  +--------------+                                               |
+------------------------------------------------------------------+
```

---

## 3. Project Structure

```
Figgybackend-main/
+-- Figgy-main/                          # Flutter Frontend
|   +-- lib/
|   |   +-- main.dart                    # App entry point
|   |   +-- models/
|   |   |   +-- ride.dart                # Ride model + global notifier
|   |   +-- screens/
|   |   |   +-- onboarding_screen.dart   # Splash / Get Started
|   |   |   +-- registration_screen.dart # 4-step GigShield wizard
|   |   |   +-- main_wrapper.dart        # Bottom nav + tab routing
|   |   |   +-- demand_screen.dart       # Home / Live demand map
|   |   |   +-- earnings_screen.dart     # Earnings analytics
|   |   |   +-- radar_screen.dart        # Weather radar
|   |   |   +-- insurance_screen.dart    # Insurance dashboard
|   |   |   +-- profile_screen.dart      # Worker profile + policy mgmt
|   |   |   +-- history_screen.dart      # Ride history
|   |   |   +-- live_tracking_screen.dart
|   |   |   +-- cancellation_screen.dart
|   |   |   +-- claim_details_screen.dart
|   |   |   +-- claim_processing_screen.dart
|   |   |   +-- fraud_verification_screen.dart
|   |   |   +-- manual_claim_screen.dart
|   |   |   +-- pow_verification_screen.dart
|   |   +-- theme/
|   |       +-- app_theme.dart           # Global color & typography tokens
|   |       +-- registration_theme.dart  # Registration wizard theme
|   +-- web/
|   |   +-- index.html                   # Web entry (Razorpay JS included)
|   |   +-- manifest.json
|   +-- pubspec.yaml                     # Flutter dependencies
|
+-- figgy_backend/                       # Python Flask Backend
|   +-- .env                             # Secret keys (not committed to git)
|   +-- requirements.txt                 # Python dependencies
|   +-- config.py                        # App config (reads .env)
|   +-- run.py                           # Server entry point
|   +-- app/
|       +-- __init__.py                  # Flask app factory + CORS
|       +-- models.py                    # DB handler + Terms store
|       +-- routes/
|       |   +-- worker.py                # Worker CRUD endpoints
|       |   +-- payment.py               # Razorpay order + verify
|       |   +-- terms.py                 # Policy T&C endpoints
|       +-- utils/
|           +-- mock_generator.py        # Deterministic mock worker data
|
+-- DOCUMENTATION.md                     # This file
```

---

## 4. Technology Stack

### Frontend

| Layer | Technology | Version |
|---|---|---|
| Framework | Flutter | SDK ^3.10.4 |
| Language | Dart | Latest stable |
| Fonts | Google Fonts | ^6.2.1 |
| Maps | flutter_map + latlong2 | ^7.0.2 / ^0.9.1 |
| HTTP Client | http | ^1.6.0 |
| Local Storage | shared_preferences | ^2.2.3 |
| Payment (Mobile) | razorpay_flutter | ^1.3.6 |
| Payment (Web) | Razorpay JS Checkout | v1 (CDN) |

### Backend

| Layer | Technology | Version |
|---|---|---|
| Framework | Flask | 2.2.5 |
| Database | MongoDB (optional) | via pymongo 4.5.0 |
| CORS | flask-cors | 4.0.0 |
| Env Manager | python-dotenv | 1.0.0 |
| Payment SDK | razorpay | 1.4.1 |
| DNS | dnspython | 2.4.2 |

---

## 5. Environment Setup

### 5.1 Backend `.env` File

Location: `figgy_backend/.env`

```env
# Razorpay Test Keys
RAZORPAY_KEY_ID=rzp_test_SWtNUFcQLg64E9
RAZORPAY_KEY_SECRET=z3B3qvi2e1s59LWRKAOw0If3

# MongoDB (optional — leave blank for in-memory demo mode)
# MONGO_URI=mongodb://localhost:27017/figgy
# MONGO_URI_ATLAS=mongodb+srv://<user>:<pass>@cluster.mongodb.net/figgy

# Toggle DB (default: False = in-memory)
# USE_DB=True

# Server config (optional)
# HOST=0.0.0.0
# PORT=5000
# FLASK_DEBUG=True
```

> IMPORTANT: Never commit `.env` to git. It is listed in `.gitignore`.

### 5.2 Prerequisites

| Tool | Min Version | Install |
|---|---|---|
| Python | 3.9+ | python.org |
| Flutter SDK | 3.10+ | flutter.dev |
| Chrome | Latest | google.com/chrome |
| MongoDB | 6+ (optional) | mongodb.com |

---

## 6. Running the Application

### Step 1 — Install backend dependencies

```powershell
cd figgy_backend
pip install -r requirements.txt
```

### Step 2 — Start Flask backend

```powershell
python run.py
# Starts at: http://localhost:5000
# Health check: GET http://localhost:5000/health
```

### Step 3 — Run Flutter on Chrome

```powershell
# From Figgy-main/ directory
flutter run -d chrome --web-port 8080
# App opens at: http://localhost:8080
```

### Step 4 — Alternative: Run on Windows Desktop

```powershell
flutter run -d windows
```

### Flutter Hot Reload Commands

| Key | Action |
|---|---|
| `r` | Hot reload |
| `R` | Hot restart |
| `q` | Quit |
| `d` | Detach (leave app running) |

---

## 7. Backend — Flask API

### 7.1 App Factory and Configuration

`config.py` reads environment variables:

```python
class Config:
    MONGO_URI           = os.getenv("MONGO_URI", "mongodb://localhost:27017/figgy")
    USE_DB              = os.getenv("USE_DB", "False").lower() == "true"
    RAZORPAY_KEY_ID     = os.getenv("RAZORPAY_KEY_ID")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
```

CORS is fully open for all origins (development only):
```python
CORS(app, resources={r"/*": {"origins": "*"}})
```

Three blueprints are registered:
- `worker_bp` → `/api/worker`
- `payment_bp` → `/api/payment`
- `terms_bp` → `/api/terms`

---

### 7.2 API Endpoints Reference

---

#### GET /health

Health check endpoint.

**Response 200:**
```json
{ "status": "ok" }
```

---

#### POST /api/worker/fetch

Fetches a worker profile by Swiggy ID or phone number. Uses deterministic mock data.

**Request Body:**
```json
{ "swiggy_id": "SWG101" }
```
or
```json
{ "phone": "7550080899" }
```

**Response 200:**
```json
{
  "status": "success",
  "data": {
    "worker_id": "GS-OVVSRL",
    "name": "Rider_899",
    "phone": "7550080899",
    "platform": "Swiggy",
    "zone": "North",
    "income_category": "Medium",
    "today_performance": {
      "earnings": 520,
      "active_hours": 5,
      "deliveries": 12
    },
    "bank_details": {
      "upi_id": "7550080899@okaxis",
      "bank_name": "State Bank of India",
      "account_number": "XXXX12345678",
      "ifsc_code": "SBIN0001234"
    },
    "kyc_details": {
      "aadhaar_number": "XXXX-XXXX-1234",
      "pan_number": "ABCDE1234F",
      "driving_license": "TN-1234567890",
      "vehicle_type": "Bike",
      "vehicle_number": "TN-10-AB-1234"
    },
    "earnings": {
      "avg_daily_earnings": 714,
      "weekly_earnings": 5000,
      "monthly_earnings": 22000,
      "total_earnings": 150000
    },
    "work_stats": {
      "daily_hours": 8,
      "weekly_deliveries": 100,
      "total_deliveries": 3200,
      "acceptance_rate": 92,
      "rating": 4.6
    },
    "incentives": {
      "current_bonus": 500,
      "weekly_target": 120,
      "completed_target": 100,
      "surge_earnings": 300
    }
  }
}
```

**Response 404:** ID not found in partner records.

---

#### POST /api/worker/register

Registers a gig worker and activates their GigShield policy.

**Request Body:**
```json
{
  "name": "Rahul Sharma",
  "phone": "9000000000",
  "platform": "Swiggy",
  "zone": "North",
  "daily_hours": 8,
  "weekly_deliveries": 100,
  "avg_daily_earnings": 714,
  "weekly_earnings": 5000,
  "swiggy_id": "SWG101"
}
```

**Response 201:**
```json
{
  "status": "success",
  "message": "Worker registered successfully",
  "worker_id": "GS-AB12CD",
  "data": { "...full worker document..." }
}
```

**Income Category Logic:**

| avg_daily_earnings | Category | Backend Premium |
|---|---|---|
| Less than Rs.700 | Low | Rs.10/week |
| Rs.700 to Rs.1000 | Medium | Rs.20/week |
| More than Rs.1000 | High | Rs.35/week |

---

#### GET /api/worker/list

Returns all registered workers (from DB or in-memory store).

**Response 200:**
```json
{
  "status": "success",
  "count": 3,
  "data": [ { "...worker object..." }, { "..." } ]
}
```

---

#### POST /api/worker/cancel_policy

Marks a worker's policy as cancelled.

**Request Body:**
```json
{ "swiggy_id": "SWG101" }
```

**Response 200:**
```json
{
  "status": "success",
  "message": "Policy cancelled successfully",
  "data": { "...updated worker object..." }
}
```

---

#### POST /api/payment/create_order

Creates a Razorpay order before the checkout UI is launched.

**Request Body:**
```json
{ "amount": 68 }
```
Amount is in whole INR (rupees). Backend converts to paise (x100).

**Response 200:**
```json
{
  "status": "success",
  "order_id": "order_PxQr12345ABC",
  "amount": 6800,
  "currency": "INR",
  "key_id": "rzp_test_SWtNUFcQLg64E9"
}
```

> Demo Mode (no .env keys): Returns `order_demo_<timestamp>` so UI can still complete the flow.

---

#### POST /api/payment/verify

Verifies Razorpay payment using HMAC-SHA256 signature check.

**Request Body:**
```json
{
  "razorpay_payment_id": "pay_AbC123",
  "razorpay_order_id": "order_PxQr12345ABC",
  "razorpay_signature": "abc123...sha256_hex_digest"
}
```

**Response 200:**
```json
{ "status": "success", "message": "Payment verified successfully" }
```

**Response 400:**
```json
{ "status": "error", "message": "Invalid payment signature" }
```

**Verification algorithm:**
```python
msg = f"{razorpay_order_id}|{razorpay_payment_id}"
generated = hmac.new(key_secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
is_valid = (generated == razorpay_signature)
```

---

#### GET /api/terms/current?language=English

Returns the latest active Terms and Conditions document.

**Query Parameters:**
- `language`: `English` | `Hindi` | `Marathi` | `Tamil` (default: `English`)

**Response 200:**
```json
{
  "status": "success",
  "version": "1.0",
  "data": {
    "language": "English",
    "version": "1.0",
    "effective_from": "2026-03-01",
    "sections": [
      { "title": "1. Introduction", "content": "GigShield is a parametric micro-insurance..." },
      { "title": "2. Coverage", "content": "..." },
      { "title": "3. What is NOT Covered", "content": "..." },
      { "title": "4. Policy Period and Premium", "content": "..." },
      { "title": "5. Claim Process", "content": "..." },
      { "title": "6. Your Responsibilities", "content": "..." },
      { "title": "7. Fraud Prevention", "content": "..." },
      { "title": "8. Cancellation and Refund", "content": "..." },
      { "title": "9. Dispute Resolution", "content": "..." },
      { "title": "10. Important Note", "content": "..." }
    ]
  }
}
```

---

### 7.3 Database and Storage

| Mode | USE_DB setting | Storage Backend | Best For |
|---|---|---|---|
| Demo Mode (default) | False | Python list in memory | Hackathon, local dev |
| DB Mode | True | MongoDB Atlas or Local | Production |

**DB connection priority (when USE_DB=True):**
1. Tries MongoDB Atlas (`MONGO_URI_ATLAS`)
2. Falls back to Local MongoDB (`MONGO_URI_LOCAL`)
3. Falls back to In-Memory on any connection error

**Worker ID format:** `GS-XXXXXX` — prefix "GS-" followed by 6 random uppercase alphanumeric characters.

---

### 7.4 Mock Data System

`app/utils/mock_generator.py` uses MD5 hash of the identifier as a deterministic random seed, so the same ID always returns the same profile.

**Hardcoded Immutable Profile (Primary Demo Account):**

| Field | Value |
|---|---|
| Phone / Swiggy ID | `7550080899` |
| Name | `Rider_899` |
| Worker ID | `GS-OVVSRL` |
| Zone | North |
| UPI ID | `7550080899@okaxis` |
| Bank | State Bank of India |
| Rating | 4.6 |
| Weekly Earnings | Rs.5,000 |

**Additional whitelisted IDs:** `SWG101`, `SWG102`, `SWG777`, `dinesh_`, `HACKER_123`

Any other identifier is accepted and generates a consistent seeded profile — same input always produces same output.

---

## 8. Frontend — Flutter Web and Mobile

### 8.1 App Entry and Navigation

`main.dart` always shows `OnboardingScreen` first. `hasOnboarded` is hardcoded to `false` for hackathon demo mode.

**User journey:**
```
OnboardingScreen -> RegistrationScreen (4 steps) -> MainWrapper (5-tab nav)
```

**MainWrapper** bottom navigation tabs:

| Tab | Index | Screen | Icon |
|---|---|---|---|
| Home | 0 | DemandScreen | home |
| Earnings | 1 | EarningsScreen | show_chart |
| Radar | 2 | RadarScreen | radar |
| Insurance | 3 | InsuranceScreen | shield |
| Profile | 4 | ProfileScreen | person |

**Elite Plan perk:** Bottom nav icons and accents turn gold (`#FACC15`) when tier is `elite` and policy status is `active` or `scheduled_cancel`.

---

### 8.2 Screen Inventory

| Screen | File | Description |
|---|---|---|
| Onboarding | onboarding_screen.dart | Splash + "GET STARTED" CTA, gradient hero background |
| Registration | registration_screen.dart | 4-step GigShield wizard — main registration flow |
| Main Wrapper | main_wrapper.dart | Bottom nav container, persists tab state |
| Demand | demand_screen.dart | Live demand heatmap, today earnings, surge zones |
| Earnings | earnings_screen.dart | Historical earnings analytics, weekly/monthly charts |
| Radar | radar_screen.dart | Weather radar, zone-level risk detection |
| Insurance | insurance_screen.dart | Insurance dashboard, policy status, auto-claim triggers |
| Profile | profile_screen.dart | Worker profile, KYC details, policy lifecycle management |
| History | history_screen.dart | Completed ride history list |
| Live Tracking | live_tracking_screen.dart | Real-time delivery tracking on map |
| Cancellation | cancellation_screen.dart | Multi-step policy cancellation flow |
| Claim Details | claim_details_screen.dart | Individual claim breakdown with amounts |
| Claim Processing | claim_processing_screen.dart | Auto-claim processing animation screen |
| Fraud Verification | fraud_verification_screen.dart | GPS and delivery activity fraud detection UI |
| Manual Claim | manual_claim_screen.dart | Manual claim submission form |
| Proof of Work | pow_verification_screen.dart | Work verification via delivery data |

---

### 8.3 Global Theme System

**app_theme.dart — Design Tokens:**

```
Colors:
  brandPrimary  = #FF6B35  (Orange — primary brand)
  background    = #0F172A  (Dark Navy — page background)
  surface       = #1E293B  (Card/panel background)
  border        = #334155  (Dividers and outlines)
  textPrimary   = #F1F5F9  (Headings)
  textSecondary = #94A3B8  (Subtext, labels)
  success       = #10B981  (Green — verified, active)
  warning       = #F59E0B  (Amber — pending, caution)
  error         = #EF4444  (Red — errors, danger)

Typography:
  AppTypography.h1         (Large headings)
  AppTypography.h2         (Section headings)
  AppTypography.h3         (Card titles)
  AppTypography.bodyLarge  (Primary body text)
  AppTypography.bodyMedium (Secondary body text)
  AppTypography.small      (Labels, captions)

Layout:
  AppStyles.borderRadius = 16.0
  AppStyles.softShadow   = [BoxShadow with low opacity black]
```

**registration_theme.dart:** Extends global theme with wizard-specific card borders, CTA button styles, and compact spacing for the registration flow.

---

## 9. GigShield Registration Flow (4-Step Wizard)

`RegistrationScreen` uses `PageView` with `NeverScrollableScrollPhysics`. Steps are programmatically navigated via `_pageController`.

```
Step 0        Step 1        Step 2        Step 3
Language  ->  Profile   ->  Tier      ->  UPI Activation
Selection     Verification  Selection     + Payment
```

### Step 0 — Language Selection

- Choose preferred language: English, Hindi, Marathi, Tamil
- Toggle location consent switch (required to enable CONTINUE button)
- All subsequent UI text is dynamically translated via `_t(key)` dictionary lookup

### Step 1 — Worker Identity and Profile

- Enter Swiggy ID or phone number
- Tap VERIFY -> `POST /api/worker/fetch` -> auto-fills: Name, Phone, Platform, Zone, Hours, Deliveries, Earnings
- Choose delivery platform (Swiggy / Zomato / Zepto / Dunzo)
- Choose working zone (North / South / East / West / Central)
- Adjust daily hours via slider (1 to 16 hours)
- Enter weekly deliveries and weekly earnings
- Enter UPI ID -> tap "TEST Rs.1" -> 2-second simulated verification -> `_isUpiVerified = true`
- **Requires:** Identity verified AND UPI verified to advance to next step

### Step 2 — Tier Selection

Three plan cards displayed side by side with tap selection:

| Tier | Price | Coverage |
|---|---|---|
| Lite | Rs.49/week | Heavy rain (IMD Level 3+) |
| Smart (AI recommended) | Rs.68/week | Rain + extreme heat + AQI > 300 |
| Elite | Rs.99/week | All Smart triggers + priority processing |

- AI recommendation badge shown: "AI recommends Smart Tier based on your zone weather forecast"
- Pressing CONTINUE TO TERMS shows bottom sheet
- Terms fetched from `GET /api/terms/current?language=<selected>`
- Worker must check "I agree" checkbox to continue

### Step 3 — One-Tap UPI Activation

- Shows policy summary: selected tier, weekly amount, active dates
- "ACTIVATE NOW" button calls `_initiatePayment()`:

```
1. POST /api/payment/create_order  ->  { order_id, amount, key_id }
2. Launch Razorpay Checkout:
     WEB:    Razorpay JS Object via dart:js
     MOBILE: razorpay_flutter SDK
3. User completes payment (UPI / card / netbanking)
4. Receive: { payment_id, order_id, signature }
5. POST /api/payment/verify  ->  HMAC-SHA256 check
6. POST /api/worker/register ->  create worker doc, policy_status=active
7. Save to SharedPreferences:
     has_onboarded = true
     selected_tier = "Smart" (or Lite/Elite)
     policy_status = "active"
     worker_id     = "GS-XXXXXX"
8. Navigate to MainWrapper
```

---

## 10. Razorpay Payment Integration

### Platform Differences

| Platform | Method | Notes |
|---|---|---|
| Web | dart:js binding to Razorpay JS | Requires `checkout.js` in `web/index.html` |
| Mobile | razorpay_flutter native SDK | `_razorpay.open(options)` |

### Razorpay JS Script (web/index.html)

```html
<script src="https://checkout.razorpay.com/v1/checkout.js"></script>
<script src="flutter_bootstrap.js" async></script>
```

### Web Payment Code (registration_screen.dart)

```dart
if (kIsWeb) {
  final rzp = js.JsObject(
    js.context['Razorpay'],
    [js.JsObject.jsify(jsOptions)]
  );
  rzp.callMethod('open');
} else {
  _razorpay.open(options);
}
```

### Payment Options Object

```dart
{
  'key': responseBody['key_id'],        // rzp_test_... or rzp_live_...
  'amount': responseBody['amount'],      // in paise
  'name': 'Figgy GigShield',
  'description': '$_selectedTier Tier Insurance',
  'order_id': responseBody['order_id'],
  'prefill': {
    'contact': _phoneController.text,
    'email': 'gigworker@figgy.com'
  },
  'theme': { 'color': '#0F172A' }
}
```

### Test vs Live Keys

| Environment | Key ID | Key Secret |
|---|---|---|
| Test | rzp_test_SWtNUFcQLg64E9 | z3B3qvi2e1s59LWRKAOw0If3 |
| Live | (generated on Razorpay dashboard) | (generated on Razorpay dashboard) |

> CAUTION: Test keys charge no real money. Replace with live keys before production deployment.

---

## 11. Insurance Policy Lifecycle

```
[Unregistered Worker]
         |
         | Pay + Register (Step 3 of wizard)
         v
     [active]  <-------------------------------------------+
         |                                                  |
         | User cancels from Profile screen                 |
         v                                                  |
 [scheduled_cancel]                                         |
         |                                                  |
         | End of policy week                               |
         v                                                  |
     [cancelled] ---------> User reactivates + pays --------+
```

**Policy status values (stored in SharedPreferences):**

| Value | Meaning | UI Effect |
|---|---|---|
| `active` | Coverage is fully live | Green badge, normal UI |
| `scheduled_cancel` | Will cancel at end of current week | Amber badge, gold Elite UI still shown |
| `cancelled` | No coverage active | Red badge, reactivate CTA shown |

---

## 12. Insurance Tiers and Pricing

| Tier | Weekly Premium | Trigger Conditions | Fixed Payout |
|---|---|---|---|
| Lite | Rs.49 | Heavy rain (IMD Level 3+) | Rs.300 |
| Smart | Rs.68 | Rain + extreme heat (>42 C) + AQI > 300 | Rs.500 |
| Elite | Rs.99 | All Smart triggers + priority claims processing | Rs.750 + surge bonus |

**Policy period:** 7 days. Auto-renews weekly unless cancelled before renewal.

**Claim process:** Fully automatic (zero-touch). When a parametric trigger is satisfied for the worker's registered zone, payout is processed within 24–48 hours directly to the linked UPI ID.

**Exclusions (not covered):**
- Health-related issues or medical expenses
- Accidents or vehicle damage
- Income loss due to personal reasons
- GPS spoofing (leads to immediate cancellation)

**Dispute resolution:** Laws of India, arbitration in Chennai.

---

## 13. Key Files Reference

| File Path | Purpose |
|---|---|
| `figgy_backend/.env` | Secret credentials — Razorpay keys, MongoDB URIs |
| `figgy_backend/config.py` | Loads `.env` and exposes Flask config class |
| `figgy_backend/run.py` | Flask dev server entry point |
| `figgy_backend/app/__init__.py` | App factory, CORS setup, blueprint registration |
| `figgy_backend/app/models.py` | Database handler singleton + PolicyTermsStore |
| `figgy_backend/app/routes/payment.py` | Razorpay create_order and verify endpoints |
| `figgy_backend/app/routes/worker.py` | Worker fetch, register, list, cancel |
| `figgy_backend/app/routes/terms.py` | T&C retrieval by language and version |
| `figgy_backend/app/utils/mock_generator.py` | Deterministic mock worker profiles |
| `Figgy-main/lib/main.dart` | Flutter entry — always shows OnboardingScreen |
| `Figgy-main/lib/screens/registration_screen.dart` | Full 4-step wizard + payment integration |
| `Figgy-main/lib/screens/main_wrapper.dart` | Bottom nav + individual tab Navigator keys |
| `Figgy-main/lib/theme/app_theme.dart` | Global design tokens (colors, typography, layout) |
| `Figgy-main/web/index.html` | Razorpay JS CDN script + Flutter Web bootstrap |
| `Figgy-main/pubspec.yaml` | Flutter package dependencies |
| `Figgy-main/lib/models/ride.dart` | Ride data model + globalCompletedRidesNotifier |

---

## 14. Known Limitations and TODOs

| # | Item | Priority |
|---|---|---|
| 1 | `razorpay_flutter` does not natively support web — workaround uses `dart:js` binding | Medium |
| 2 | UPI Rs.1 test drop is simulated (2-second fake delay), no real penny dropped in demo | High |
| 3 | MongoDB disabled by default (USE_DB=False) — all data is lost when Flask server restarts | High |
| 4 | No JWT or authentication layer — all API endpoints are publicly accessible | High |
| 5 | CORS is fully open (origins=*) — must restrict to specific domains before production | High |
| 6 | `cancel_policy` endpoint only updates the in-memory object reference, not a real DB record | Medium |
| 7 | Auto-claim weather trigger detection system is not implemented (mock/UI only) | Medium |
| 8 | `hmac.new()` call in payment.py is deprecated in newer Python versions | Low |
| 9 | `main.dart` hardcodes `hasOnboarded = false` — always forces onboarding screen | Low |
| 10 | Marathi and Tamil T&C sections are incomplete in `models.py` PolicyTermsStore | Low |

---

*Figgy GigShield — Full Technical Documentation — March 2026 Hackathon Build*
