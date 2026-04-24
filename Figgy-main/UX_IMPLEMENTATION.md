# Figgy UX Implementation Guide

This document outlines the design philosophy, visual language, and interactive patterns implemented in the Figgy application. The goal is to provide a premium, accessible, and high-trust experience for gig workers.

---

## 1. Design Philosophy

Figgy’s UX is built on three core pillars:
- **High Trust (MNC-Style):** Using professional typography, subtle shadows, and clear status indicators to feel reliable and "bank-grade."
- **Accessibility-First:** Multilingual support is not an afterthought; it is integrated into the core navigation with "Translation Flip" labels.
- **Micro-Interactions:** Using layout transitions and tactile feedback (visual) to guide workers through complex insurance processes.

---

## 2. Visual Identity & Tokens

Defined in `lib/theme/app_theme.dart`.

### Color Palette
- **Brand Primary:** `#FF6A2A` (Safety Orange) — used for primary actions and brand presence.
- **Brand Gradient:** From `#8A0F3C` to `#FF6A2A`. Used for hero sections to create a premium "Glassmorphism" effect.
- **Success:** `#10B981` (Emerald) — for verified states and active protection.
- **Neutral:** `#F9FAFB` (Background) and `#FFFFFF` (Surface).

### Typography (Outfit)
We use the **Outfit** Google Font for its modern, geometric yet friendly feel.
- **H1 (26px):** Used for main headers and hero titles.
- **H3 (18px):** Used for card titles and section headers.
- **Body (14px/16px):** Optimized for readability with 1.4x line height.
- **Small (12px):** Used for uppercase labels and metadata.

### Styling & Elevation
- **Soft Shadows:** `0.04` opacity black shadow for standard cards to maintain a clean layout.
- **Premium Shadows:** `0.12` opacity brand-tinted shadow for active or highlighted components.
- **Border Radius:** `12px` for general containers and `16px` for major cards.

---

## 3. Core UX Components

### A. 3-Step Worker Registration Wizard
Located in `lib/screens/registration_screen.dart`.
1.  **Stage 1: Language & Consent:** Immediate personalization. The app adapts its voice before asking for data.
2.  **Stage 2: Verified Identity:** A dual-purpose screen that imports existing data (Swiggy/Zomato) and links UPI via a "₹1 Test Drop" to establish trust instantly.
3.  **Stage 3: AI-Optimized Plan Selection:** Presents insurance tiers with a "Recommended" banner based on the worker's operating zone and historical weather patterns.

### B. Translation Flip Labels (`TranslationFlipLabel`)
A custom interaction pattern that allows workers to tap any label (e.g., "Full Name") to temporarily flip it between their selected language and English. This aids in learning and provides confidence during technical data entry.

### C. Shield & claims (Figgy Shield)
Located under `lib/features/shield/` (timeline tab, claims list, and manual claim flow).
- **Shield timeline:** Disruption demo, ride timeline, and income summary cards.
- **Claims:** Expandable claim cards with verification steps and payout states.
- **Manual filing:** `FileClaimScreen` → proof → review when auto-detection is unavailable.

---

## 4. Interaction Patterns

| Pattern | Implementation | Purpose |
| :--- | :--- | :--- |
| **Progressive Disclosure** | `PageView` in Registration | Prevents cognitive overload by showing only relevant fields. |
| **Tactile Verification** | Animated Loading States | Shows the system is "working" during Swiggy ID or UPI checks. |
| **Contextual Banners** | AI Recommendation Strip | Guide users toward the "Smart" choice without removing autonomy. |
| **Soft UI Borders** | 1px Solid Gray (`#E5E7EB`) | Defines boundaries without the "harshness" of old-school shadows. |

---

## 5. Next Steps for UX Polish
- [ ] **Lottie Animations:** Add subtle weather animations (rain/sun) to the tier selection.
- [ ] **Haptic Feedback:** Integrate vibration for "Verified" and "Success" states.
- [ ] **Dark Mode:** Implement a high-contrast dark theme for night-shift workers.
