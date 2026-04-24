# UI Screen Documentation (Flutter Frontend)

The Flutter frontend maintains an ultra-premium, modern, and engaging user interface specifically optimized for delivery workers working outdoors (dark mode first).

## Core Navigation Architecture
The primary wrapper (`main_wrapper.dart`) uses an animated Bottom Navigation Bar connecting the main pillar screens:

### 1. Radar Screen
- Acts as the operational center.
- Displays live, location-aware weather and disruption alerts using a dynamic Glassmorphism interface.
- Includes a map or visual representation of the worker's operational zone to showcase active environmental risks.

### 2. Earnings & Home Screen
- High-level overview of daily metrics.
- Tracks `Deliveries done`, `Income generated`, and dynamically predicts if a worker is lagging due to recorded disruptions.

### 3. Insurance Dashboard (`insurance_screen.dart`)
- **Active Policy Card**: Shows the current subscribed Tier (Lite, Smart, Elite), validity, and daily premium breakdown.
- **Payout History**: A paginated list of past claims, status markers, and disbursed amounts fetched via `/api/claim/list/<id>`.
- Provides the floating entry point to file a **Manual Claim**.

### 4. Profile Screen
- Manages user details, linked UPI ID for payouts, and application settings.

## Secondary / Modal Screens

### 1. Manual Claim Submission (`manual_claim_screen.dart`)
- A wizard-based form allowing workers to report localized disruptions (e.g., specific traffic blockades or localized street flooding) that weren't captured by the automated weather auto-trigger.
- Requires them to submit a timeline, estimated lost income, and optional proof URLs.

### 2. Claim Processing Screen (`claim_processing_screen.dart`)
- The emotional centerpiece of the claim experience.
- Shown immediately after a claim triggers or is submitted.
- Prevents user navigation while polling the backend `/api/claim/status` every 5 seconds.
- Transitions smoothly via animations through `Receiving` → `Verifying` → `Calculating`.
- Hands off to terminal states: **Approved**, **Rejected**, **Under Review**, or **Payout Failed**.

### 3. Claim Details / Receipt Screen (`claim_details_screen.dart`)
- A highly polished receipt view outlining the final decision matrix.
- Breaks down the income calculation, surge bonuses applied, and the final payout reference (RRN).
- Features a massive bold "PAID" validation checkmark to establish trust.

### 4. Policy Registration Wizard (`registration_screen.dart`)
- A multi-step onboarding carousel that guides new workers through selecting a tier, linking their UPI ID, and paying their first premium.
