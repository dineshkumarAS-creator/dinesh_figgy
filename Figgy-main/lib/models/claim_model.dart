/// claim_model.dart
/// -----------------
/// Data model for a Figgy GigShield claim.
/// Used by claim flows (Shield hub, claim_processing_screen, and
/// claim_details_screen) to display claim lifecycle state.

class ClaimModel {
  final String claimId;
  final String disruptionType; // "Heavy Rain" | "Flood" | "Extreme Heat" etc.
  final String date;           // YYYY-MM-DD — from created_at
  final String status;         // under_review | verifying | approved | rejected | manual_review | paid
  final int estimatedLoss;     // INR, self-reported
  final int compensation;      // INR, eligible_payout from server
  final String? fraudRisk;     // "low" | "medium" | "high" | null
  final String? payoutUpi;     // UPI handle once payout is triggered
  final String uiMessage;      // Human-readable status message for the app
  final bool appealEligible;   // Updated in this session
  final String? rejectionReason;
  final String? payoutStatus;         // initiated | paid | failed
  final String? paymentFailedReason;

  const ClaimModel({
    required this.claimId,
    required this.disruptionType,
    required this.date,
    required this.status,
    required this.estimatedLoss,
    required this.compensation,
    this.fraudRisk,
    this.payoutUpi,
    required this.uiMessage,
    this.appealEligible = false,
    this.rejectionReason,
    this.payoutStatus,
    this.paymentFailedReason,
  });

  // ---------------------------------------------------------------------------
  // Factory — parse from GET /api/claim/status/:id or list item
  // ---------------------------------------------------------------------------
  factory ClaimModel.fromJson(Map<String, dynamic> json) {
    // Safely extract date from created_at (ISO string → YYYY-MM-DD)
    final createdAt = json['created_at'] as String? ?? '';
    final date = createdAt.length >= 10 ? createdAt.substring(0, 10) : createdAt;

    final status = json['status'] as String? ?? 'under_review';

    return ClaimModel(
      claimId:        json['claim_id']       as String? ?? '',
      disruptionType: json['disruption_type'] as String?  //  manual claims
                   ?? json['claim_type']      as String?  //  auto claims
                   ?? 'Unknown',
      date:           date,
      status:         status,
      estimatedLoss:  (json['estimated_loss'] as num?)?.toInt() ?? 0,
      compensation:   (json['eligible_payout'] as num?)?.toInt()
                   ?? (json['compensation']   as num?)?.toInt()
                   ?? 0,
      fraudRisk:  json['fraud_risk']  as String?,
      payoutUpi:  json['payout_upi']  as String?,
      uiMessage:  json['ui_message']  as String? ?? _uiMessage(status),
      appealEligible: json['appeal_eligible'] == true,
      rejectionReason: json['rejection_reason'] as String?,
      payoutStatus: json['payout_status'] as String?,
      paymentFailedReason: json['payment_failed_reason'] as String?,
    );
  }

  // ---------------------------------------------------------------------------
  // Convenience getters — used by claim_processing_screen for UI state
  // ---------------------------------------------------------------------------

  /// True once the UPI credit completes.
  bool get isPaid => status == 'paid';

  /// True while the backend is processing (under_review or verifying).
  bool get isUnderReview =>
      status == 'under_review' || status == 'verifying';

  /// True if the claim was rejected by the fraud engine.
  bool get isRejected => status == 'rejected';

  /// True if a human needs to manually approve (medium/high fraud risk).
  bool get isManualReview => status == 'manual_review';

  /// True once the payout has been successfully approved.
  bool get isApproved => status == 'approved';

  /// True if payment failed
  bool get isPaymentFailed => status == 'payment_failed';

  // ---------------------------------------------------------------------------
  // toJson — for caching / local storage
  // ---------------------------------------------------------------------------
  Map<String, dynamic> toJson() => {
    'claim_id':       claimId,
    'disruption_type': disruptionType,
    'created_at':     date,
    'status':         status,
    'estimated_loss': estimatedLoss,
    'eligible_payout': compensation,
    'fraud_risk':     fraudRisk,
    'payout_upi':     payoutUpi,
  };

  // ---------------------------------------------------------------------------
  // UI copy helper
  // ---------------------------------------------------------------------------
  static String _uiMessage(String status) {
    switch (status) {
      case 'under_review':
        return 'Your claim is submitted and under review.';
      case 'verifying':
        return 'We\'re verifying your claim details — this takes a moment.';
      case 'approved':
        return 'Claim approved! Payout is being processed.';
      case 'paid':
        return 'Payout credited to your UPI. Check your bank.';
      case 'rejected':
        return 'Claim could not be approved. See details below.';
      case 'manual_review':
        return 'Your claim needs additional review. We\'ll notify you soon.';
      default:
        return 'Checking claim status...';
    }
  }

  @override
  String toString() =>
      'ClaimModel($claimId, $status, ₹$compensation, fraud: $fraudRisk)';
}
