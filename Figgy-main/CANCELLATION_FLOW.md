# GigShield Policy Cancellation & Management Flow

This document formalizes the high-trust cancellation, pause, and reactivation logic implemented in Figgy.

## Cancellation Strategy: "Protected Until End of Cycle"

To maintain trust and ensure workers aren't left vulnerable mid-week, GigShield does not offer immediate termination or refunds. Instead:

1.  **Scheduled Status**: When a user cancels, the status changes to `scheduled_cancel` (UI shows **"CLOSING"**).
2.  **Continued Coverage**: The worker remains fully protected until the end of the current weekly cycle (next Sunday).
3.  **No New Charges**: Auto-renewal is disabled, and no further premium will be deducted.
4.  **Re-activation**: Users can cancel the cancellation or re-activate their policy at any time, which takes them to the Tier Selection screen to confirm their choice.

## Technical Implementation

### State Management
- `policy_status` in `SharedPreferences` handles the three states: `active`, `scheduled_cancel`, and `inactive`.
- `MainWrapper` refreshes the global state to ensure bottom navigation and premium badges reflect the correct status.

### UI Components
- **CancellationScreen**: A 4-step wizard collecting feedback and providing transparent warnings about the "No Refund" policy and remaining coverage dates.
- **ProfileScreen**: Features a dynamic `InsuranceManagementCard` that adapts its layout and actions based on the current policy state.
- **Theme Support**: Uses `AppColors.warningLight` and `AppColors.brandOrange` for high-visibility informational cards.

## Verification Checklist

- [ ] Cancellation button triggers the 4-step flow.
- [ ] Cancellation reason is collected (optional but encouraged).
- [ ] Warning card correctly displays the next Sunday as the end-of-coverage date.
- [ ] After cancellation, Profile Screen shows "CLOSING" status with a timer icon.
- [ ] Re-activate button navigate back to Tier Selection (Step 3) of Registration.
