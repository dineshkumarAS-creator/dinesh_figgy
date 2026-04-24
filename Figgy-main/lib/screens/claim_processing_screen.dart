import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:figgy_app/routes.dart';
import 'package:figgy_app/models/claim_model.dart';
import 'package:figgy_app/config/api_base_url.dart';
import 'package:figgy_app/features/profile/profile_screen.dart';
import 'package:figgy_app/screens/claim_details_screen.dart';

class ClaimProcessingScreen extends StatefulWidget {
  final String claimId;
  final String? initialStatus;

  const ClaimProcessingScreen({super.key, required this.claimId, this.initialStatus});

  @override
  State<ClaimProcessingScreen> createState() => _ClaimProcessingScreenState();
}

enum ProcessingState {
  receiving,
  verifying,
  calculating,
  paid,
  manualReview,
  rejected,
  paymentFailed,
}

class _ClaimProcessingScreenState extends State<ClaimProcessingScreen> with TickerProviderStateMixin {
  Timer? _pollingTimer;
  Timer? _elapsedTimer;
  int _elapsedSeconds = 0;
  bool _claimNotFoundHandled = false;

  ProcessingState _currentState = ProcessingState.receiving;
  int _payoutAmount = 0;
  bool _isTerminal = false;

  // Flash animation for PAID state
  late AnimationController _flashController;
  late Animation<Color?> _flashColorAnimation;

