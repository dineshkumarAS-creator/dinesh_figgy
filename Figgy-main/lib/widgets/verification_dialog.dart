import 'dart:async';
import 'package:flutter/material.dart';
import 'package:figgy_app/theme/app_theme.dart';

Future<void> showVerificationDialog(BuildContext context, VoidCallback onSuccess) {
  return showDialog(
    context: context,
    barrierDismissible: false,
    builder: (context) => _VerificationDialog(onSuccess: onSuccess),
  );
}

class _VerificationDialog extends StatefulWidget {
  final VoidCallback onSuccess;
  const _VerificationDialog({required this.onSuccess});

  @override
  State<_VerificationDialog> createState() => _VerificationDialogState();
}

class _VerificationDialogState extends State<_VerificationDialog> with SingleTickerProviderStateMixin {
  int _secondsRemaining = 28 * 60 + 15; // 28 mins 15 secs
  Timer? _timer;
  
  bool _isVerifying = false;
  bool _isSuccess = false;
  
  late AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _startTimer();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
  }

  void _startTimer() {
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) return;
      setState(() {
        if (_secondsRemaining > 0) {
          _secondsRemaining--;
        } else {
          _timer?.cancel();
        }
      });
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    _pulseController.dispose();
    super.dispose();
  }

  String get _formattedTime {
    final minutes = (_secondsRemaining / 60).floor();
    final seconds = _secondsRemaining % 60;
    return '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
  }

  Future<void> _handleConfirm() async {
    setState(() {
      _isVerifying = true;
    });
    
    // Simulate API Call Verification
    await Future.delayed(const Duration(milliseconds: 1500));
    if (!mounted) return;
    
    setState(() {
      _isVerifying = false;
      _isSuccess = true;
    });
    
    // Simulate Success Message Before Closing
    await Future.delayed(const Duration(milliseconds: 1500));
    if (!mounted) return;
    
    widget.onSuccess();
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      backgroundColor: Colors.white,
      insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 400),
        child: AnimatedSize(
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOutCubic,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (!_isSuccess) ...[
                _buildHeader(),
                _buildMapChallenge(),
                _buildFooterActions(),
              ] else ...[
                _buildSuccessState(),
              ]
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 20),
      decoration: const BoxDecoration(
        color: Color(0xFFFEE2E2),
        borderRadius: BorderRadius.only(topLeft: Radius.circular(24), topRight: Radius.circular(24)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.timer_outlined, color: Color(0xFFEF4444), size: 24),
          const SizedBox(width: 8),
          Text(
            '$_formattedTime remaining',
            style: AppTypography.h3.copyWith(
              color: const Color(0xFFB91C1C),
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMapChallenge() {
    return Container(
      height: 220,
      width: double.infinity,
      color: const Color(0xFFF3F4F6),
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Simulated map background pattern
          Positioned.fill(
            child: CustomPaint(
              painter: _MapGridPainter(),
            ),
          ),
          
          // Tolerance zone (2km circle)
          Container(
            width: 140,
            height: 140,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: const Color(0xFF22C55E).withOpacity(0.15),
              border: Border.all(color: const Color(0xFF22C55E).withOpacity(0.5), width: 2),
            ),
          ),
          
          // Blue Pin (Disruption Location) - center
          const Icon(Icons.location_on, color: Colors.blue, size: 40),
          
          // Pulse Animation for Red Pin
          AnimatedBuilder(
            animation: _pulseController,
            builder: (context, child) {
              return Transform.translate(
                offset: const Offset(30, 20), // 150m away logically
                child: Container(
                  width: 30 + (_pulseController.value * 20),
                  height: 30 + (_pulseController.value * 20),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: const Color(0xFFEF4444).withOpacity(0.3 - (_pulseController.value * 0.3)),
                  ),
                ),
              );
            },
          ),
          
          // Red Pin (User GPS)
          Transform.translate(
            offset: const Offset(30, 20),
            child: Container(
              width: 16,
              height: 16,
              decoration: BoxDecoration(
                color: const Color(0xFFEF4444),
                shape: BoxShape.circle,
                border: Border.all(color: Colors.white, width: 3),
                boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 4)],
              ),
            ),
          ),
          
          // Distance badge
          Positioned(
            bottom: 12,
            right: 12,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 4)],
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.my_location, size: 14, color: AppColors.textSecondary),
                  const SizedBox(width: 4),
                  Text('150m from claim zone', style: AppTypography.small.copyWith(fontWeight: FontWeight.w700)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFooterActions() {
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        children: [
          Text(
            'Confirm you are actively in the disruption zone to secure your payout.',
            textAlign: TextAlign.center,
            style: AppTypography.bodySmall.copyWith(color: AppColors.textSecondary, height: 1.4),
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            height: 54,
            child: ElevatedButton(
              onPressed: _isVerifying ? null : _handleConfirm,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.brandPrimary,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                elevation: 0,
              ),
              child: _isVerifying
                  ? const SizedBox(
                      width: 24, height: 24,
                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                    )
                  : Text(
                      'CONFIRM LOCATION',
                      style: AppTypography.h3.copyWith(color: Colors.white, fontWeight: FontWeight.w900),
                    ),
            ),
          ),
          const SizedBox(height: 16),
          GestureDetector(
            onTap: () {
              // Action to send SMS
            },
            child: Text(
              'Or verify via SMS',
              style: AppTypography.small.copyWith(
                color: AppColors.textSecondary,
                fontWeight: FontWeight.w600,
                decoration: TextDecoration.underline,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSuccessState() {
    return Padding(
      padding: const EdgeInsets.all(40.0),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 80, height: 80,
            decoration: BoxDecoration(
              color: const Color(0xFFDCFCE7),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.check, color: Color(0xFF16A34A), size: 48),
          ),
          const SizedBox(height: 24),
          Text(
            'Location Verified!',
            style: AppTypography.h2.copyWith(fontWeight: FontWeight.w900, color: const Color(0xFF166534)),
          ),
          const SizedBox(height: 8),
          Text(
            'Trust Score +0.05\nReady for payout',
            textAlign: TextAlign.center,
            style: AppTypography.bodyMedium.copyWith(color: const Color(0xFF166534), fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }
}

class _MapGridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.black.withOpacity(0.04)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;
      
    for (double i = 0; i < size.width; i += 20) {
      canvas.drawLine(Offset(i, 0), Offset(i, size.height), paint);
    }
    for (double i = 0; i < size.height; i += 20) {
      canvas.drawLine(Offset(0, i), Offset(size.width, i), paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
