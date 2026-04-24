# FIGGY Display & Output Requirements for Your App

## What Your App Can Display to Users

---

## 1. WORKER/CLAIMANT MOBILE APP

### Claim Submission Screen
```
┌─────────────────────────────────────┐
│  NEW CLAIM                          │
├─────────────────────────────────────┤
│                                     │
│  Disruption Event:                  │
│  ├─ Event Type: Curfew              │
│  ├─ Location: Mumbai, Bandra        │
│  ├─ Active Since: 2 hours ago       │
│  ├─ Severity: High (4/5)            │
│  └─ Source: Govt Alert              │
│                                     │
│  Claim Details:                     │
│  ├─ Income Lost: ₹1,500             │
│  ├─ Duration: 4 hours              │
│  ├─ Status: Ready to Submit         │
│  └─ ⚠️ Will be verified             │
│                                     │
│  [SUBMIT CLAIM]  [CANCEL]           │
└─────────────────────────────────────┘
```

### Active Claims Dashboard
```
┌─────────────────────────────────────┐
│  MY CLAIMS                          │
├─────────────────────────────────────┤
│                                     │
│  Claim #CLM-001                     │
│  ┌─────────────────────────────────┤
│  │ Amount: ₹1,500                  │
│  │ Status: UNDER_REVIEW            │
│  │ Submitted: 2 hours ago          │
│  │ Progress:                       │
│  │ ✓ Submitted                     │
│  │ ⏳ ML Scoring (in progress)      │
│  │ ⏳ Verification                 │
│  │ ⏳ Review                       │
│  │ ⏳ Payout                       │
│  │                                 │
│  │ [VIEW DETAILS]  [TRACK]          │
│  └─────────────────────────────────┤
│                                     │
│  Claim #CLM-002                     │
│  ┌─────────────────────────────────┤
│  │ Amount: ₹2,000                  │
│  │ Status: APPROVED                │
│  │ Submitted: 1 day ago            │
│  │ Approved: 4 hours ago           │
│  │ Payment: Processing             │
│  │                                 │
│  │ [VIEW DETAILS]  [RECEIPT]        │
│  └─────────────────────────────────┤
│                                     │
│  Claim #CLM-003                     │
│  ┌─────────────────────────────────┤
│  │ Amount: ₹800                    │
│  │ Status: REJECTED                │
│  │ Reason: Location verification   │
│  │ failed (GPS mismatch)           │
│  │ Rejected: 6 hours ago           │
│  │ ⚠️ Can be appealed (23h left)    │
│  │                                 │
│  │ [VIEW DETAILS]  [APPEAL]         │
│  └─────────────────────────────────┤
│                                     │
└─────────────────────────────────────┘
```

### Soft Verification Challenge Screen
```
┌─────────────────────────────────────┐
│  LOCATION VERIFICATION              │
│  ⏱️ 28 minutes remaining             │
├─────────────────────────────────────┤
│                                     │
│  Your Claim at: Bandra, Mumbai      │
│                                     │
│  [  MAP VISUALIZATION  ]            │
│  ├─ Original location (blue pin)    │
│  ├─ Your current location (red pin) │
│  ├─ Tolerance zone (2km radius)     │
│  └─ Distance: 150m ✓ PASS           │
│                                     │
│  Response Method:                   │
│  ┌─────────────────────────────────┐
│  │ [✓ CONFIRM LOCATION]            │
│  │ or                              │
│  │ [RESPOND VIA SMS]               │
│  └─────────────────────────────────┘
│                                     │
│  Why this check?                    │
│  GPS verification proves you were   │
│  at the disruption location during  │
│  the time of your claim.            │
│                                     │
│  ℹ️ You can respond via:             │
│  • App tap (recommended)            │
│  • SMS: Reply "YES" to +91-XXXX     │
│  • Click link in notification       │
│                                     │
└─────────────────────────────────────┘
```

