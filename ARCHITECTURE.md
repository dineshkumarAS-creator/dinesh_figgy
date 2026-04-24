# Figgy GigShield — Architecture & Documentation

This document describes the **Figgy** system end-to-end: the Flutter worker app (`Figgy-main`), the Flask backend (`figgy_backend`), how they connect, and how the codebase is organized.

---

## 1. What Figgy Is

**Figgy GigShield** is a parametric income-protection product for gig workers: registration and premiums on the app, weather-based (and related) triggers on the backend, claim verification, and payouts (Razorpay on the client for collection; backend utilities for disbursement design).

---

## 2. Repository Layout

```
Figgybackend-main/                 # Monorepo root (this folder)
├── ARCHITECTURE.md                 # This file — system overview
├── docs/
│   ├── business_logic_architecture.md   # Rules, fraud, payouts (backend)
│   └── claim_management.md             # Claim lifecycle & orchestrator
│
├── figgy_backend/                  # Python Flask API + schedulers
│   ├── run.py                      # Entry: Flask + BackgroundScheduler (weather triggers)
│   ├── config.py                   # Config object / env
│   ├── requirements.txt
│   ├── README_BACKEND.md           # Quick run & sample endpoints
│   ├── app/
│   │   ├── __init__.py             # create_app(), blueprints, CORS, scheduler init
│   │   ├── models.py               # DB / in-memory helpers
│   │   ├── config/                 # Thresholds and app config fragments
│   │   ├── routes/                 # API blueprints (worker, claims, weather, …)
│   │   └── utils/                  # weather, fraud, calculations, claim_processor, …
│   ├── demo/                       # Scripted demo (e.g. Ravi scenario)
│   ├── scripts/                    # Training / test helpers
│   └── tests/
│
└── Figgy-main/                     # Flutter app (package name: figgy_app)
    ├── lib/
    ├── pubspec.yaml
    ├── README.md
    └── UX_IMPLEMENTATION.md        # UX tokens and patterns
```

---

## 3. Flutter App (`Figgy-main`)

### 3.1 Entry & global navigation

| Piece | Path | Role |
|--------|------|------|
| Entry | `lib/main.dart` | `WidgetsFlutterBinding`, `SharedPreferences`, chooses first screen: `RegistrationScreen`, `MainWrapper`, or `OnboardingScreen`. Web can force registration via URL flags. |
| Root `MaterialApp` | `lib/main.dart` → `MyApp` | `navigatorKey: NavigationService.navigatorKey`, `onGenerateRoute: AppRoutes.generateRoute`. |
| Main shell | `lib/app/main_wrapper.dart` | **5 tabs**: Home (demand), Shield timeline, Claims, Radar, Profile. Each tab has its own `Navigator` + `GlobalKey`. |
| Tab switching from deep UI | `lib/core/navigation/main_tab_scope.dart` | `MainTabScope` + `context.goToMainTab(index)` so feature code does not import `main_wrapper.dart` (avoids circular imports). |

**Tab indices** (keep in sync with `MainWrapper` and any `setIndex` / `goToMainTab` calls):

| Index | Label | Widget |
|-------|--------|--------|
| 0 | Home | `DemandScreen` |
| 1 | Shield | `ShieldTimelineTabScreen` |
| 2 | Claims | `ClaimsTabScreen` |
| 3 | Radar | `RadarScreen` |
| 4 | Profile | `ProfileScreen` |

Default post-onboarding landing: **Shield** (`initialIndex: 1`).

### 3.2 Folder structure (feature-first + legacy)

