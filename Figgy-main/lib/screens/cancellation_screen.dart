import 'package:flutter/material.dart';
import 'package:figgy_app/screens/cancellation_confirm_screen.dart';

class CancellationScreen extends StatefulWidget {
  const CancellationScreen({super.key});

  @override
  State<CancellationScreen> createState() => _CancellationScreenState();
}

class _CancellationScreenState extends State<CancellationScreen> {
  int? _selectedReasonIndex;

  final List<String> _reasons = [
    '₹20 a week is too much for me',
    "I'm not working in this area anymore",
    'I want to switch to a bigger plan',
    'Something else',
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF7F6F1), // Slight off-white background matching typical app surface
      appBar: AppBar(
        backgroundColor: const Color(0xFFE46B44),
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.white),
          onPressed: () => Navigator.pop(context),
        ),
        title: const Text(
          'Stop my plan',
          style: TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.w600,
            fontSize: 16,
          ),
        ),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        child: Container(
          color: Colors.white,
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Red Alert Box
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFFFCE8E8), // Light red bg
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Are you sure you want to stop?',
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF991B1B), // Dark red
                      ),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Once you stop, Figgy will not pay you if rain, floods or strikes happen.',
                      style: TextStyle(
                        fontSize: 12,
                        color: Color(0xFF991B1B),
                        height: 1.4,
                      ),
                    ),
                    const SizedBox(height: 12),
                    _buildAlertPoint(
                      icon: Icons.close_rounded,
                      iconColor: const Color(0xFFDC2626), // Red
                      text: 'No more money if disruptions happen',
                      textColor: const Color(0xFF991B1B),
                    ),
                    const SizedBox(height: 6),
                    _buildAlertPoint(
                      icon: Icons.close_rounded,
                      iconColor: const Color(0xFFDC2626),
                      text: "₹20 fee stops, but this week's fee is not refunded",
                      textColor: const Color(0xFF991B1B),
                    ),
                    const SizedBox(height: 6),
                    _buildAlertPoint(
                      icon: Icons.check_rounded,
                      iconColor: const Color(0xFF16A34A), // Green
                      text: 'Any claim we already approved will still be paid to you',
                      textColor: const Color(0xFF166534), // Darker green text for the positive aspect
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              
              const Text(
                'Why are you stopping?',
                style: TextStyle(
                  fontSize: 14,
                  color: Colors.black87,
                ),
              ),
              const SizedBox(height: 12),
              
              // Radio Buttons
              ...List.generate(_reasons.length, (index) {
                return _buildReasonOption(index, _reasons[index]);
              }),

              const SizedBox(height: 24),

              // Green Pause Box
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFFEAF5E1), // Light green bg
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'A better option: take a break instead',
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.black87, // Or Dark Green based on image it looks dark grayish black
                      ),
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      'You can pause for up to 4 weeks. Your protection comes back by itself after that.',
                      style: TextStyle(
                        fontSize: 12,
                        color: Colors.black87, // dark color text
                        height: 1.4,
                      ),
                    ),
                    const SizedBox(height: 12),
                    OutlinedButton(
                      onPressed: () {
                        // Pause action
                        Navigator.pop(context);
                      },
                      style: OutlinedButton.styleFrom(
                        side: const BorderSide(color: Color(0xFF2E7D32)), // Dark green border
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      ),
                      child: const Text(
                        'Take a break instead',
                        style: TextStyle(
                          color: Color(0xFF1B5E20), // Dark green text
                          fontWeight: FontWeight.w500,
                          fontSize: 14,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              
              const SizedBox(height: 24),

              // Action Buttons
              SizedBox(
                width: double.infinity,
                height: 48,
                child: OutlinedButton(
                  onPressed: () {
                    // Navigate to confirmation screen
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => const CancellationConfirmScreen(),
                      ),
                    );
                  },
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: Color(0xFFD1D5DB)), // Light gray border
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                  child: const Text(
                    'Yes, I want to stop the plan',
                    style: TextStyle(
                      color: Colors.black,
                      fontWeight: FontWeight.w600,
                      fontSize: 14,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                height: 48,
                child: OutlinedButton(
                  onPressed: () {
                    // Keep running action
                    Navigator.pop(context);
                  },
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: Color(0xFFD1D5DB)),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                  child: const Text(
                    'Keep my plan running',
                    style: TextStyle(
                      color: Colors.black,
                      fontWeight: FontWeight.w600,
                      fontSize: 14,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 32),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildAlertPoint({required IconData icon, required Color iconColor, required String text, required Color textColor}) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(top: 2.0),
          child: Icon(icon, color: iconColor, size: 14),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            text,
            style: TextStyle(
              fontSize: 12,
              color: textColor,
              height: 1.3,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildReasonOption(int index, String text) {
    bool isSelected = _selectedReasonIndex == index;
    return GestureDetector(
      onTap: () {
        setState(() {
          _selectedReasonIndex = index;
        });
      },
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(color: const Color(0xFFE5E7EB)),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          children: [
            Container(
              width: 18,
              height: 18,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: isSelected ? const Color(0xFFE46B44) : const Color(0xFF9CA3AF),
                  width: isSelected ? 5 : 1.5,
                ),
              ),
            ),
            const SizedBox(width: 12),
            Text(
              text,
              style: const TextStyle(
                fontSize: 14,
                color: Colors.black87,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