### Challenge Response Timeline
```
┌─────────────────────────────────────┐
│  CHALLENGE RESPONSE                 │
├─────────────────────────────────────┤
│                                     │
│  Challenge Sent: 12:30 PM           │
│  ├─ Your Claim at: Bandra           │
│  ├─ Tolerance: ±2km from location   │
│  └─ Valid until: 1:00 PM (30min)    │
│                                     │
│  Location Score: 0.95               │
│  ├─ GPS Accuracy: 12m ✓             │
│  ├─ Distance from claim: 150m ✓     │
│  └─ Within tolerance zone ✓         │
│                                     │
│  Response Speed: 0.80               │
│  ├─ Responded at: 12:42 PM          │
│  ├─ Time taken: 12 minutes ✓        │
│  └─ Before SLA expiry ✓             │
│                                     │
│  Final Score: 0.95 PASS             │
│  └─ Status: Ready for payout        │
│                                     │
└─────────────────────────────────────┘
```

### Appeal Submission Screen
```
┌─────────────────────────────────────┐
│  APPEAL REJECTED CLAIM              │
├─────────────────────────────────────┤
│                                     │
│  Claim #CLM-003                     │
│  Reason: Location verification      │
│  failed                             │
│  Amount: ₹800                       │
│                                     │
│  Your Appeal:                       │
│  ┌─────────────────────────────────┐
│  │ [Text Input]                    │
│  │ I was at the location but GPS   │
│  │ was acting up due to network    │
│  │ interference in the area.       │
│  │                                 │
│  │ Max 500 characters (234/500)    │
│  └─────────────────────────────────┘
│                                     │
│  Supporting Evidence:               │
│  [+ Add Photo] [+ Add Video]        │
│  ├─ photo_1.jpg (1.2 MB)           │
│  ├─ video_1.mp4 (15 MB)            │
│  └─ receipt_proof.pdf (800 KB)      │
│                                     │
│  📋 Agreement                       │
│  ☑ I declare the information is     │
│    truthful and accurate.           │
│                                     │
│  Appeal SLA: 24 hours              │
│  Decision by: Tomorrow 6:00 PM     │
│                                     │
│  [SUBMIT APPEAL]  [CANCEL]          │
└─────────────────────────────────────┘
```

### Payment Status Screen
```
┌─────────────────────────────────────┐
│  PAYMENT RECEIVED                   │
├─────────────────────────────────────┤
│                                     │
│  ✓ APPROVED                         │
│                                     │
│  Amount: ₹1,500.00                  │
│  Claim ID: CLM-001                  │
│  Approved By: Reviewer (Senior)     │
│  Approved At: Apr 16, 2:30 PM      │
│                                     │
│  Transaction Details:               │
│  ├─ Ref #: TXN-2026041601234       │
│  ├─ Settled: Apr 16, 3:15 PM       │
│  ├─ Method: NEFT to Bank Account    │
│  ├─ A/C: ****5429                   │
│  └─ IFSC: SBIN0001001               │
│                                     │
│  Payment Confirmation:              │
│  Your bank has credited ₹1,500     │
│  Check your bank app for balance    │
│  update (may take 2-4 hours).      │
│                                     │
│  Next Steps:                        │
│  • Claim Closed                     │
│  • Receipt saved to device          │
│  • Tax receipt available            │
│                                     │
│  [DOWNLOAD RECEIPT]  [SHARE]        │
│  [VIEW CLAIM DETAILS]               │
│                                     │
└─────────────────────────────────────┘
```

