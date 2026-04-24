# GigShield Policy Lifecycle: Documentation

This document outlines the end-to-end flow for a gig worker within the Figgy application, covering registration, policy selection, activation, and deactivation.

---

## 🟢 Phase 1: Registration (Onboarding)
The registration process is designed to be inclusive and data-driven, ensuring every worker is correctly identified and their risk profile is established.

### 1. Language & Localization
Workers can choose their preferred language (English, Hindi, Marathi, Tamil, etc.) to ensure complete transparency of insurance terms.
*   **Action**: Select Language → Enable Location Access.
*   **Why**: Location access is critical for parametric insurance to track local weather risks (Rain, AQI, Heat).

### 2. Identity & Profile Verification
Workers link their delivery platform ID (e.g., Swiggy/Zomato) and verify their identity.
*   **Input**: Swiggy ID, Phone Number, Full Name.
*   **Verification**: The system verifies the worker's active status and historical delivery data.

### 3. Financial Setup (UPI)
To enable instant parametric payouts, workers must link their UPI ID.
*   **Action**: Enter UPI ID → Instant Verification (₹1 Test Transaction).

---

## 🔵 Phase 2: Choosing a Policy (Tier Selection)
Figgy provides three distinct tiers tailored to different risk appetites and working hours.

| Tier | Coverage Scope | Recommended For |
| :--- | :--- | :--- |
| **Starter** | Basic Rain & Heat protection. | Part-time workers (< 4 hrs/day). |
| **Smart** | **AI-Recommended**. Balanced coverage for all weather events. | Full-time urban workers (8 hrs/day). |
| **Elite** | Maximum protection + highest payout multipliers. | 10+ hrs/day workers in high-risk zones. |

*   **AI Recommendation**: The app analyzes the next 7-day weather forecast in the worker's primary zone to suggest the most cost-effective tier.

---

## ⚡ Phase 3: Activating Coverage
Activation is the final step where the policy becomes "Live."

### 1. Dynamic Premium Breakdown
The worker views an AI-calculated breakdown of their weekly commitment based on:
*   Real-time zone risks (e.g., predicted heavy rain in North Delhi).
*   Historical platform reliability.

### 2. One-Tap Activation
*   **Step 1**: Review the high-end terms & conditions (Simplified TL;DR provided).
*   **Step 2**: Tap **"ACTIVATE NOW"**.
*   **Result**: The policy is linked to the worker's profile, and coverage starts immediately for the current week.

---

## 🔴 Phase 4: Deactivation & Management
Workers have full control over their lifecycle through the **Insurance Management Module** in their Profile.

### 1. Active Policy Overview
Workers can see their active status, coverage period (e.g., Mar 28 - Apr 04), and auto-renewal settings.

### 2. Cancellation
If a worker wishes to pause protection, they can use the "Lifecycle Management" card.
*   **Action**: Profile → Section: "Protection Under Management" → **CANCEL ACTIVE POLICY**.
*   **Feedback**: The app confirms the cancellation and updates the local status to `inactive`. 
*   **Flexibility**: The user can **RE-ACTIVATE** at any time through the same interface.

---

## 📊 Summary of Tech Stack Integration
*   **Backend**: Flask-based API for T&C fetching and premium calculation.
*   **Frontend**: Flutter `RegistrationScreen` (wizard-style) and `ProfileScreen` (management-style).
*   **State Management**: `SharedPreferences` for lifecycle persistence and `ValueListenableBuilder` for real-time history syncing.
