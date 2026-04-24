# Profile Screen with Wallet: End-to-End Design Guide

**For Figgy App — Gig Worker Protection Platform**  
*Generated: April 24, 2026*

---

## Table of Contents

1. [Information Architecture](#1-information-architecture)
2. [Wallet Integration Flow](#2-wallet-integration-flow)
3. [Detailed Wallet Features](#3-detailed-wallet-features)
4. [Payout Settings](#4-payout-settings-enhanced)
5. [Full Wallet Screen](#5-full-wallet-screen-dedicated-tab)
6. [Backend Integration](#6-backend-integration-requirements)
7. [Key UX Interactions](#7-key-ux-interactions)
8. [Design Tokens](#8-design-tokens-implementation)
9. [Wallet Insights Dashboard](#9-wallet-insights-dashboard-optional-enhancement)
10. [Implementation Roadmap](#10-progressive-implementation-roadmap)
11. [Key Benefits](#11-key-benefits-for-gig-workers)

---

## 1. INFORMATION ARCHITECTURE

### Profile Screen Hierarchy

```
Profile Screen (Primary)
├── Sticky Header (Performance Summary)
├── Quick Metrics (3 cards)
│   ├── Today's Earnings
│   ├── Active Hours
│   └── Delivery Count
├── ──────────────────────────
├── WALLET SECTION (NEW)
│   ├── Balance Card (Hero)
│   ├── Quick Actions
│   │   ├── Request Payout
│   │   ├── View Transactions
│   │   └── Add Payment Method
│   └── Recent Transactions (Mini Feed)
├── ──────────────────────────
├── Payout Settings
│   ├── UPI ID Management
│   ├── Payment Methods
│   └── Payout Schedule
├── ──────────────────────────
├── Insurance Management
│   ├── Policy Status
│   ├── Coverage Details
│   └── Claims Summary
└── Other Sections
    ├── Recent Deliveries
    ├── Schemes & Benefits
    └── Profile Settings
```

---

## 2. WALLET INTEGRATION FLOW

### Phase 1: Unified Balance View (Hero Section)

**Visual Layout:**
```
┌─────────────────────────────────┐
│  💰 AVAILABLE BALANCE           │
│     ₹520                        │
│  Last payout: 2 hrs ago         │
│                                 │
│  [Request Payout] [Details ▶]   │
└─────────────────────────────────┘
```

**Key Details:**

- **Design**: Gradient background (Orange → Deep Blue)
- **Balance Updates**: Real-time sync with backend
- **Status Indicators**:
  - 🟢 **"Ready to Payout"** — Balance > ₹100
  - 🟡 **"Low Balance"** — Balance < ₹100
  - 🔴 **"Pending Verification"** — UPI unverified

**Typography:**
- Amount: `Outfit 32px, W900, tracking -0.5`
- Subtitle: `Outfit 13px, W500, color textSecondary`
- Last Updated: `Outfit 11px, W600, color textMuted, italic`

**Interactions:**
- Tap anywhere → Opens full Wallet screen
- Pull/Refresh icon → Reloads balance in real-time
- Error state → Shows red banner with retry option

---

### Phase 2: Request Payout Modal

**Default State:**
```
REQUEST PAYOUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Current Balance: ₹520

Amount Requested: [____] ₹
(Auto-placeholder: Maximum available)

⚙️ Recommended Maximum: ₹500
(75% of available balance)

Payout Method Section:
  🏦 worker@upi (verified) ✅
  └─ Last used: 2 hrs ago
  
Alternative Methods:
  [+ Add New UPI]
  [+ Add Bank Account]

Transfer Speed:
  ⚡ Instant (0s-30s)     ← Default
  🕐 Standard (1-2 hrs)
  💤 Scheduled (Next day)

≈ Processing Fee: ₹0
≈ Final Amount: ₹520

[CONFIRM PAYOUT]    [CANCEL]
```

**Modal Behavior:**
- Opens via bottom sheet
- Amount field: Real-time validation (min ₹100, max current balance)
- Speed selection: Radio buttons with fee display
- Confirmation: Haptic feedback + success toast

**Success State:**
```
✅ PAYOUT REQUESTED

Payout ID: #POT-2024-03-24-1145
Amount: ₹520
Destination: worker@upi
Status: Processing (2-5 seconds)

[View Transaction] [Done]
```

---

### Phase 3: Transaction Timeline

**Visual Structure:**
```
Recent Activity (Last 7 days)

TODAY
│
├─ 2:45 PM  ✅ Payout Sent
│           ₹250 → worker@upi
│           Instant Transfer
│           Status: Success in 12s
│
├─ 10:30 AM ✅ Earnings Credited
│           +₹45 delivery bonus
│           Delivery #D-12567
│
YESTERDAY
│
├─ 8:50 PM  ✅ Payout Completed
│           ₹300 → worker@upi
│           Funds received at 8:52 PM
│           Status: Confirmed
│
MARCH 28
│
└─ 4:15 PM  ✅ Premium Deducted
            -₹20 Smart Saver Plan
            Policy Week: Mar 28 - Apr 04
```

**Card Design:**
- Icon (left): Category emoji or icon
- Amount (right): + for credits, - for debits, color-coded
- Date/Time: Compact format `HH:MM AM/PM`
- Reference ID: `#Claim-12345` or `#D-67890`
- Status badge: Small pill with icon

**Colors:**
- Credited: 🟢 Emerald (#10B981)
- Pending: 🟡 Amber (#F59E0B)
- Failed: 🔴 Red (#EF4444)
- Reversed: 🔵 Blue (#3B82F6)

---

## 3. DETAILED WALLET FEATURES

### A. Balance Card (Hero Section)

**Component Structure:**
```dart
┌─────────────────────────────────────┐
│ [💳 Icon]  Available Balance   [⟳]  │
│            ₹520                     │
│ Last payout: 2 hrs ago              │
│                                     │
│ Status: Ready to Payout ✅          │
└─────────────────────────────────────┘
```

**Element Details:**

| Element | Style | Notes |
|---------|-------|-------|
| Icon | 24px | Color matches balance state |
| Amount | H1 style (26px W900) | High emphasis |
| Subtitle | Small (12px W600) | Secondary info |
| Refresh Button | Icon button | Animates during load |
| Background | Gradient | Orange to Deep Blue |
| Shadow | Soft shadow | 4px blur, 8% alpha |

**States:**
- **Loading**: Shimmer animation on amount, spinner on refresh
- **Success**: Green accent, confirmation toast
- **Error**: Red border, error message below
- **Offline**: Grayed out with "Last sync" time

---

### B. Quick Action Buttons

**Layout 1 (Profile Screen Integration):**
```
2-COLUMN MOBILE
┌─────────────────────────────────┐
│ [Request Payout] [View History] │
│  ₹250 Recommended  All Txns ▶   │
└─────────────────────────────────┘

3 SECONDARY ACTIONS
┌──────┬──────┬──────────────────┐
│[Add] │[TXN] │[View Receipts]   │
│Method│Report│                  │
└──────┴──────┴──────────────────┘
```

**Layout 2 (Tablet/Desktop):**
```
HORIZONTAL ROW
[Request]  [History]  [Add Method]  [Reports]  [Settings]
```

**Button Specifications:**
- Primary: `Elevated`, Orange bg, White text, 48px height
- Secondary: `Outlined`, Orange border, 44px height
- Tertiary: `Text`, Orange text, minimal styling

---

### C. Transaction List UI

**Individual Transaction Item:**
```
┌────────────────────────────────────────┐
│ 🔵 Earnings Credited          2:45 PM  │
│ +₹250 → Wallet                         │
│ Delivery Completion #D-12345           │
│ Mar 24, 2026                           │
│                                        │
│ [View Receipt]  [Share]  [More ⋯]      │
└────────────────────────────────────────┘
```

**Transaction Anatomy:**
- **Header**: Icon + Title + Time (right-aligned)
- **Amount**: Bold, color-coded (+green, -red)
- **Description**: Secondary text, reference ID
- **Date**: Subdued, full date on first transaction of day
- **Actions**: Context menu (receipt, share, report)

**Category Badges:**

| Category | Icon | Color | Examples |
|----------|------|-------|----------|
| CREDITED | 🟢 | Green (#10B981) | Delivery earnings, bonuses |
| PAYOUT | ⬅️ | Orange (#FF6A2A) | Payout sent to UPI |
| PREMIUM | 🛡️ | Blue (#3B82F6) | Insurance premium deduction |
| ADJUSTMENT | 🔧 | Gray (#9CA3AF) | Manual adjustments |
| REVERSED | ⤴️ | Red (#EF4444) | Failed/reversed transactions |

**List Behaviors:**
- Infinite scroll with pagination
- Pull-to-refresh at top
- Swipe actions (iOS): Pin, archive, delete
- Long-press (Android): Selection mode
- Date dividers: "TODAY", "YESTERDAY", "MARCH 28"

---

## 4. PAYOUT SETTINGS (Enhanced)

**Layout:**
```
PAYOUT SETTINGS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔐 PRIMARY PAYMENT METHOD
┌─────────────────────────────────┐
│ 🏦 worker@upi                   │
│ Active • Last used: 2 hrs ago   │
│ Status: ✅ Verified             │
│                                 │
│ [Change]  [Edit]                │
└─────────────────────────────────┘

➕ ADD ALTERNATIVE METHOD
┌─────────────────────────────────┐
│ [🏪 Add Bank Account]           │
│ [🏷️ Add Alternate UPI]          │
│ [💳 Add Debit Card (Soon)]      │
└─────────────────────────────────┘

⏰ AUTO-PAYOUT SCHEDULE
┌─────────────────────────────────┐
│ Auto-release every:             │
│ ┌─────────────────────┐          │
│ │ Monday ▼            │          │
│ └─────────────────────┘          │
│                                 │
│ Minimum balance: [₹250 ▼]       │
│                                 │
│ ✅ Auto-Payout Enabled          │
└─────────────────────────────────┘

📋 PAYOUT HISTORY
┌─────────────────────────────────┐
│ View Full Payout History... ▶   │
│ Downloaded: 15 payouts          │
│ Success Rate: 99.8%             │
└─────────────────────────────────┘
```

**Settings Details:**

| Setting | Type | Options | Default |
|---------|------|---------|---------|
| Primary Method | Radio | Active UPI/Bank | Worker's first verified method |
| Auto-Release | Toggle | ON/OFF | ON |
| Release Day | Dropdown | Mon-Sun | Monday |
| Min Balance | Stepper | ₹50-₹500 | ₹250 |
| Speed | Radio | Instant/Standard/Scheduled | Standard |

**UPI Verification Flow:**
```
1. User enters UPI ID
2. System validates format (regex: ^[a-zA-Z0-9._-]+@[a-zA-Z]+$)
3. API verification call
4. Status updates in real-time:
   - Loading: Spinner
   - Success: Green checkmark + timestamp
   - Error: Red X + error message
```

---

## 5. FULL WALLET SCREEN (Dedicated Tab)

**Complete Screen Layout:**

### Header
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
← [WALLET]                   [⟳]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Section 1: Balance & Summary
```
📊 CURRENT STATUS
┌──────────────────────────────────┐
│ Available:  ₹520 ✅              │
│ Pending:    ₹0                   │
│ Reserved:   ₹0                   │
│ ────────────────────────────     │
│ Total Today: ₹520                │
│ This Week: +₹2,150               │
│ This Month: +₹8,600              │
└──────────────────────────────────┘
```

### Section 2: Quick Stats
```
🎯 QUICK INSIGHTS
┌──────────────────────────────────┐
│ Payouts Received: 15             │
│ Avg Payout: ₹340                 │
│ Last Payout: 2 hrs ago           │
│ Fail Rate: 0.2%                  │
│ Success Streak: 127 days ✨       │
└──────────────────────────────────┘
```

### Section 3: Transaction Filters
```
📋 ALL TRANSACTIONS

[All Txns ▼] [Newest ▼] [Share ⬆]

Filter Options:
├─ All Transactions (15)
├─ Credits Only (12)
├─ Debits Only (3)
├─ Payouts (10)
├─ Premiums (3)
├─ Adjustments (2)
└─ Failed (0)

Date Range:
[Mar 1] - [Apr 24]  [This Month]
```

### Section 4: Transaction Feed
```
(Scrollable list of transactions as defined in Section 3)
```

### Section 5: Export & Download
```
📄 REPORTS & DOCUMENTS

[📥 Download CSV] This Month
[📄 Download PDF] Tax Receipt
[📤 Share Report] Via Email/Share
[📊 View Analytics] Weekly/Monthly

Available Reports:
├─ Monthly Income Statement
├─ Tax Summary (FY2026)
├─ Payout History
└─ Transaction Receipts (All)
```

---

## 6. BACKEND INTEGRATION REQUIREMENTS

### API Endpoints

```yaml
# Wallet Balance
GET /api/v1/wallet/balance
  Response:
    {
      "available": 520,
      "pending": 0,
      "reserved": 0,
      "last_payout_at": "2024-03-24T14:45:00Z"
    }

# Request Payout
POST /api/v1/wallet/request-payout
  Body:
    {
      "amount": 500,
      "method_id": "upi_worker@upi",
      "speed": "instant"  # instant|standard|scheduled
    }
  Response:
    {
      "payout_id": "POT-2024-03-24-1145",
      "status": "processing",
      "estimated_completion": "2024-03-24T14:47:00Z"
    }

# Get Transactions
GET /api/v1/wallet/transactions
  Query Parameters:
    - limit: 20
    - offset: 0
    - category: "all"  # all|credit|debit|payout|premium
    - date_from: "2024-03-01"
    - date_to: "2024-03-31"
  Response:
    {
      "transactions": [
        {
          "id": "txn_12345",
          "type": "payout",
          "category": "payout",
          "amount": 250,
          "status": "success",
          "method": "upi",
          "method_detail": "worker@upi",
          "reference_id": "D-12567",
          "description": "Payout to UPI",
          "created_at": "2024-03-24T14:45:00Z",
          "completed_at": "2024-03-24T14:45:12Z"
        }
      ],
      "total": 45,
      "count": 20
    }

# Verify UPI
POST /api/v1/wallet/verify-upi
  Body:
    {
      "upi_id": "worker@upi"
    }
  Response:
    {
      "valid": true,
      "verified_at": "2024-03-24T10:30:00Z",
      "registered_name": "WORKER NAME"
    }

# Payout History
GET /api/v1/wallet/payout-history
  Response:
    {
      "total_payouts": 15,
      "total_amount": 5100,
      "success_count": 15,
      "failed_count": 0,
      "success_rate": 100,
      "avg_payout": 340,
      "last_payout": "2024-03-24T14:45:00Z"
    }

# Set Auto-Payout
POST /api/v1/wallet/auto-payout-schedule
  Body:
    {
      "enabled": true,
      "day_of_week": 1,  # 0=Sunday, 1=Monday
      "min_balance": 250
    }

# Add Payment Method
POST /api/v1/wallet/payment-methods
  Body:
    {
      "type": "upi",  # upi|bank|card
      "value": "worker@upi",
      "is_primary": true
    }
  Response:
    {
      "method_id": "pm_12345",
      "type": "upi",
      "value": "worker@upi",
      "verified": false,
      "created_at": "2024-03-24T10:30:00Z"
    }

# Get Failed Payouts
GET /api/v1/wallet/failed-payouts
  Response:
    {
      "failed_payouts": [
        {
          "id": "POT-xxxx",
          "amount": 200,
          "reason": "Invalid UPI",
          "created_at": "2024-03-20T15:00:00Z",
          "retry_possible": true
        }
      ]
    }

# Retry Payout
POST /api/v1/wallet/retry-payout
  Body:
    {
      "payout_id": "POT-xxxx",
      "method_id": "pm_12345"
    }
```

### Data Models

```dart
class WalletBalance {
  final int availableAmount;
  final int pendingAmount;
  final int reservedAmount;
  final DateTime lastPayoutAt;
  
  WalletBalance({
    required this.availableAmount,
    required this.pendingAmount,
    required this.reservedAmount,
    required this.lastPayoutAt,
  });
}

class WalletTransaction {
  final String id;
  final int amountInr;
  final String reason;
  final String category;
  final String status;  // success|pending|failed|reversed
  final String? methodId;
  final String? methodDetail;
  final String? referenceId;
  final DateTime createdAt;
  final DateTime? completedAt;
  
  WalletTransaction({
    required this.id,
    required this.amountInr,
    required this.reason,
    required this.category,
    required this.status,
    this.methodId,
    this.methodDetail,
    this.referenceId,
    required this.createdAt,
    this.completedAt,
  });
}

class PaymentMethod {
  final String id;
  final String type;  // upi|bank|card
  final String value;
  final bool isVerified;
  final bool isPrimary;
  final DateTime createdAt;
  
  PaymentMethod({
    required this.id,
    required this.type,
    required this.value,
    required this.isVerified,
    required this.isPrimary,
    required this.createdAt,
  });
}

class AutoPayoutConfig {
  final bool enabled;
  final int dayOfWeek;  // 0-6
  final int minBalance;
  
  AutoPayoutConfig({
    required this.enabled,
    required this.dayOfWeek,
    required this.minBalance,
  });
}
```

---

## 7. KEY UX INTERACTIONS

### Interaction Patterns

| Interaction | Trigger | Behavior | Feedback |
|---|---|---|---|
| **Pull Refresh** | Pull down on balance card | Reload wallet data | Shimmer + "Updated" badge + timestamp |
| **Request Payout** | Tap balance card or button | Open payout modal | Haptic feedback (medium) |
| **Confirm Payout** | Tap confirm in modal | Call API, close modal | Toast with payout ID + redirect to receipt |
| **Failed Payout** | API error | Show error banner on profile | Red banner + "Retry" button |
| **Add UPI** | Tap "Edit" on payout settings | Inline text field | Real-time validation + API verify |
| **Copy to Clipboard** | Long-press transaction | Copy amount | "Copied!" toast |
| **View Receipt** | Tap transaction item | Open receipt modal | Slide-up animation |
| **Share Receipt** | Tap share button | Native share sheet | System share UI |
| **Filter Transactions** | Tap filter dropdown | Update list | Smooth re-render + count badge |
| **Auto-Payout Toggle** | Tap toggle switch | Update config | Haptic + confirmation toast |

### Animation Specifications

```
Balance Loading:
├─ Duration: 1.5s
├─ Curve: easeInOut
├─ Effect: Shimmer pulse on amount text

Payout Success:
├─ Duration: 0.8s
├─ Curve: bounceOut
├─ Effect: Confetti + scale animation on amount

Transaction List:
├─ Item entry: 0.3s slideUp
├─ Item exit: 0.2s slideDown
├─ Filter transition: 0.4s fade

Modal Open:
├─ Duration: 0.4s
├─ Curve: easeOut
├─ From: Bottom sheet

Modal Close:
├─ Duration: 0.3s
├─ Curve: easeIn
└─ To: Bottom sheet down
```

### Error Handling

```
UPI Verification Failed:
├─ Show: Red border on input
├─ Message: "Invalid UPI format"
├─ Suggestion: Show example format
└─ Action: Auto-focus field for retry

Payout Request Failed:
├─ Show: Red banner above balance
├─ Title: "Payout Failed"
├─ Details: Error reason (network/invalid UPI/etc)
├─ Action: [Retry] [Contact Support]
└─ Fallback: Link to WalletScreen with retry option

Network Timeout:
├─ Show: "Unable to connect"
├─ Offer: [Retry] [Work Offline]
├─ Cache: Show last known balance in gray
└─ Badge: "Last synced 5 mins ago"

Insufficient Balance:
├─ Show: "Insufficient balance"
├─ Highlight: Max available amount
├─ Action: Show delivery opportunities
└─ Recommendation: "Earn ₹100 more to request payout"
```

---

## 8. DESIGN TOKENS (Implementation)

### Color Palette

```dart
class WalletColors {
  // Hero States
  static const walletHeroGradient = [
    Color(0xFFFF6A2A),  // Orange (top)
    Color(0xFF111827),  // Deep Blue (bottom)
  ];
  
  // Transaction States
  static const transactionColors = {
    'credited': Color(0xFF10B981),    // Success Green
    'pending': Color(0xFFF59E0B),     // Warning Amber
    'failed': Color(0xFFEF4444),      // Error Red
    'reversed': Color(0xFF3B82F6),    // Info Blue
    'payout': Color(0xFF7C3AED),      // Violet
  };
  
  // UI Elements
  static const balancePositive = Color(0xFF10B981);
  static const balanceNegative = Color(0xFFEF4444);
  static const balancePending = Color(0xFFF59E0B);
  static const methodVerified = Color(0xFF10B981);
  static const methodUnverified = Color(0xFF9CA3AF);
}

class WalletTypography {
  static TextStyle get balanceAmount => GoogleFonts.outfit(
    fontSize: 32,
    fontWeight: FontWeight.w900,
    color: AppColors.textPrimary,
    letterSpacing: -0.5,
  );
  
  static TextStyle get balanceSubtitle => GoogleFonts.outfit(
    fontSize: 13,
    fontWeight: FontWeight.w500,
    color: AppColors.textSecondary,
    height: 1.4,
  );
  
  static TextStyle get transactionAmount => GoogleFonts.outfit(
    fontSize: 16,
    fontWeight: FontWeight.w800,
    color: AppColors.textPrimary,
  );
  
  static TextStyle get transactionLabel => GoogleFonts.outfit(
    fontSize: 12,
    fontWeight: FontWeight.w700,
    color: AppColors.textMuted,
    letterSpacing: 0.3,
  );
  
  static TextStyle get transactionDescription => GoogleFonts.outfit(
    fontSize: 13,
    fontWeight: FontWeight.w500,
    color: AppColors.textSecondary,
    height: 1.4,
  );
}

class WalletSpacing {
  static const heroCardPadding = 20.0;
  static const transactionItemPadding = 16.0;
  static const listItemGap = 12.0;
  static const sectionGap = 24.0;
}

class WalletShadows {
  static const heroShadow = [
    BoxShadow(
      color: Color(0xFF000000).withOpacity(0.08),
      blurRadius: 12,
      offset: Offset(0, 4),
    ),
  ];
  
  static const transactionShadow = [
    BoxShadow(
      color: Color(0xFF000000).withOpacity(0.04),
      blurRadius: 6,
      offset: Offset(0, 2),
    ),
  ];
}
```

### Icon Mapping

| Icon | Usage | Flutter Icon |
|------|-------|--------------|
| 💰 | Wallet/Balance | `Icons.account_balance_wallet_outlined` |
| ⬅️ | Payout/Transfer | `Icons.arrow_back_rounded` |
| ✅ | Success/Verified | `Icons.check_circle` |
| ⏱️ | Pending | `Icons.schedule_rounded` |
| ❌ | Failed | `Icons.cancel_rounded` |
| 🛡️ | Premium/Insurance | `Icons.shield_outlined` |
| 🔧 | Adjustment | `Icons.build_rounded` |
| 📋 | Transaction | `Icons.receipt_long_rounded` |
| 🔄 | Refresh | `Icons.refresh_rounded` |
| 📤 | Share | `Icons.share_rounded` |

---

## 9. WALLET INSIGHTS DASHBOARD (Optional Enhancement)

### Earnings Analytics Section

```
EARNINGS INSIGHTS
━━━━━━━━━━━━━━━━━━━━━━━━

📈 WEEKLY TREND
┌──────────────────────────────────┐
│                    ◆ (₹890)       │
│              ◆ (₹750)             │
│         ◆ (₹680)                  │
│         520  450                  │
│  ●  ●  ●  ●  ●  ●  ●             │
│ Mon Tue Wed Thu Fri Sat Sun       │
│                                  │
│ Best Day: Sunday (+23%)          │
│ Avg Daily: ₹562                  │
│ Weekly: ₹4,280                   │
└──────────────────────────────────┘

💡 SMART RECOMMENDATIONS
┌──────────────────────────────────┐
│ ✅ Focus on evening shifts       │
│    Average ₹120+ per hour        │
│                                  │
│ ✅ Sundays have 2x potential    │
│    ₹1,200+ earnings possible    │
│                                  │
│ 💫 Consider Elite Plan           │
│    You're averaging ₹600 daily  │
│    Elite: ₹35/week for ₹1k coverage
└──────────────────────────────────┘

📊 PAYOUT METRICS
├─ Success Rate: 99.8% ✨
├─ Avg Processing Time: 15s
├─ Total Payouts: 15
├─ Total Payout Value: ₹5,100
└─ Streaks: 127 days without failure
```

### Analytics Features

**Chart Types:**
- Line chart: Daily/Weekly earnings trend
- Bar chart: Category breakdown (earnings, premiums, bonuses)
- Pie chart: Payout method breakdown
- Heatmap: Peak earning hours/days

**Filters:**
- Time Range: This Week, This Month, Last 3 Months, Custom
- Category: All, Earnings, Payouts, Premiums
- Method: All, UPI, Bank, Card

**Export Options:**
- CSV: Full transaction export
- PDF: Formatted report with charts
- Excel: Spreadsheet with pivot tables
- Email: Auto-send monthly summary

---

## 10. PROGRESSIVE IMPLEMENTATION ROADMAP

### Phase 1: MVP (Week 1-2)
**Priority: Critical**

Features:
- [ ] Balance card on profile screen
- [ ] Request payout modal
- [ ] UPI management & validation
- [ ] Basic transaction history (last 10)
- [ ] Payout settings storage

Backend:
- [ ] GET `/wallet/balance`
- [ ] POST `/wallet/request-payout`
- [ ] POST `/wallet/verify-upi`
- [ ] GET `/wallet/transactions` (basic)

Components:
- `WalletBalanceCard` widget
- `RequestPayoutModal` widget
- `TransactionListTile` widget
- `WalletService` (API + local storage)

### Phase 2: Enhanced Transactions (Week 3-4)
**Priority: High**

Features:
- [ ] Full wallet screen with tab
- [ ] Transaction filters & search
- [ ] Transaction details modal
- [ ] Receipt view/download
- [ ] Share transaction receipts
- [ ] Date grouping in list

Backend:
- [ ] GET `/wallet/transactions` (advanced filters)
- [ ] GET `/wallet/transaction/{id}`
- [ ] POST `/wallet/share-receipt`

Components:
- `WalletScreen` (full page)
- `TransactionDetailModal` widget
- `TransactionFilterBar` widget
- `ReceiptGenerator` utility

### Phase 3: Payment Methods (Week 5-6)
**Priority: High**

Features:
- [ ] Add multiple payment methods
- [ ] Bank account integration
- [ ] Payment method management
- [ ] Delete/deactivate methods
- [ ] Switch primary method
- [ ] Method verification flow

Backend:
- [ ] POST `/wallet/payment-methods`
- [ ] GET `/wallet/payment-methods`
- [ ] PUT `/wallet/payment-methods/{id}`
- [ ] DELETE `/wallet/payment-methods/{id}`

Components:
- `PaymentMethodModal` widget
- `PaymentMethodList` widget
- `BankAccountForm` widget

### Phase 4: Analytics & Insights (Week 7-8)
**Priority: Medium**

Features:
- [ ] Weekly earnings chart
- [ ] Category breakdown
- [ ] Payout success metrics
- [ ] Recommendations engine
- [ ] Monthly reports
- [ ] Export to CSV/PDF

Backend:
- [ ] GET `/wallet/analytics`
- [ ] GET `/wallet/insights`
- [ ] POST `/wallet/export`

Components:
- `EarningsChart` widget
- `MetricsCard` widget
- `RecommendationBanner` widget

### Phase 5: Advanced Features (Week 9-10+)
**Priority: Low**

Features:
- [ ] Auto-payout scheduling
- [ ] Failed payout recovery
- [ ] Refund processing
- [ ] Tax document generation
- [ ] Spending categorization
- [ ] Budget alerts

Backend:
- [ ] POST `/wallet/auto-payout`
- [ ] POST `/wallet/retry-payout`
- [ ] GET `/wallet/failed-payouts`
- [ ] POST `/wallet/tax-documents`

---

## 11. KEY BENEFITS FOR GIG WORKERS

### Trust & Transparency
✅ **Real-time Balance** — Always know available funds  
✅ **Transaction Receipts** — Instant proof for every transaction  
✅ **Payment History** — Complete audit trail of all payouts  
✅ **Success Metrics** — 99.8% success rate visible  

### Speed & Convenience
⚡ **Instant Payouts** — 0-30 second processing  
⚡ **One-Tap Request** — No complex forms  
⚡ **Multiple Methods** — UPI, Bank, Card options  
⚡ **Auto-Payout** — Set and forget weekly releases  

### Financial Control
💰 **Minimum Balance Setting** — Control when you get paid  
💰 **Payout Scheduling** — Choose payout day  
💰 **Fee Transparency** — See exact deductions  
💰 **Smart Recommendations** — Optimize earnings  

### Security & Support
🔒 **UPI Verification** — Verified payment methods  
🔒 **Failed Payout Recovery** — Auto-retry on failure  
🔒 **Support Integration** — Contact support from wallet  
🔒 **Encryption** — All sensitive data encrypted  

### Income Intelligence
📊 **Earning Trends** — Visualize weekly patterns  
📊 **Peak Hour Analysis** — Know when to work  
📊 **Category Breakdown** — See where money comes from  
📊 **Tax Reports** — Auto-generated statements  

---

## Implementation Priority Summary

| Phase | Weeks | Impact | Effort |
|-------|-------|--------|--------|
| MVP | 1-2 | High | Medium |
| Transactions | 3-4 | High | Medium |
| Payment Methods | 5-6 | Medium | High |
| Analytics | 7-8 | Medium | Low |
| Advanced | 9+ | Low | High |

---

## Notes for Development Team

1. **Local Caching**: Cache balance & transactions locally for offline support
2. **Error Recovery**: Implement retry logic for failed payouts (exponential backoff)
3. **Push Notifications**: Alert user when payout succeeds/fails
4. **Accessibility**: Ensure WCAG 2.1 AA compliance for all UI components
5. **Testing**: Unit test all business logic, UI test all user flows
6. **Analytics**: Track payout requests, failures, retry rates
7. **Security**: Never log UPI IDs, use token-based API auth
8. **Performance**: Keep wallet API responses under 200ms for smooth UX

---

**Document Version**: 1.0  
**Last Updated**: April 24, 2026  
**Status**: Ready for Implementation