### Statistics Dashboard (Worker)
```
┌─────────────────────────────────────┐
│  MY STATISTICS                      │
├─────────────────────────────────────┤
│                                     │
│  Total Claims: 12                   │
│  ├─ Approved: 10 (83%)              │
│  ├─ Pending: 1 (8%)                 │
│  ├─ Rejected: 1 (8%)                │
│  └─ Average decision time: 2.3h     │
│                                     │
│  Total Earned: ₹18,500              │
│  ├─ This Month: ₹5,200              │
│  ├─ Last Month: ₹8,100              │
│  └─ Average per claim: ₹1,542       │
│                                     │
│  Trust Score: 0.92 (Excellent)      │
│  ├─ On-time responses: 100%         │
│  ├─ Location accuracy: 95%          │
│  ├─ Approval rate: 83%              │
│  └─ No fraud flags                  │
│                                     │
│  Recent Activity:                   │
│  • CLM-050: Approved (2d ago)       │
│  • CLM-049: Approved (5d ago)       │
│  • CLM-048: Rejected (1w ago)       │
│                                     │
└─────────────────────────────────────┘
```

---

## 2. REVIEWER/CLAIMS ADJUSTER DASHBOARD

### Reviewer Queue Dashboard
```
┌──────────────────────────────────────────────────┐
│  MY REVIEW QUEUE          [Filters] [Sort]       │
├──────────────────────────────────────────────────┤
│                                                  │
│  CRITICAL (Priority 1) - 3 items (2h SLA)       │
│  ┌──────────────────────────────────────────────┐
│  │ CLM-092 | ₹2,500 | NEW WORKER              │
│  │ Disruption: Curfew (Mumbai)                │
│  │ Flagged: GPS Anomaly Detected              │
│  │ Assigned: 45 min ago ⚠️ 1h 15m left         │
│  │ Status: Ready for Review                   │
│  │ [VIEW CONTEXT] [MAKE DECISION]              │
│  └──────────────────────────────────────────────┘
│                                                  │
│  ┌──────────────────────────────────────────────┐
│  │ CLM-091 | ₹1,800 | WORKERS FLAG             │
│  │ Disruption: Strike (Delhi)                 │
│  │ Risk: High (0.72 fraud score)              │
│  │ Assigned: 1h ago ⚠️ 1h left                 │
│  │ Status: Ready for Review                   │
│  │ [VIEW CONTEXT] [MAKE DECISION]              │
│  └──────────────────────────────────────────────┘
│                                                  │
│  HIGH (Priority 2) - 8 items (4h SLA)          │
│  ┌──────────────────────────────────────────────┐
│  │ CLM-090 | ₹600 | New but high disruption   │
│  │ Disruption: Bandh (Bangalore)              │
│  │ Status: In Progress (assigned 2h ago)      │
│  │ [VIEW CONTEXT] [MAKE DECISION] [RELEASE]    │
│  └──────────────────────────────────────────────┘
│                                                  │
│  NORMAL (Priority 3) - 15 items (8h SLA)       │
│  [Collapsed - Load 5 | Load More]               │
│                                                  │
│  Load Indicator:                                │
│  You: 5/10 claims | Senior Alice: 8/10        │
│      (50% capacity)        (80% capacity)       │
│                                                  │
│  📊 Queue Stats:                                │
│  • Total: 26 claims                             │
│  • SLA Breaches: 0                              │
│  • Avg Review Time: 8.3 min                     │
│  • Your Approval Rate: 72%                      │
│                                                  │
└──────────────────────────────────────────────────┘
```