```
lib/
├── main.dart
├── routes.dart                    # Named routes: parametric, pow, claim processing, …
├── app/
│   └── main_wrapper.dart
├── core/
│   └── navigation/
│       └── main_tab_scope.dart
├── features/                      # Vertical slices
│   ├── demand/
│   │   └── demand_screen.dart     # Home / demand map
│   ├── radar/
│   │   └── radar_screen.dart
│   ├── profile/
│   │   └── profile_screen.dart
│   └── shield/                    # Shield + claims UX (timeline, demo sim, filing flow)
│       ├── shield_theme.dart      # ShieldColors (separate from global AppColors)
│       ├── shield_timeline_tab_screen.dart
│       ├── claims_tab_screen.dart
│       ├── core/
│       │   ├── simulation_controller.dart
│       │   └── animation_constants.dart
│       ├── screens/
│       │   ├── my_shield_screen.dart
│       │   ├── claims_screen.dart
│       │   ├── file_claim_screen.dart
│       │   ├── add_proof_screen.dart
│       │   └── review_claim_screen.dart
│       └── widgets/
│           ├── timeline_feed.dart
│           ├── alert_cards.dart
│           └── …
├── screens/                       # Shared flows not yet moved into features/
│   ├── onboarding_screen.dart
│   ├── registration_screen.dart
│   ├── claim_processing_screen.dart
│   ├── claim_details_screen.dart
│   ├── parametric_screen.dart
│   ├── wallet_screen.dart
│   └── …
├── services/
│   ├── api_service.dart           # HTTP to Flask (see §5)
│   ├── navigation_service.dart
│   ├── notification_service.dart
│   ├── wallet_service.dart
│   └── razorpay_*.dart
├── theme/
│   ├── app_theme.dart             # AppColors, typography (Outfit via Google Fonts)
│   └── registration_theme.dart
├── models/
│   ├── claim_model.dart
│   └── ride.dart
└── widgets/
    └── receipt_row_widget.dart
```

**Design rule:** New product areas should live under `lib/features/<name>/` with local `screens/`, `widgets/`, and optional `core/`. Cross-app pieces stay in `theme/`, `models/`, `services/`, `widgets/`.

### 3.3 Routing (`lib/routes.dart`)

`MaterialApp.onGenerateRoute` handles paths such as:

- `/parametric` → `ParametricScreen`
- `/pow-token`, `/pow-verify` → proof-of-work flows
- `/claim-processing`, `/claim-details` → claim UI with typed arguments

These are used for flows **above** the bottom tab bar (global navigator).

### 3.4 Styling

- **Global:** `lib/theme/app_theme.dart` — brand orange, neutrals, `AppTypography`.
- **Shield-only:** `lib/features/shield/shield_theme.dart` — `ShieldColors` to avoid clashing with `AppColors`.

### 3.5 HTTP client

- **`ApiService`** (`lib/services/api_service.dart`): single place for backend calls.
- **Base URL:** `--dart-define=API_BASE_URL=...` or defaults: `http://localhost:5000` (web), `http://10.0.2.2:5000` (Android emulator → host).

---

## 4. Backend (`figgy_backend`)

### 4.1 Runtime model

Two complementary scheduling mechanisms exist (see `run.py` header comments):

1. **`create_app()`** (`app/__init__.py`): registers Flask blueprints, CORS, Mongo index setup, **Flask-APScheduler** via `init_scheduler(app)`.
2. **`run.py` as `__main__`**: starts a **standalone `BackgroundScheduler`** that runs `check_weather_and_trigger()` on an interval (default 15 minutes) inside `app.app_context()`.

`run.py` also implements **auto-claim creation** (`create_auto_claim`) and **verify/payout** (`verify_and_payout`) for parametric triggers. Use `use_reloader=False` when running Flask alongside APScheduler to avoid double jobs.

### 4.2 Flask application factory

`app/__init__.py` → `create_app()`:

- Loads `config.Config`
- Registers blueprints: `worker`, `terms`, `payment`, `payout`, `claims`, `weather`, `demo`, `telemetry`, `demand`, `admin` (under `/admin`)
- `/health` → `{"status": "ok"}`
- Initializes scheduler and Mongo claim indexes when `USE_DB` is true

### 4.3 Main domains (blueprints)

| Area | Module | Typical responsibility |
|------|--------|-------------------------|
| Workers | `app/routes/worker.py` | Registration, fetch, profile fields |
| Claims | `app/routes/claims.py` | Manual/auto claim, status polling |
| Weather | `app/routes/weather.py` | Zone weather for app/radar |
| Demand | `app/routes/demand.py` | Demand / zone data for map |
| Payment / Payout | `payment.py`, `payout.py` | Razorpay-related flows |
| Demo | `demo.py` | Demo mode behaviors |
| Admin | `admin_bp` | Admin dashboard (prefixed) |
| Telemetry | `telemetry_routes.py` | Worker telemetry for fraud/PoW context |

### 4.4 Business logic modules (`app/utils/`)

