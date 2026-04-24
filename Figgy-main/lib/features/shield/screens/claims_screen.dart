import 'package:flutter/material.dart';
import '../core/theme.dart';
import 'file_claim_screen.dart';

class ClaimsScreen extends StatefulWidget {
  const ClaimsScreen({super.key});

  @override
  State<ClaimsScreen> createState() => _ClaimsScreenState();
}

class _ClaimsScreenState extends State<ClaimsScreen> {
  int? expandedClaimIndex;

  final List<Map<String, dynamic>> claims = [
    {
      'id': '#FGY-2483',
      'status': 'Verifying',
      'time': '1:45 PM, Apr 2',
      'amount': '198',
      'loss': '300',
      'disruption': 'Heavy Rain',
      'period': '11:30 - 13:45',
      'step': 1, // 0-indexed, 1 means GPS done, currently at Delivery Log
    },
    {
      'id': '#FGY-2102',
      'status': 'Paid',
      'time': '10:15 AM, Mar 28',
      'amount': '450',
      'loss': '500',
      'disruption': 'Flood',
      'period': '08:00 - 12:00',
      'step': 3, // All done
    },
    {
      'id': '#FGY-1922',
      'status': 'Rejected',
      'time': '4:30 PM, Mar 25',
      'amount': '0',
      'loss': '300',
      'disruption': 'GPS Error',
      'period': '14:00 - 16:00',
      'step': 1, // Only GPS done
    }
  ];

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 800),
        child: ListView.builder(
          padding: const EdgeInsets.all(20),
          itemCount: claims.length,
          itemBuilder: (context, index) {
            final claim = claims[index];
            final bool isExpanded = expandedClaimIndex == index;

            return AnimatedContainer(
              duration: const Duration(milliseconds: 400),
              curve: Curves.easeInOut,
              margin: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(32),
                border: Border.all(color: Colors.grey.shade200),
                boxShadow: [
                  BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 20, offset: const Offset(0, 10)),
                ],
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(32),
                child: Column(
                  children: [
                    // Card Header (Large)
                    InkWell(
                      onTap: () {
                        setState(() {
                          expandedClaimIndex = isExpanded ? null : index;
                        });
                      },
                      child: Padding(
                        padding: const EdgeInsets.all(28),
                        child: Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(14),
                              decoration: BoxDecoration(color: AppColors.primary.withOpacity(0.12), shape: BoxShape.circle),
                              child: Icon(Icons.receipt_long_outlined, color: AppColors.primary, size: 28),
                            ),
                            const SizedBox(width: 20),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('Claim ${claim['id']}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18, letterSpacing: -0.3)),
                                  const SizedBox(height: 6),
                                  Text('Filed ${claim['time']}', style: TextStyle(color: Colors.grey.shade600, fontSize: 14)),
                                ],
                              ),
                            ),
                            _buildStatusChip(claim['status']),
                          ],
                        ),
                      ),
                    ),
                    // Animated Expansion UX
                    AnimatedSize(
                      duration: const Duration(milliseconds: 500),
                      curve: Curves.fastOutSlowIn,
                      child: isExpanded
                          ? _buildClaimDetails(claim)
                          : const SizedBox(width: double.infinity, height: 0),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildStatusChip(String status) {
    Color bgColor;
    Color textColor;
    switch (status) {
      case 'Paid':
        bgColor = Colors.green.shade50;
        textColor = Colors.green.shade700;
        break;
      case 'Rejected':
        bgColor = Colors.red.shade50;
        textColor = Colors.red.shade700;
        break;
      default:
        bgColor = Colors.orange.shade50;
        textColor = Colors.orange.shade700;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(color: bgColor, borderRadius: BorderRadius.circular(20)),
      child: Text(
        status,
        style: TextStyle(color: textColor, fontWeight: FontWeight.bold, fontSize: 13),
      ),
    );
  }

  Widget _buildClaimDetails(Map<String, dynamic> claim) {
    return TweenAnimationBuilder<Offset>(
      duration: const Duration(milliseconds: 600),
      curve: Curves.easeOutCubic,
      tween: Tween<Offset>(begin: const Offset(0, 0.4), end: Offset.zero),
      builder: (context, offset, child) {
        return Transform.translate(
          offset: offset * 150, // Slides up from bottom
          child: Opacity(
            opacity: (1 - (offset.dy / 0.4)).clamp(0, 1),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                   const Divider(),
                  const SizedBox(height: 16),
                  // Hero Amount Box (Professional Large)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 28),
                    width: double.infinity,
                    decoration: BoxDecoration(
                      color: claim['status'] == 'Paid' ? const Color(0xFFE8F5E9) : (claim['status'] == 'Rejected' ? const Color(0xFFFFEBEE) : const Color(0xFFFFF3E0)),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        RichText(
                          text: TextSpan(
                            style: TextStyle(
                              color: claim['status'] == 'Paid' ? const Color(0xFF1B5E20) : (claim['status'] == 'Rejected' ? const Color(0xFFB71C1C) : const Color(0xFFE65100)),
                              fontSize: 34,
                              fontWeight: FontWeight.bold,
                              letterSpacing: -0.5,
                            ),
                            children: [
                              TextSpan(text: claim['status'] == 'Rejected' ? '₹0 ' : '₹${claim['amount']} '),
                              TextSpan(
                                text: claim['status'] == 'Paid' ? 'paid' : (claim['status'] == 'Rejected' ? 'denied' : 'coming'),
                                style: const TextStyle(fontWeight: FontWeight.normal, fontSize: 34),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 10),
                        Text(
                          claim['status'] == 'Paid' ? 'Sent to your UPI · Apr 2, 3:52 PM' : (claim['status'] == 'Rejected' ? 'Delivery log deviation detected. No payout issued.' : '66% of ₹${claim['loss']} loss · Smart plancap applied'),
                          style: TextStyle(
                            color: claim['status'] == 'Paid' ? const Color(0xFF2E7D32) : (claim['status'] == 'Rejected' ? const Color(0xFFC62828) : const Color(0xFFEF6C00)),
                            fontSize: 15,
                            fontWeight: FontWeight.w400,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 32),
                  Text(
                    claim['status'] == 'Paid' ? 'VERIFICATION LOG' : (claim['status'] == 'Rejected' ? 'FAILURE REASON' : 'VERIFICATION STEPS'),
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.black.withOpacity(0.6), letterSpacing: 0.5),
                  ),
                  const SizedBox(height: 16),
                  if (claim['status'] == 'Paid') ...[
                    _buildStepTile(true, 'GPS confirmed', 'Worker in T Nagar zone 11:30-13:45', isDone: true),
                    _buildStepTile(false, 'Delivery log matched', '8 of 8 attempts succeeded (heavy rain)', isDone: true),
                    _buildStepTile(false, 'Anti-spoof check passed', 'Device sensor + route valid', isDone: true),
                    _buildStepTile(false, 'Proof-of-work token issued', 'Blockchain record: #0xA3F...', isDone: true),
                    _buildStepTile(false, 'Smart cap applied', '66% of ₹300 loss · Smart plan cap', isDone: true),
                  ] else if (claim['status'] == 'Rejected') ...[
                    _buildStepTile(true, 'GPS check failed', 'Incomplete GPS path in zone', isError: true),
                    _buildStepTile(false, 'Delivery log mismatch', 'No matching disrupted orders found', isError: true),
                     _buildStepTile(false, 'Proof-of-work rejected', 'Verification token invalid', isError: true),
                  ] else ...[
                    _buildStepTile(true, 'GPS activity confirmed', 'You were in T Nagar zone', isDone: true),
                    _buildStepTile(false, 'Delivery log cross-check', 'Matching order attempts', isLoading: true),
                    _buildStepTile(false, 'Proof reviewed', '2 photos attached'),
                    _buildStepTile(false, 'Payout approved', 'Sent to UPI'),
                  ],
                  if (claim['status'] == 'Paid' || claim['status'] == 'Rejected') ...[
                    const SizedBox(height: 24),
                    OutlinedButton(
                      onPressed: () {
                        if (claim['status'] == 'Rejected') {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => FileClaimScreen(
                                isResubmit: true,
                                claimId: claim['id'],
                              ),
                            ),
                          );
                        }
                      },
                      style: OutlinedButton.styleFrom(
                        side: BorderSide(color: claim['status'] == 'Paid' ? AppColors.primary : Colors.red.shade300, width: 1),
                         minimumSize: const Size(double.infinity, 55),
                         shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      child: Text(
                        claim['status'] == 'Paid' ? 'Download claim receipt' : 'Resubmit with better proof',
                        style: TextStyle(color: claim['status'] == 'Paid' ? AppColors.primary : Colors.red.shade700, fontWeight: FontWeight.normal, fontSize: 16),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Center(
                      child: Text(
                        'Shield tab updated · ${claim['status']} shown',
                        style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
                      ),
                    ),
                  ],
                  const SizedBox(height: 24),
                  _buildStatusBreakdownBox(claim['status']),
                  const SizedBox(height: 32),
                  const Text('Your submission', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  const SizedBox(height: 16),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF9F9F4),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: Colors.grey.shade100),
                    ),
                    child: Column(
                      children: [
                        _buildSubmissionRow('Disruption', claim['disruption']),
                        _buildSubmissionRow('Time', claim['period']),
                        _buildSubmissionRow('Estimated loss', '₹${claim['loss']}'),
                        _buildSubmissionRow('Proof', '', isProof: true),
                      ],
                    ),
                  ),
                  const SizedBox(height: 32),
                  const Center(
                    child: Column(
                      children: [
                        Text(
                          'Expected resolution by 4:00 PM today.',
                          style: TextStyle(color: Colors.black87, fontSize: 13, fontWeight: FontWeight.normal),
                        ),
                        SizedBox(height: 4),
                        Text(
                          'We\'ll notify you.',
                          style: TextStyle(color: Colors.black87, fontSize: 13, fontWeight: FontWeight.normal),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildStatusBreakdownBox(String status) {
    if (status == 'Verifying') return const SizedBox.shrink();

    final bool isPaid = status == 'Paid';
    final Color bgColor = isPaid ? const Color(0xFFE8F5E9) : const Color(0xFFFFEBEE);
    final Color textColor = isPaid ? const Color(0xFF2E7D32) : const Color(0xFFC62828);
    final String title = isPaid ? 'Success Highlights' : 'Missing Requirements';
    final List<String> items = isPaid
        ? [
            'Claim settled instantly to UPI',
            'Smart plancap maximized payout',
            'Blockchain proof verified',
            'Shield balance updated',
          ]
        : [
            'GPS data points were sparse',
            'Delivery attempts did not match',
            'Proof photos insufficient',
            'Token could not be minted',
          ];

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: bgColor, borderRadius: BorderRadius.circular(16)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: textColor)),
          const SizedBox(height: 12),
          ...items.map((item) => Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('• ', style: TextStyle(color: textColor, fontWeight: FontWeight.bold, fontSize: 16)),
                Expanded(child: Text(item, style: TextStyle(color: textColor.withOpacity(0.9), fontSize: 13, height: 1.4))),
              ],
            ),
          )),
        ],
      ),
    );
  }

  Widget _buildStepTile(bool isFirst, String title, String subtitle, {bool isDone = false, bool isLoading = false, bool isError = false}) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      decoration: BoxDecoration(
        color: const Color(0xFFF5F5EF),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Icon(
            isDone ? Icons.check : (isError ? Icons.close : (isLoading ? Icons.radio_button_checked : Icons.radio_button_off)),
            size: 18,
            color: isDone ? const Color(0xFF2E7D32) : (isError ? const Color(0xFFC62828) : (isLoading ? Colors.orange : Colors.grey)),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.black, height: 1.2)),
                const SizedBox(height: 2),
                Text(subtitle, style: TextStyle(color: Colors.black.withOpacity(0.6), fontSize: 11, height: 1.2)),
              ],
            ),
          ),
          if (isLoading)
            const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2, valueColor: AlwaysStoppedAnimation<Color>(Colors.orange)),
            ),
        ],
      ),
    );
  }

  Widget _buildSubmissionRow(String label, String value, {bool isProof = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        crossAxisAlignment: isProof ? CrossAxisAlignment.start : CrossAxisAlignment.center,
        children: [
          Text(label, style: TextStyle(color: Colors.black.withOpacity(0.7), fontSize: 15)),
          if (isProof)
            Row(
              children: [
                _buildThumbnailBox(Icons.camera_alt_outlined),
                const SizedBox(width: 10),
                _buildThumbnailBox(Icons.description_outlined),
              ],
            )
          else
            Text(value, style: const TextStyle(fontWeight: FontWeight.normal, fontSize: 15, color: Colors.black)),
        ],
      ),
    );
  }

  Widget _buildThumbnailBox(IconData icon) {
    return Container(
      width: 60,
      height: 60,
      decoration: BoxDecoration(
        color: const Color(0xFFF9F9F4),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: Icon(icon, size: 24, color: Colors.grey.shade500),
    );
  }
}