### Claim Context View (Reviewer)
```
┌──────────────────────────────────────────────────┐
│  CLAIM REVIEW                      CLM-092       │
│  Worker: Priya Sharma (ID: worker_123)          │
├──────────────────────────────────────────────────┤
│                                                  │
│  CLAIM DETAILS                                  │
│  ├─ Amount: ₹2,500                              │
│  ├─ Disruption: Curfew (Mumbai, Bandra)         │
│  ├─ Claim Date: Apr 16, 10:30 AM               │
│  ├─ Lost Hours: 5                               │
│  ├─ Rate/Hour: ₹500                             │
│  └─ Status: NEW - Unverified                    │
│                                                  │
│  WORKER PROFILE                                 │
│  ├─ Trust Tier: NEW (first claim)               │
│  ├─ Total Claims: 1                             │
│  ├─ Approval Rate: N/A                          │
│  ├─ Flagged Reasons: None                       │
│  ├─ Disruption Zone: Bandra (high activity)     │
│  └─ Previous Claims in Zone: 0                  │
│                                                  │
│  ML RISK ASSESSMENT 🤖                          │
│  ┌──────────────────────────────────────────────┐
│  │ Overall Risk Score: 0.72 (HIGH RISK)         │
│  │                                              │
│  │ Key Signals:                                 │
│  │ ⚠️ GPS Pattern Anomaly (-0.35 SHAP)          │
│  │    Road match: 0.12 (vs typical 0.85)       │
│  │    Suggests possible GPS spoofing             │
│  │                                              │
│  │ ⚠️ Motion Continuity Low (-0.28 SHAP)        │
│  │    Sudden jumps in location detected         │
│  │    May indicate network issues or fraud      │
│  │                                              │
│  │ ✓ Network Conditions: Normal (+0.15)         │
│  │    Good signal strength expected              │
│  │                                              │
│  │ 🤖 Claude AI Summary:                        │
│  │ "Worker shows unusual GPS pattern: road      │
│  │  match 0.12 vs typical 0.85 for disruption  │
│  │  in this zone. Motion continuity is low,     │
│  │  suggesting network interference or GPS      │
│  │  spoofing attempt. New worker status adds    │
│  │  risk. Recommend live location verification." │
│  │                                              │
│  │ Recommended Action: MANUAL_FLAG              │
│  └──────────────────────────────────────────────┘
│                                                  │
│  CLAIM HISTORY                                  │
│  ├─ Similar claims this worker: 0               │
│  ├─ Similar claims this zone: 8                 │
│  ├─ Approval rate (similar): 85%                │
│  └─ [View last 5 similar claims]                │
│                                                  │
│  PROOF DOCUMENTS                                │
│  ├─ photo_proof_1.jpg (2.3 MB) [DOWNLOAD]       │
│  ├─ video_disruption.mp4 (18 MB) [STREAM]       │
│  └─ receipt_income.pdf (1.1 MB) [DOWNLOAD]      │
│                                                  │
│  GPS TRACE VISUALIZATION                        │
│  ┌──────────────────────────────────────────────┐
│  │ [30-minute GPS trace on map]                 │
│  │ Start: 10:30 AM                              │
│  │ End: 11:00 AM                                │
│  │ Points: 180 (1 every 10 seconds)             │
│  │ ├─ Red line = path taken                     │
│  │ ├─ Green zone = expected disruption area     │
│  │ └─ Blue dot = current location               │
│  │                                              │
│  │ [ZOOM IN] [ZOOM OUT] [CENTER]                │
│  └──────────────────────────────────────────────┘
│                                                  │
│  CROWD VALIDATION                               │
│  └─ 42 other workers claimed same disruption    │
│     in this zone • 87% approved rate            │
│                                                  │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│  YOUR DECISION                                   │
├──────────────────────────────────────────────────┤
│                                                  │
│  Decision: [ Select... ▼ ]                       │
│  ├─ APPROVE                                      │
│  ├─ REJECT                                       │
│  └─ REQUEST_MORE_INFO                            │
│                                                  │
│  Confidence (1-5): [●●●○○] 3/5                  │
│                                                  │
│  Rejection Reason (if applicable):              │
│  ☑ GPS Spoofing (High Risk)                     │
│  ☐ Insufficient Evidence                        │
│  ☐ Income Loss Not Verified                     │
│  ☐ Claim Not Eligible                           │
│  ☐ Worker Flagged                               │
│                                                  │
│  Additional Notes:                              │
│  ┌──────────────────────────────────────────────┐
│  │ [Text Input - Optional]                      │
│  │ GPS anomaly detected. New worker claiming    │
│  │ high amount with suspicious location data.   │
│  │ Recommend flag for fraud investigation.      │
│  │                                              │
│  │ (142/500 characters)                         │
│  └──────────────────────────────────────────────┘
│                                                  │
│  Payout Override (optional):                    │
│  [ ] Override amount: ₹_______                  │
│                                                  │
│  [SUBMIT DECISION] [SAVE DRAFT] [RELEASE]       │
│                                                  │
└──────────────────────────────────────────────────┘
```