| Module | Role |
|--------|------|
| `weather.py` / `weather_client.py` | Zone weather and trigger interpretation |
| `scheduler.py` | Flask-tied scheduled jobs |
| `claim_processor.py` | Verify-and-payout pipeline (orchestrator steps) |
| `fraud.py` | Rule-based risk scoring |
| `calculations.py` | Expected vs actual earnings, caps, surge |
| `payout.py` | Payout assembly / Razorpay integration helpers |
| `mock_generator.py` | Deterministic mocks (e.g. by Swiggy ID) |

**Deeper narrative:** `docs/business_logic_architecture.md` and `docs/claim_management.md`.

### 4.5 Data

- **MongoDB** when configured (`MONGO_URI`, `USE_DB`); **in-memory** fallbacks for development (see `app/models.py` patterns).
- Claims: unique index on `claim_id`, index on `worker_id` (see `_ensure_claim_indexes`).

### 4.6 Running the backend

```bash
cd figgy_backend
pip install -r requirements.txt
# MongoDB: mongodb://localhost:27017 or MONGO_URI
python run.py
```

Default host/port: `0.0.0.0:5000` (see `run.py`). Demo scripts: `demo/run_demo.py`, `demo/reset_demo.py`. Details: `README_BACKEND.md`.

---

## 5. Frontend ↔ Backend Integration

- The app **does not** embed business rules for payout; it **calls APIs** (`ApiService`) and **polls** claim status where documented in `docs/claim_management.md`.
- **Registration / worker** endpoints align with `worker` blueprint; **claims** with `claims` blueprint; **radar/demand** with `weather` / `demand` as implemented.
- **CORS** is open for dev (`origins: *`); tighten for production.

---

## 6. Claim Lifecycle (summary)

1. **Auto-trigger:** Weather job detects threshold breach per zone → eligible workers → auto claim in `verifying` → fraud + payout path.
2. **Manual:** Worker submits via API → `under_review` (or as implemented) → same pipeline concepts.
3. **Orchestrator:** Steps in `claim_processor.py` (load, telemetry, notify, fraud, branch to manual review, quantify loss, payout, finalize). See `docs/claim_management.md` for states: `paid`, `rejected`, `manual_review`, `payment_failed`, etc.

---

## 7. Configuration Highlights

### Backend (`figgy_backend/config.py` + env)

- Mongo URI, `USE_DB`, demo flags, scheduler interval, Razorpay keys as applicable.

### Flutter

- `API_BASE_URL` via `--dart-define`
- `SharedPreferences`: onboarding, tier, policy status, nav index, worker prefs used across `MainWrapper` and registration.

---

## 8. Testing & tooling

- **Flutter:** `test/widget_test.dart` (smoke).
- **Backend:** `figgy_backend/tests/` (e.g. claim flow, scenarios); `test_orchestrator.py` at backend root for orchestration checks.

---

## 9. Known gaps / follow-ups (non-exhaustive)

Analyzer may report issues unrelated to architecture, for example:

- `share_plus` / `claim_details_screen` if package resolution fails in a given environment.
- `notification_service` references to `navigatorKey` must match `main.dart` export pattern.
- Web-only Razorpay helper vs VM compilation.

Treat these as **integration hygiene**, not as core architecture changes.

---

## 10. Related documentation index

| Document | Content |
|----------|---------|
| `docs/business_logic_architecture.md` | Schedulers, fraud, calculations, payments |
| `docs/claim_management.md` | Init paths, 10-step pipeline, polling, terminal states |
| `figgy_backend/README_BACKEND.md` | Run instructions, sample POST bodies, demo mode |
| `Figgy-main/README.md` | Flutter project readme |
| `Figgy-main/UX_IMPLEMENTATION.md` | Design tokens, registration wizard, Shield feature UX |

---

## 11. Quick mental model

```text
┌─────────────────────────────────────────────────────────────────┐
│                     Flutter (figgy_app)                          │
│  Onboarding / Registration → MainWrapper (5 tabs)                │
│  + global routes (parametric, claim details, PoW, …)             │
│  ApiService ──────────────── HTTP ───────────────► Flask API      │
└─────────────────────────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                     figgy_backend (Flask)                        │
│  Blueprints: worker, claims, weather, demand, payment, …         │
│  Utils: fraud, calculations, claim_processor, weather             │
│  Schedulers: periodic weather → auto claims → verify/payout      │
└─────────────────────────────────────────────────────────────────┘
```

This file is the **single map** of the repo; domain depth lives in `docs/` and the smaller READMEs cited above.
