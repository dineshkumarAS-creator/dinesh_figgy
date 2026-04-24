import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/simulation_controller.dart';
import '../models/ride_item.dart';
import '../widgets/ride_timeline_widget.dart';

class ShieldTimelineTabScreen extends StatefulWidget {
  const ShieldTimelineTabScreen({super.key});

  @override
  State<ShieldTimelineTabScreen> createState() =>
      _ShieldTimelineTabScreenState();
}

class _ShieldTimelineTabScreenState extends State<ShieldTimelineTabScreen>
    with SingleTickerProviderStateMixin {

  late final AnimationController _bannerCtrl;
  bool _bannerShown = false;

  @override
  void initState() {
    super.initState();
    _bannerCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
    );

    WidgetsBinding.instance.addPostFrameCallback((_) {
      final ctrl = context.read<SimulationController>();
      ctrl.addListener(_onControllerChange);
      ctrl.startDemoSequence();
    });
  }

  void _onControllerChange() {
    final step = context.read<SimulationController>().eventStep;
    if (step >= 7 && !_bannerShown) {
      _bannerShown = true;
      _bannerCtrl.forward();
    }
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    // safely remove listener even if context already disposed
    try {
      context.read<SimulationController>().removeListener(_onControllerChange);
    } catch (_) {}
    _bannerCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ctrl = context.watch<SimulationController>();
    final visibleRides =
        ctrl.rides.where((r) => r.phase != RidePhase.hidden).toList();

    return Scaffold(
      backgroundColor: const Color(0xFF0f1117),
      body: SafeArea(
        child: Column(
          children: [
            _AppBar(),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 12),
                    const _PolicyCard(),
                    const SizedBox(height: 16),
                    const Text(
                      "TODAY'S RIDES — APR 2",
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w500,
                        color: Color(0xFF6b7280),
                        letterSpacing: 0.5,
                      ),
                    ),
                    const SizedBox(height: 10),

                    // ── Ride list ────────────────────────────────────────────
                    ...List.generate(visibleRides.length, (i) {
                      return RideTimelineWidget(
                        key: ValueKey(visibleRides[i].id),
                        ride: visibleRides[i],
                        isLastItem: i == visibleRides.length - 1,
                      );
                    }),

                    const SizedBox(height: 8),

                    // ── Payout banner ────────────────────────────────────────
                    _PayoutBanner(
                      ctrl: ctrl,
                      bannerCtrl: _bannerCtrl,
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── AppBar ─────────────────────────────────────────────────────────────────────

class _AppBar extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 4, 0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          const Text(
            'figgy',
            style: TextStyle(
              color: Color(0xFFf97316),
              fontSize: 16,
              fontWeight: FontWeight.w800,
              letterSpacing: -0.5,
            ),
          ),
          const Text(
            'My Shield',
            style: TextStyle(
              color: Colors.white,
              fontSize: 15,
              fontWeight: FontWeight.w600,
            ),
          ),
          IconButton(
            icon: const Icon(
              Icons.notifications_outlined,
              color: Color(0xFF9ca3af),
              size: 20,
            ),
            onPressed: () {},
          ),
        ],
      ),
    );
  }
}

// ── Policy card ────────────────────────────────────────────────────────────────

class _PolicyCard extends StatelessWidget {
  const _PolicyCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFF1a1d27),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    _Chip('Smart Plan', const Color(0xFF1e3a2e), const Color(0xFF4ade80)),
                    const SizedBox(width: 6),
                    _Chip('Active', const Color(0xFF1c3a5e), const Color(0xFF60a5fa)),
                  ],
                ),
                const SizedBox(height: 4),
                const Text(
                  '₹20/week · Renews Apr 9',
                  style: TextStyle(fontSize: 11, color: Color(0xFF9ca3af)),
                ),
              ],
            ),
          ),
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              color: const Color(0xFF1e3a2e),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(
              Icons.shield_outlined,
              size: 16,
              color: Color(0xFF4ade80),
            ),
          ),
        ],
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip(this.label, this.bg, this.fg);
  final String label;
  final Color bg, fg;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        label,
        style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: fg),
      ),
    );
  }
}

// ── Payout banner ──────────────────────────────────────────────────────────────

class _PayoutBanner extends StatelessWidget {
  const _PayoutBanner({required this.ctrl, required this.bannerCtrl});
  final SimulationController ctrl;
  final AnimationController bannerCtrl;

  @override
  Widget build(BuildContext context) {
    if (ctrl.eventStep < 7) return const SizedBox.shrink();

    final claimRide = ctrl.rides.firstWhere(
      (r) => r.phase == RidePhase.claimTriggered,
      orElse: () => ctrl.rides.last,
    );

    return SlideTransition(
      position: Tween<Offset>(
        begin: const Offset(0, 0.5),
        end: Offset.zero,
      ).animate(CurvedAnimation(
        parent: bannerCtrl,
        curve: Curves.easeOutCubic,
      )),
      child: FadeTransition(
        opacity: bannerCtrl,
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: const Color(0xFF0f2d1e),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFF166534)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Your income protection',
                style: TextStyle(fontSize: 11, color: Color(0xFF9ca3af)),
              ),
              const SizedBox(height: 2),
              Text(
                '₹${claimRide.payoutAmount?.toStringAsFixed(0) ?? "198"} coming to you',
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF4ade80),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