### Appeal Review Screen
```
┌──────────────────────────────────────────────────┐
│  APPEAL REVIEW                     APP-045       │
│  Original Claim: CLM-089                         │
│  Appealing Worker: Ramesh Kumar                  │
├──────────────────────────────────────────────────┤
│                                                  │
│  APPEAL SUBMITTED                               │
│  ├─ Date: Apr 16, 3:45 PM                       │
│  ├─ SLA: 24 hours (until tomorrow 3:45 PM)      │
│  ├─ ⏱️ 19h 30m remaining                         │
│  └─ Status: Pending Review                      │
│                                                  │
│  ORIGINAL DECISION                              │
│  ├─ Claim Amount: ₹1,200                        │
│  ├─ Original Reviewer: Alice (Senior)           │
│  ├─ Decision: REJECTED                          │
│  ├─ Reason: Location Verification Failed        │
│  └─ Confidence: 4/5                             │
│                                                  │
│  APPEAL REASON FROM WORKER                      │
│  ┌──────────────────────────────────────────────┐
│  │ "I was at the location but my GPS was        │
│  │  acting up because there was network         │
│  │  interference. I have a screenshot showing   │
│  │  poor signal at 11:30 AM that day. Also,     │
│  │  many other workers in the same area were    │
│  │  approved."                                  │
│  └──────────────────────────────────────────────┘
│                                                  │
│  SUPPORTING EVIDENCE (from worker)              │
│  ├─ photo_signal_strength.jpg (2.1 MB)          │
│  ├─ testimonial_workers.pdf (980 KB)            │
│  └─ location_screenshot.png (1.5 MB)            │
│                                                  │
│  COMPARISON DATA                                │
│  ├─ Similar zone area claims: 14                │
│  ├─ Approved in that period: 12 (86%)           │
│  ├─ Rejected in that period: 2 (14%)            │
│  └─ This worker's rejection rate: 10%           │
│     (1 rejection out of 10 claims)              │
│                                                  │
│  RE-ANALYSIS                                    │
│  ├─ New ML explanation: Available               │
│  ├─ GPS trace re-examined: Shows network kicks  │
│  ├─ Signal map correlation: Matches worker      │
│  └─ Crowd consensus: 86% approval rate          │
│                                                  │
│  YOUR DECISION                                  │
│  ├─ Decision: [ Select... ▼ ]                   │
│  │  ├─ APPEAL_APPROVED (overturn rejection)     │
│  │  └─ APPEAL_REJECTED (uphold original)        │
│  │                                              │
│  ├─ Confidence: [●●●●○] 4/5                     │
│  │                                              │
│  ├─ Decision Notes:                             │
│  │  ┌────────────────────────────────────────┐  │
│  │  │ Worker's evidence supports claim.      │  │
│  │  │ Signal map shows network interference  │  │
│  │  │ at exact location/time. Crowd voting   │  │
│  │  │ also supports (86% approval). Overturn │  │
│  │  │ decision. Recommend network test in    │  │
│  │  │ that zone for future claims.           │  │
│  │  └────────────────────────────────────────┘  │
│  │                                              │
│  └─ [SUBMIT DECISION] [SAVE DRAFT]              │
│                                                  │
│  ⚠️ Note: Appeals are critical tier review        │
│     Lead/Senior reviewers only.                  │
│                                                  │
└──────────────────────────────────────────────────┘
```