  @override
  void initState() {
    super.initState();

    _flashController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 500),
    );
    _flashColorAnimation = ColorTween(
      begin: const Color(0xFF0F0F13),
      end: Colors.green.withOpacity(0.8),
    ).animate(_flashController);

    if (widget.initialStatus != null) {
      _currentState = _statusToState(widget.initialStatus!, 0);
      _isTerminal = _isTerminalState(_currentState);
    }

    _startTimers();
  }

  void _startTimers() {
    _elapsedTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      setState(() {
        if (!_isTerminal) _elapsedSeconds++;
      });
    });

    // Initial poll
    _pollStatus();

    _pollingTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      _pollStatus();
    });
  }

  Future<void> _pollStatus() async {
    if (_isTerminal) return;

    try {
      final res = await http.get(Uri.parse('${figgyApiBaseUrl}/api/claim/status/${widget.claimId}'));
      
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        final status = data['status'] as String? ?? 'verifying';
        final step = data['processing_step'] as int? ?? 1;
        _payoutAmount = data['payout_amount'] as int? ?? 0;

        _mapStatusToState(status, step);
      } else if (res.statusCode == 404 && !_claimNotFoundHandled) {
        _claimNotFoundHandled = true;
        _pollingTimer?.cancel();
        _elapsedTimer?.cancel();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Claim not found or expired. Please trigger a new claim.'),
              backgroundColor: Colors.orange,
            ),
          );
          Navigator.of(context).popUntil((route) => route.isFirst);
        }
      }
    } catch (e) {
      debugPrint("Polling error: $e");
    }
  }

  void _mapStatusToState(String status, int step) {
    if (_isTerminal) return;

    final newState = _statusToState(status, step);
    _isTerminal = _isTerminalState(newState);

    if (newState != _currentState) {
      setState(() {
        _currentState = newState;
      });

      if (_isTerminal) {
        _handleTerminalState();
      }
    }
  }

  ProcessingState _statusToState(String status, int step) {
    // Prefer explicit backend status — async auto_trigger often leaves
    // processing_step at 1 while status moves under_review → verifying → approved → paid.
    final s = status.toLowerCase();
    if (s == 'paid') return ProcessingState.paid;
    if (s == 'rejected') return ProcessingState.rejected;
    if (s == 'manual_review') return ProcessingState.manualReview;
    if (s == 'payment_failed') return ProcessingState.paymentFailed;
    if (s == 'under_review') return ProcessingState.receiving;
    if (s == 'verifying') return ProcessingState.verifying;
    if (s == 'approved') return ProcessingState.calculating;
    if (step <= 1) return ProcessingState.receiving;
    if (step >= 2 && step <= 4) return ProcessingState.verifying;
    return ProcessingState.calculating;
  }

  bool _isTerminalState(ProcessingState state) {
    return state == ProcessingState.paid ||
        state == ProcessingState.rejected ||
        state == ProcessingState.manualReview ||
        state == ProcessingState.paymentFailed;
  }

  void _handleTerminalState() {
    _pollingTimer?.cancel();
    _elapsedTimer?.cancel();

    if (_currentState == ProcessingState.paid) {
      _flashController.forward().then((_) => _flashController.reverse());
    }

    if (_currentState != ProcessingState.manualReview) {
      Future.delayed(const Duration(milliseconds: 1500), () {
        if (mounted) {
          Navigator.pushReplacementNamed(
            context,
            AppRoutes.claimDetails,
            arguments: ClaimDetailsArgs(claimId: widget.claimId),
          );
        }
      });
    }
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    _elapsedTimer?.cancel();
    _flashController.dispose();
    super.dispose();
  }

  String get _formattedTime {
    final m = _elapsedSeconds ~/ 60;
    final s = _elapsedSeconds % 60;
    return '${m}:${s.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    // ignore: deprecated_member_use
    return WillPopScope(
      onWillPop: () async => false, // Block back button
      child: AnimatedBuilder(
        animation: _flashColorAnimation,
        builder: (context, child) {
          return Scaffold(
            backgroundColor: _isTerminal && _currentState == ProcessingState.paid 
                ? _flashColorAnimation.value 
                : const Color(0xFF0F0F13),
            body: SafeArea(
              child: Center(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24.0),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Spacer(),
                      _buildAnimatedIcon(),
                      const SizedBox(height: 48),
                      _buildAnimatedText(),
                      const SizedBox(height: 16),
                      _buildAnimatedSubtitle(),
                      const Spacer(),
                      if (_isTerminal) _buildTerminalCTA(),
                      const SizedBox(height: 32),
                      _buildElapsedCounter(),
                      const SizedBox(height: 24),
                    ],
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildAnimatedIcon() {
    switch (_currentState) {
      case ProcessingState.receiving:
        return _PulsingIcon(
          color: Colors.blue,
          icon: Icons.download_rounded,
        );
      case ProcessingState.verifying:
        return const _ScanningBars();
      case ProcessingState.calculating:
        return const SizedBox(
          width: 80,
          height: 80,
          child: CircularProgressIndicator(
            color: Colors.orange,
            strokeWidth: 3,
          ),
        );
      case ProcessingState.paid:
        return const Icon(Icons.check_circle_rounded, color: Colors.green, size: 80);
      case ProcessingState.manualReview:
        return const Icon(Icons.access_time_filled_rounded, color: Colors.amber, size: 80);
      case ProcessingState.rejected:
        return const Icon(Icons.cancel_rounded, color: Colors.red, size: 80);
      case ProcessingState.paymentFailed:
        return const Icon(Icons.warning_rounded, color: Colors.orange, size: 80);
    }
  }

  Widget _buildAnimatedText() {
    String text;
    Color color = Colors.white;

    switch (_currentState) {
      case ProcessingState.receiving:
        text = "Receiving your claim...";
        break;
      case ProcessingState.verifying:
        text = "Checking your work records...";
        break;
      case ProcessingState.calculating:
        text = "Calculating your payout...";
        break;
      case ProcessingState.paid:
        text = "₹$_payoutAmount is on its way!";
        color = Colors.greenAccent;
        break;
      case ProcessingState.manualReview:
        text = "Quick check needed";
        color = Colors.amber;
        break;
      case ProcessingState.rejected:
        text = "Disruption not confirmed in your area";
        color = Colors.redAccent;
        break;
      case ProcessingState.paymentFailed:
        text = "Payment didn't go through";
        color = Colors.orangeAccent;
        break;
    }

    return Text(
      text,
      textAlign: TextAlign.center,
      style: TextStyle(
        fontSize: 22,
        fontWeight: FontWeight.w700,
        color: color,
        letterSpacing: 0.5,
      ),
    );
  }

  Widget _buildAnimatedSubtitle() {
    String text;
    switch (_currentState) {
      case ProcessingState.receiving:
        text = "Claim ID: ${widget.claimId}";
        break;
      case ProcessingState.verifying:
        text = "GPS · Deliveries · App activity";
        break;
      case ProcessingState.calculating:
        text = "Expected vs actual earnings";
        break;
      case ProcessingState.paid:
        text = "Transfer successful";
        break;
      case ProcessingState.manualReview:
        text = "Usually done in 2 hours. We'll notify you.";
        break;
      case ProcessingState.rejected:
        text = "Our systems show normal activity patterns.";
        break;
      case ProcessingState.paymentFailed:
        text = "Please check your UPI ID in Profile";
        break;
    }

    return Text(
      text,
      textAlign: TextAlign.center,
      style: const TextStyle(
        fontSize: 14,
        fontWeight: FontWeight.w400,
        color: Colors.white60,
        letterSpacing: 0.5,
      ),
    );
  }

  Widget _buildTerminalCTA() {
    String label = "";
    VoidCallback onTap = () {};

    switch (_currentState) {
      case ProcessingState.paid:
        label = "See Payment Details →";
        onTap = () {
          // Handled by auto-navigate timeout usually, but if clicked before:
          Navigator.pushReplacementNamed(
            context,
            AppRoutes.claimDetails,
            arguments: ClaimDetailsArgs(claimId: widget.claimId),
          );
        };
        break;
      case ProcessingState.manualReview:
        label = "View Claim Status";
        onTap = () => Navigator.of(context).popUntil((route) => route.isFirst);
        break;
      case ProcessingState.rejected:
        label = "Contact Support";
        onTap = () {
          debugPrint("Support tapped");
        };
        break;
      case ProcessingState.paymentFailed:
        label = "Update UPI →";
        onTap = () {
          Navigator.push(context, MaterialPageRoute(builder: (_) => const ProfileScreen(focusUpi: true)));
        };
        break;
      default:
        return const SizedBox.shrink();
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 16.0),
      child: TextButton(
        onPressed: onTap,
        style: TextButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          backgroundColor: Colors.white.withOpacity(0.1),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
        ),
        child: Text(
          label,
          style: const TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.w700,
            fontSize: 14,
          ),
        ),
      ),
    );
  }

  Widget _buildElapsedCounter() {
    return Text(
      "Processing for $_formattedTime...",
      style: const TextStyle(
        fontSize: 12,
        color: Colors.white38,
        fontWeight: FontWeight.w500,
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Custom Animations
// ─────────────────────────────────────────────────────────────────────────────

class _PulsingIcon extends StatefulWidget {
  final Color color;
  final IconData icon;

  const _PulsingIcon({required this.color, required this.icon});

  @override
  _PulsingIconState createState() => _PulsingIconState();
}

class _PulsingIconState extends State<_PulsingIcon> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(vsync: this, duration: const Duration(milliseconds: 1000))..repeat(reverse: true);
    _animation = Tween<double>(begin: 0.9, end: 1.2).animate(CurvedAnimation(parent: _controller, curve: Curves.easeInOut));
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ScaleTransition(
      scale: _animation,
      child: Container(
        width: 100,
        height: 100,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: widget.color.withOpacity(0.15),
          border: Border.all(color: widget.color.withOpacity(0.5), width: 2),
        ),
        child: Icon(widget.icon, color: widget.color, size: 48),
      ),
    );
  }
}

class _ScanningBars extends StatefulWidget {
  const _ScanningBars();

  @override
  _ScanningBarsState createState() => _ScanningBarsState();
}

class _ScanningBarsState extends State<_ScanningBars> with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(vsync: this, duration: const Duration(milliseconds: 1500))..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 80,
      child: AnimatedBuilder(
        animation: _controller,
        builder: (context, child) {
          return Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(3, (index) {
              // Offset phase for each bar
              double t = (_controller.value * 2 * math.pi) + (index * math.pi / 2);
              double v = (math.sin(t) + 1) / 2; // 0.0 to 1.0

              return Container(
                margin: const EdgeInsets.symmetric(horizontal: 6),
                width: 12,
                height: 30 + (40 * v), // height varies from 30 to 70
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.3 + (0.7 * v)),
                  borderRadius: BorderRadius.circular(6),
                ),
              );
            }),
          );
        },
      ),
    );
  }
}
