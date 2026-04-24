# Figgy Profile UI/UX Design

The Profile Screen in Figgy serves as the central hub for worker performance, financial health, and insurance management. It is designed to be highly informative while maintaining a clean, professional aesthetic (MNC-style).

---

## 1. Visual Hierarchy & Information Architecture

The screen follows a top-down priority layout:
- **Primary Metrics:** Today's performance (Earnings, Hours, Deliveries).
- **Recent Activity:** Quick view of the last few deliveries.
- **Shortcuts:** "Quick Action" cards for frequent navigation.
- **Active Protection:** Current insurance status and management tools.
- **Value-Add:** Personalized government schemes and "Smart Saver" plan suggestions based on earning history.

---

## 2. Core UI Components

### A. Performance Metrics Card
- **Visuals:** Uses subtle background tints (Green for money, Blue for time, Orange for volume) with distinct iconography.
- **UX Goal:** Provide instant feedback on the day's progress without requiring navigation.

### B. "Manage Insurance" Module
- **States:** 
  - **Active:** Displays "Elite/Smart/Lite Plan Protection" with a prominent green badge. Provides a "Cancel Policy" action.
  - **Inactive/Cancelled:** Displays a gray status with a "Re-Activate Protection" primary button to drive conversion.
- **Interaction:** Uses a confirmation dialog for cancellation to prevent accidental loss of coverage.

### C. Smart Recommendations (Income-Aware)
- **Income Profile Card:** Transparently shows the worker's earnings category (e.g., "Medium Income") and suggested budget.
- **Government Schemes:** Tailored suggestions like *Pradhan Mantri Jan Dhan Yojana* are presented with distinct "Benefit Tags" (e.g., "BEST FOR SAVINGS").
- **UX Goal:** Position Figgy as a partner in the worker's long-term financial security, not just a service provider.

---

## 3. Design Patterns & Colors

| Element | Specification | Purpose |
| :--- | :--- | :--- |
| **Section Headers** | Bold H3 with "LIVE" badge indicator | Creates a sense of real-time data accuracy (HSTS). |
| **Quick Action Cards** | Grid-based, high-contrast icons | Large tap targets for on-the-go navigation while riding. |
| **Insight Cards** | Toned backgrounds (Red/Orange) | Used for "Savings Insights" or "Warnings" to catch the eye safely. |
| **Gradient Banners** | Demand Map Preview | Visual break in the scroll to highlight high-earning opportunities. |

---

## 4. Technical Logic (UX under the hood)
- **Instant Refresh:** When a policy is cancelled, the app uses `MainWrapper.of(context)?.refreshState()` to update the global theme and navigation bar color instantly without a page reload.
- **Deterministic Mocking:** Data is fetched based on the `swiggy_id` or `phone` to ensure a consistent experience across sessions.
- **Scroll Optimization:** `SingleChildScrollView` ensures that the rich content is accessible on smaller smartphone screens commonly used by gig partners.