### Reviewer Performance Dashboard
```
┌──────────────────────────────────────────────────┐
│  MY PERFORMANCE                                  │
├──────────────────────────────────────────────────┤
│                                                  │
│  📊 DECISION METRICS                             │
│  ├─ Total Decided: 127                           │
│  ├─ Approval Rate: 72%                           │
│  │  └─ Trend: ↑ +3% (last week)                  │
│  ├─ Avg Decision Time: 8.3 min                   │
│  │  └─ Target: <10 min ✓ ON TRACK               │
│  ├─ SLA Breaches: 0/127 (0%)                     │
│  │  └─ Status: ✓ EXCELLENT                       │
│  └─ Current Load: 5/10 claims (50%)              │
│                                                  │
│  📈 QUALITY METRICS                              │
│  ├─ Appeal Overturn Rate: 8%                     │
│  │  └─ Interpretation: 8 of 100 rejections get   │
│  │     overturned on appeal (healthy: 5-15%)     │
│  ├─ Decision Reversals: 2 (in last month)        │
│  │  └─ Reason: QA audit flagged false fraud      │
│  ├─ False Positive Rate: 12%                     │
│  │  └─ Status: ⚠️ SLIGHTLY HIGH (target <10%)    │
│  └─ False Negative Rate: 2%                      │
│     └─ Status: ✓ GOOD (target <5%)               │
│                                                  │
│  🎓 SKILL LEVEL: SENIOR REVIEWER                 │
│  ├─ Since: Jan 2026                              │
│  ├─ Tier Authorized: CRITICAL, HIGH              │
│  ├─ Specialization: High-Payout Claims           │
│  └─ Mentoring: 2 junior reviewers                │
│                                                  │
│  🔔 ALERTS                                       │
│  └─ ⚠️ False positive rate trending up            │
│     Recommendation: Review last 10 rejections    │
│     for pattern analysis                         │
│                                                  │
│  📅 RECENT ACTIVITY                              │
│  ├─ Today: 14 decisions (2h 4m avg time)         │
│  ├─ This Week: 64 decisions                      │
│  ├─ This Month: 127 decisions                    │
│  └─ 🏆 Top Reviewer this week!                   │
│                                                  │
│  [DOWNLOAD REPORT] [VIEW DETAILED BREAKDOWN]     │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## 3. OPERATIONS/ADMIN DASHBOARD

### Queue Health Dashboard
```
┌──────────────────────────────────────────────────┐
│  QUEUE HEALTH                      [LIVE]        │
├──────────────────────────────────────────────────┤
│                                                  │
│  QUEUE DEPTH (Real-Time)                        │
│  ┌──────────────────────────────────────────────┐
│  │                                              │
│  │  CRITICAL (2h SLA)      ░░░░░░░░░  8 items   │
│  │  HIGH (4h SLA)         ░░░░░░░░░░░░░  32     │
│  │  NORMAL (8h SLA)       ░░░░░░░░░░░░░░░░░      │
│  │                        (many items)  156      │
│  │                                              │
│  └──────────────────────────────────────────────┘
│                                                  │
│  SLA STATUS                                     │
│  ├─ CRITICAL:                                   │
│  │  ├─ Avg Age: 45 min (SLA: 2h)                │
│  │  ├─ Max Age: 1h 38m ✓ Before breach         │
│  │  ├─ Breach Rate: 0%                          │
│  │  └─ Status: ✓ HEALTHY                        │
│  │                                              │
│  ├─ HIGH:                                       │
│  │  ├─ Avg Age: 1h 22m (SLA: 4h)                │
│  │  ├─ Max Age: 3h 45m ✓ Before breach         │
│  │  ├─ Breach Rate: 0%                          │
│  │  └─ Status: ✓ HEALTHY                        │
│  │                                              │
│  └─ NORMAL:                                     │
│     ├─ Avg Age: 4h 12m (SLA: 8h)                │
│     ├─ Max Age: 7h 33m ✓ Before breach         │
│     ├─ Breach Rate: 0%                          │
│     └─ Status: ✓ HEALTHY                        │
│                                                  │
│  REVIEWER CAPACITY                              │
│  ├─ Online: 12 / 15 reviewers (80%)             │
│  ├─ At Capacity: 3 reviewers (20%)              │
│  ├─ Available Slots: 28 claims                  │
│  ├─ Pending Assignments: 196                    │
│  └─ ⚠️ Alert: Consider calling on-call lead      │
│                                                  │
│  THROUGHPUT (Last Hour)                         │
│  ├─ Submitted: 45 claims                        │
│  ├─ Decided: 38 claims                          │
│  ├─ Burn Rate: 85% (target >90%)                │
│  └─ ⚠️ Alert: Workload > capacity                │
│                                                  │
│  [AUTO-ALERT CONFIG]  [CALL ESCALATION TEAM]    │
│                                                  │
└──────────────────────────────────────────────────┘
```

### System Health Monitoring
```
┌──────────────────────────────────────────────────┐
│  SYSTEM HEALTH                     [LIVE]        │
├──────────────────────────────────────────────────┤
│                                                  │
│  SERVICES STATUS                                │
│  ├─ Layer 0 (Event Detection):     ✓ UP         │
│  ├─ Layer 1 (Kafka):               ✓ UP         │
│  ├─ Layer 2 (Weather/AQI):         ✓ UP         │
│  ├─ Layer 3 (Features):            ✓ UP         │
│  ├─ Layer 4 (ML Scores):           ✓ UP         │
│  ├─ Layer 5 (Soft Verify):         ✓ UP         │
│  ├─ Layer 6 (Manual Review):       ✓ UP         │
│  ├─ Layer 7 (Payout):              ✓ UP         │
│  └─ Redis Cache:                   ✓ UP         │
│                                                  │
│  PERFORMANCE METRICS                            │
│  ├─ Avg Latency: 234ms (target <500ms) ✓       │
│  ├─ Error Rate: 0.12% (target <1%) ✓            │
│  ├─ Db Connections: 45/100 (45%)                │
│  ├─ API Response Time: 89ms                     │
│  ├─ Kafka Lag: 2.3s (normal)                    │
│  └─ Cache Hit Rate: 87%                         │
│                                                  │
│  ALERTS ACTIVE: 0                               │
│  └─ Last alert: 2d ago (resolved)               │
│                                                  │
│  [DETAILED LOGS]  [CONFIGURE ALERTS]            │
│                                                  │
└──────────────────────────────────────────────────┘
```

### Analytics Dashboard
```
┌──────────────────────────────────────────────────┐
│  ANALYTICS & INSIGHTS               [Apr 16]     │
├──────────────────────────────────────────────────┤
│                                                  │
│  📊 CLAIMS OVERVIEW (Today)                      │
│  ├─ Submitted: 142 claims                        │
│  ├─ Approved: 98 (69%)   ✓                       │
│  ├─ Rejected: 28 (20%)   ⚠                       │
│  ├─ Pending: 16 (11%)    ⏳                       │
│  └─ Total Payout: ₹1,84,500                      │
│                                                  │
│  📈 TRENDS (Last 7 Days)                         │
│  ├─ Approval Rate: 70% (↑ from 65% week ago)    │
│  ├─ Avg Decision Time: 7.8 min (↓ improved)     │
│  ├─ Appeal Rate: 8% (↓ from 12%)                │
│  ├─ Appeal Overturn: 9% (normal range)          │
│  └─ False Rejection Rate: 11% (↓ improving)     │
│                                                  │
│  🔍 FRAUD METRICS                               │
│  ├─ Claims Flagged: 12 (8.5% of total)          │
│  ├─ Manual Investigation: 8 (67%)               │
│  ├─ Confirmed Fraud: 3 (25%)                    │
│  ├─ Appeal Overturns: 2 (17%)                   │
│  └─ Workers Blocked: 2 (repeat fraud)           │
│                                                  │
│  👥 REVIEWER STATS                              │
│  ├─ Active: 12/15 (80%)                         │
│  ├─ Avg Load: 6.2/10 (62%)                      │
│  ├─ Avg Decision Time: 8.1 min                  │
│  ├─ Avg Approval Rate: 71%                      │
│  └─ Schedule:                                   │
│     • Shift 1 (6-2pm): 4 reviewers              │
│     • Shift 2 (2-10pm): 5 reviewers             │
│     • Shift 3 (10pm-6am): 3 reviewers           │
│                                                  │
│  🌍 GEOGRAPHIC HOTSPOTS                         │
│  ├─ Mumbai: 45 claims (31%), 72% approval      │
│  ├─ Delhi: 32 claims (23%), 68% approval       │
│  ├─ Bangalore: 28 claims (20%), 75% approval   │
│  ├─ Hyderabad: 22 claims (15%), 82% approval   │
│  └─ Other: 15 claims (11%), 73% approval       │
│                                                  │
│  [EXPORT REPORT] [SCHEDULE EMAIL] [CUSTOM VIEW] │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## 4. REAL-TIME TRACKING & NOTIFICATIONS

