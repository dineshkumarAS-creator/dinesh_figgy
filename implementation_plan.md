# Registration Flow Upgrade Plan (GigShield Standard)

Based on the GigShield principles, the current registration flow in the app is functionally working as a data-entry form, but it lacks the progressive disclosure, KYC verification, and dynamic premium checkout steps required for a seamless, mobile-first gig worker onboarding experience.

Here is an analysis of what we can improve and how we plan to implement it:

## Areas for Improvement

1. **UX Structure (Progressive Disclosure)**
   * **Current**: A single, long scrolling form containing all fields (Phone, Platform, Zone, Hours, Earnings).
   * **Improvement**: Convert to a **multi-step wizard** (e.g., a `PageView` or bottom-sheet flow) to avoid overwhelming the user. Ask only what's needed per step.
2. **Missing KYC & Document Upload**
   * **Current**: Relies purely on the mock Swiggy ID fetch; no physical ID validation or UPI linking UI.
   * **Improvement**: Add a dedicated "Quick KYC" step. Include UI placeholders for **Aadhaar/PAN photo upload** (mock OCR) and **UPI ID** entry for claim payouts.
3. **Tiered Policy Selection & Payment**
   * **Current**: "Register Now" immediately dumps the user into the main dashboard.
   * **Improvement**: Implement a highly transparent **Tiered Policy Preview Step** before finishing. This screen should display 3 Tier options (Lite, Smart, Pro) based on the user's risk profiling. Let the AI dynamically price the "Smart" tier and pre-select it as the recommended default.

---

## Proposed Changes

We will refactor [registration_screen.dart](file:///c:/Users/sridh/Downloads/Figgy-main%20%281%29/Figgy-main/lib/screens/registration_screen.dart) to support a stateful, multi-page layout.

### [lib/screens/registration_screen.dart](file:///c:/Users/sridh/Downloads/Figgy-main%20%281%29/Figgy-main/lib/screens/registration_screen.dart)
* **Step 1: Phone & Profile Verification (The Hook)**
  * Retain the existing Swiggy ID/Phone verification API fetch block, making it the sole focus of the first view.
  * Add language selection toggles.
* **Step 2: Risk Profiling (The Setup)**
  * Display the Platform dropdown, Zone map/dropdown, and Daily Hours slider. 
  * Add the optional *Vehicle Type* selector (Bike/Cycle/EV).
* **Step 3: KYC & Payouts (The Trust)**
  * **[NEW UI]** "Upload ID" button (Aadhaar/PAN) with a mock success checkmark.
  * **[NEW UI]** UPI ID text field with a "Verify & Link" button (mocking a ₹1 test drop).
* **Step 4: Tier Selection & Activation (The Checkout)**
  * **[NEW UI]** Visually distinct cards for the 3 Tiers:
    * **Lite (₹49/week)**: Basic protection (Rain only).
    * **Smart (₹60–₹80/week)**: Comprehensive (Rain, Heat, Pollution). *[AI Recommended Default]*
    * **Pro (₹99/week)**: Premium protection (Lower thresholds, higher payouts).
  * **[NEW UI]** Simple dynamic explanation text: "Smart ₹68 this week – low rain risk in your zone!"
  * Replace the basic "Register Now" button with a one-tap CTA: "Pay ₹[SelectedAmount] & Activate via UPI".

## Verification Plan

### Automated Tests
* Will rely on hot-reloading Flutter session to verify UI state management.

### Manual Verification
1. Open the app and navigate to the Registration full-screen flow.
2. Step through the wizard sequentially (Profile -> Profiling -> KYC).
3. On Step 4, verify the 3 tiers (Lite, Smart, Pro) render correctly. 
4. Check that the **Smart** tier is pre-selected by default as the AI recommendation.
5. Tap between the tiers to ensure the final CTA button dynamically updates its layout and price (e.g., "Pay ₹49 & Activate").