### Push Notifications (SMS + App)

**Claimant gets:**
```
1. Claim Submitted
   "Your claim #CLM-001 for ₹1,500 received. 
    Decision in ~4 hours. Check app for updates."

2. Verification Challenge
   "Location verification needed! Respond to confirm 
    your location. 30 min window. Tap to respond."

3. Challenge Response Status
   "Location verified ✓. GPS match score: 0.95. 
    Your claim approved for payout!"

4. Decision (Approved)
   "Your claim #CLM-001 approved! ₹1,500 being 
    processed. Check payment status in app."

5. Decision (Rejected)
   "Your claim #CLM-001 rejected. Reason: Location 
    verification failed. You can appeal (24h left)."

6. Payment Received
   "₹1,500 credited to your account. 
    Ref: TXN-2026041601234. Tap to view receipt."
```

**Reviewer gets:**
```
1. New Claim Assigned
   "New claim assigned: CLM-092 (₹2,500, CRITICAL). 
    Risk: HIGH. Review urgently (1h 45m left)."

2. Appeals Pending
   "New appeal submitted: APP-045. Decision needed 
    by tomorrow 3:45 PM. Review now."

3. Queue Alert
   "⚠️ Critical queue > 20 items. 3 claims may 
    breach SLA soon. Consider calling backup."

4. Performance Alert
   "Your false positive rate: 14% (target <10%). 
    Review last 10 rejections for patterns."
```

---

## 5. DOWNLOADABLE REPORTS

**Worker can download:**
```
✓ Claim Receipt (PDF)
  - Claim details, decision, payout confirmation
  
✓ Payment Proof (PDF)
  - Transaction ID, amount, date, bank details
  
✓ Tax Certificate (PDF)
  - Annual earnings, category, FIGGY attestation
  
✓ Claims History (CSV)
  - All past claims with decisions and amounts
```

**Reviewer can download:**
```
✓ Daily Report (PDF)
  - Claims decided, approval rate, avg time, alerts
  
✓ Performance Report (PDF)
  - Monthly stats, overturn rates, appeals handled
  
✓ Queue Analysis (CSV)
  - Queue metrics, SLA status, bottlenecks
```

**Admin can download:**
```
✓ System Health Report (PDF)
  - Service status, performance metrics, alerts
  
✓ Analytics Dashboard (PDF/CSV)
  - Claims overview, trends, fraud metrics, geo hotspots
  
✓ Capacity Planning (Excel)
  - Queue projections, reviewer needed, cost analysis
```

---

## Summary: What Can Be Displayed

| User Type | Can Display |
|-----------|---|
| **Worker** | Claim status, verification challenges, appeal form, payment confirmation, stats, history |
| **Reviewer** | Pending queue, claim context, ML explanations, worker profile, decision form, performance stats |
| **Admin** | Queue health, system status, analytics, alerts, capacity, trends, fraud metrics |
| **All Users** | Real-time notifications, downloadable reports, GPS visualizations, decision timelines |

