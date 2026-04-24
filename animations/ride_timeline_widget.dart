import 'dart:async';
import 'package:flutter/material.dart';
import '../models/ride_item.dart';
import '../core/animation_constants.dart';
import 'animation_helpers.dart';

class RideTimelineWidget extends StatefulWidget {
  const RideTimelineWidget({
    super.key,
    required this.ride,
    this.isLastItem = false,
  });

  final RideItem ride;
  final bool isLastItem;

  @override
  State<RideTimelineWidget> createState() => _RideTimelineWidgetState();
}

class _RideTimelineWidgetState extends State<RideTimelineWidget>
    with TickerProviderStateMixin {

  // ── 6 animation controllers ────────────────────────────────────────────────
  late final AnimationController _entranceCtrl;   // slide+fade in
  late final AnimationController _progressCtrl;   // progress bar fill
  late final AnimationController _pulseCtrl;      // amber circle pulse
  late final AnimationController _monitorCtrl;    // monitor panel expand
  late final AnimationController _shakeCtrl;      // blocked card shake
  late final AnimationController _claimCtrl;      // claim card bounce
  late final AnimationController _disruptionCtrl; // disruption/blocked slide up
  late final AnimationController _bannerCtrl;     // claim banner slide up

  int _monitorTextStep = 0;
  Timer? _monitorTimer;

  @override
  void initState() {
    super.initState();

    _entranceCtrl = AnimationController(
      vsync: this,
      duration: ShieldAnimations.entranceDuration,
    );
    _progressCtrl = AnimationController(
      vsync: this,
      duration: ShieldAnimations.progressDemoDuration,
    );
    _pulseCtrl = AnimationController(
      vsync: this,
      duration: ShieldAnimations.pulseDuration,
    );
    _monitorCtrl = AnimationController(
      vsync: this,
      duration: ShieldAnimations.monitorExpandDur,
    );
    _shakeCtrl = AnimationController(
      vsync: this,
      duration: ShieldAnimations.shakeDuration,
    );
    _claimCtrl = AnimationController(
      vsync: this,
      duration: ShieldAnimations.claimBounceDur,
    );
    _disruptionCtrl = AnimationController(
      vsync: this,
      duration: ShieldAnimations.disruptionSlideDur,
    );
    _bannerCtrl = AnimationController(
      vsync: this,
      duration: ShieldAnimations.bannerSlideDur,
    );

    if (widget.ride.phase != RidePhase.hidden) {
      _playEntrance();
      _applyPhaseImmediate(widget.ride.phase);
    }
  }

  void _playEntrance() {
    Future.delayed(
      ShieldAnimations.staggerStepDelay * widget.ride.staggerIndex,
      () { if (mounted) _entranceCtrl.forward(); },
    );
  }

  /// Called on first appearance — no transition animation, just set final state.
  void _applyPhaseImmediate(RidePhase phase) {
    switch (phase) {
      case RidePhase.inProgress:
        _progressCtrl.forward();
        break;
      case RidePhase.completedMonitor:
        _progressCtrl.value = 1.0;
        _monitorCtrl.value = 1.0;
        _monitorTextStep = 3;
        break;
      case RidePhase.disruptionWarning:
        _disruptionCtrl.value = 1.0;
        _pulseCtrl.repeat(reverse: true);
        break;
      case RidePhase.blocked:
        _disruptionCtrl.value = 1.0;
        break;
      case RidePhase.claimTriggered:
        _disruptionCtrl.value = 1.0;
        _claimCtrl.value = 1.0;
        _bannerCtrl.value = 1.0;
        _monitorTextStep = 3;
        break;
      default:
        break;
    }
  }

  @override
  void didUpdateWidget(RideTimelineWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    final oldPhase = oldWidget.ride.phase;
    final newPhase = widget.ride.phase;

    // Entrance when moving from hidden
    if (oldPhase == RidePhase.hidden && newPhase != RidePhase.hidden) {
      _playEntrance();
    }

    // Phase transition animations
    if (oldPhase != newPhase) {
      _transitionToPhase(newPhase);
    }
  }

  void _transitionToPhase(RidePhase phase) {
    switch (phase) {
      case RidePhase.inProgress:
        _progressCtrl.forward();
        break;

      case RidePhase.completedMonitor:
        // Fill bar to 100% → expand monitor → sequential text
        _progressCtrl
            .animateTo(1.0, duration: const Duration(milliseconds: 400))
            .then((_) {
          if (!mounted) return;
          _monitorCtrl.forward().then((_) {
            if (!mounted) return;
            _startMonitorTextSequence();
          });
        });
        break;

      case RidePhase.queued:
        // Circle color change handled by AnimatedContainer — no extra ctrl needed
        break;

      case RidePhase.disruptionWarning:
        // Amber pulse starts, disruption card slides up
        _pulseCtrl.repeat(reverse: true);
        Future.delayed(const Duration(milliseconds: 100), () {
          if (mounted) _disruptionCtrl.forward();
        });
        break;

      case RidePhase.blocked:
        // Stop pulse, show blocked card, shake it
        _pulseCtrl
          ..stop()
          ..value = 0;
        Future.delayed(const Duration(milliseconds: 150), () {
          if (!mounted) return;
          _shakeCtrl.forward(from: 0);
        });
        break;

      case RidePhase.claimTriggered:
        // Reset shake, bounce claim card in, slide up banner
        _shakeCtrl.reset();
        Future.delayed(const Duration(milliseconds: 100), () {
          if (mounted) _claimCtrl.forward();
        });
        Future.delayed(const Duration(milliseconds: 350), () {
          if (mounted) _bannerCtrl.forward();
        });
        break;

      default:
        break;
    }
  }

  void _startMonitorTextSequence() {
    _monitorTimer?.cancel();
    setState(() => _monitorTextStep = 1);
    _monitorTimer = Timer.periodic(ShieldAnimations.monitorTextStep, (t) {
      if (!mounted) { t.cancel(); return; }
      setState(() => _monitorTextStep++);
      if (_monitorTextStep >= 3) t.cancel();
    });
  }

  @override
  void dispose() {
    _entranceCtrl.dispose();
    _progressCtrl.dispose();
    _pulseCtrl.dispose();
    _monitorCtrl.dispose();
    _shakeCtrl.dispose();
    _claimCtrl.dispose();
    _disruptionCtrl.dispose();
    _bannerCtrl.dispose();
    _monitorTimer?.cancel();
    super.dispose();
  }

  // ── Build ──────────────────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    if (widget.ride.phase == RidePhase.hidden) return const SizedBox.shrink();

    return SlideTransition(
      position: Tween<Offset>(
        begin: const Offset(0, 0.3),
        end: Offset.zero,
      ).animate(CurvedAnimation(
        parent: _entranceCtrl,
        curve: ShieldAnimations.entranceCurve,
      )),
      child: FadeTransition(
        opacity: _entranceCtrl,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _LeftColumn(
              ride: widget.ride,
              isLastItem: widget.isLastItem,
              pulseCtrl: _pulseCtrl,
            ),
            const SizedBox(width: 10),
            Expanded(child: _buildRightColumn()),
          ],
        ),
      ),
    );
  }

  Widget _buildRightColumn() {
    final ride = widget.ride;
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Header row ────────────────────────────────────────────────────
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                ride.phase == RidePhase.blocked ? '${ride.id} blocked' : ride.id,
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: Colors.white,
                ),
              ),
              AnimatedDefaultTextStyle(
                duration: ShieldAnimations.circleColorDur,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: ride.isNegativeAmount
                      ? const Color(0xFFf87171)
                      : const Color(0xFF4ade80),
                ),
                child: Text(
                  ride.isNegativeAmount
                      ? '−₹${ride.displayAmount.abs().toStringAsFixed(0)}'
                      : '+₹${ride.earnedAmount.toStringAsFixed(0)}',
                ),
              ),
            ],
          ),
          const SizedBox(height: 2),

          // ── Subtitle ──────────────────────────────────────────────────────
          Text(
            '${ride.fromZone} → ${ride.toZone} · ${ride.timeLabel}',
            style: const TextStyle(fontSize: 11, color: Color(0xFF6b7280)),
          ),
          const SizedBox(height: 5),

          // ── Progress bar (inProgress phase) ──────────────────────────────
          if (ride.showProgressBar)
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: AnimatedBuilder(
                animation: _progressCtrl,
                builder: (_, __) => ClipRRect(
                  borderRadius: BorderRadius.circular(2),
                  child: LinearProgressIndicator(
                    value: _progressCtrl.value,
                    minHeight: 4,
                    backgroundColor: const Color(0xFF1f2937),
                    valueColor:
                        const AlwaysStoppedAnimation(Color(0xFF16a34a)),
                  ),
                ),
              ),
            ),

          // ── Monitor panel (completedMonitor phase) ────────────────────────
          MonitorBridge(
            controller: _monitorCtrl,
            monitorContent: ride.showMonitorPanel
                ? _MonitorPanel(textStep: _monitorTextStep)
                : const SizedBox.shrink(),
          ),

          // ── Disruption card ───────────────────────────────────────────────
          if (ride.showDisruptionCard)
            SlideUpTransition(
              controller: _disruptionCtrl,
              curve: ShieldAnimations.disruptionCurve,
              child: _DisruptionCard(ride: ride),
            ),

          // ── Blocked card with shake ───────────────────────────────────────
          if (ride.showBlockedCard)
            ShakeTransition(
              controller: _shakeCtrl,
              child: SlideUpTransition(
                controller: _disruptionCtrl,
                child: _BlockedCard(ride: ride),
              ),
            ),

          // ── Claim card with bounce ────────────────────────────────────────
          if (ride.showClaimCard)
            BounceInTransition(
              controller: _claimCtrl,
              child: _ClaimCard(ride: ride),
            ),
        ],
      ),
    );
  }
}

// ── Left column: circle + vertical line ───────────────────────────────────────

class _LeftColumn extends StatelessWidget {
  const _LeftColumn({
    required this.ride,
    required this.isLastItem,
    required this.pulseCtrl,
  });

  final RideItem ride;
  final bool isLastItem;
  final AnimationController pulseCtrl;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 40,
      child: Column(
        children: [
          _CircleNode(ride: ride, pulseCtrl: pulseCtrl),
          if (!isLastItem)
            Padding(
              padding: const EdgeInsets.only(top: 2),
              child: AnimatedContainer(
                duration: ShieldAnimations.circleColorDur,
                width: 2,
                height: 44,
                decoration: BoxDecoration(
                  color: ride.lineColor(),
                  borderRadius: BorderRadius.circular(1),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _CircleNode extends StatelessWidget {
  const _CircleNode({required this.ride, required this.pulseCtrl});

  final RideItem ride;
  final AnimationController pulseCtrl;

  @override
  Widget build(BuildContext context) {
    final isAmber = ride.isAmberPulsing;

    return AnimatedBuilder(
      animation: pulseCtrl,
      builder: (_, child) {
        final opacity = isAmber
            ? (0.4 + 0.6 * (1 - pulseCtrl.value)).clamp(0.0, 1.0)
            : 1.0;
        return Opacity(opacity: opacity, child: child);
      },
      child: AnimatedContainer(
        duration: ShieldAnimations.circleColorDur,
        width: 32,
        height: 32,
        decoration: BoxDecoration(
          color: ride.circleColor().withOpacity(0.18),
          shape: BoxShape.circle,
          border: Border.all(color: ride.circleColor(), width: 1.8),
        ),
        child: Center(child: _circleIcon()),
      ),
    );
  }

  Widget _circleIcon() {
    switch (ride.phase) {
      case RidePhase.completedMonitor:
      case RidePhase.queued:
        return Icon(Icons.check, size: 14, color: ride.circleTextColor());
      case RidePhase.claimTriggered:
        return Icon(Icons.shield, size: 14, color: ride.circleTextColor());
      case RidePhase.blocked:
        return Icon(Icons.close, size: 14, color: ride.circleTextColor());
      default:
        return Text(
          ride.id,
          style: TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w700,
            color: ride.circleTextColor(),
          ),
        );
    }
  }
}

// ── Sub-widgets ────────────────────────────────────────────────────────────────

class _MonitorPanel extends StatelessWidget {
  const _MonitorPanel({required this.textStep});
  final int textStep;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 4),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFF1a1d27),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF1f2937)),
      ),
      child: Column(
        children: [
          _mRow(
            textStep == 0 ? 'Analysing telemetry...' : 'Risk score',
            textStep == 0 ? '' : 'LOW · clear',
            visible: true,
          ),
          AnimatedOpacity(
            opacity: textStep >= 2 ? 1.0 : 0.0,
            duration: ShieldAnimations.monitorTextFade,
            child: _mRow('Orders', 'Normal rate', visible: true),
          ),
          AnimatedOpacity(
            opacity: textStep >= 3 ? 1.0 : 0.0,
            duration: ShieldAnimations.monitorTextFade,
            child: _mRow('GPS', 'Consistent', visible: true),
          ),
        ],
      ),
    );
  }

  Widget _mRow(String label, String value, {required bool visible}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 1.5),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          AnimatedSwitcher(
            duration: ShieldAnimations.monitorTextFade,
            child: Text(
              label,
              key: ValueKey(label),
              style: const TextStyle(fontSize: 11, color: Color(0xFF6b7280)),
            ),
          ),
          Text(
            value,
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w500,
              color: Color(0xFFd1fae5),
            ),
          ),
        ],
      ),
    );
  }
}

class _DisruptionCard extends StatelessWidget {
  const _DisruptionCard({required this.ride});
  final RideItem ride;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 4),
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: const Color(0xFF2d1f06),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF92400e)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            ride.disruptionType ?? 'Disruption detected',
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: Color(0xFFfbbf24),
            ),
          ),
          const SizedBox(height: 4),
          _dRow('Area', ride.disruptionArea ?? '—'),
          _dRow('Deliveries', ride.deliveriesImpact ?? '—'),
          _dRow('Duration', ride.disruptionDuration ?? '—'),
          _dRow('Protection', ride.protectionStatus ?? 'Active'),
        ],
      ),
    );
  }

  Widget _dRow(String l, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 1.5),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(l, style: const TextStyle(fontSize: 10, color: Color(0xFF9ca3af))),
            Text(v,
                style: const TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w500,
                    color: Color(0xFFfde68a))),
          ],
        ),
      );
}

class _BlockedCard extends StatelessWidget {
  const _BlockedCard({required this.ride});
  final RideItem ride;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(top: 4, bottom: 4),
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: const Color(0xFF2d1515),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF7f1d1d)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '${ride.id} blocked',
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: Color(0xFFf87171),
            ),
          ),
          const SizedBox(height: 2),
          const Text(
            'Blocked due to rain · Income loss detected',
            style: TextStyle(fontSize: 10, color: Color(0xFFfca5a5)),
          ),
        ],
      ),
    );
  }
}

class _ClaimCard extends StatelessWidget {
  const _ClaimCard({required this.ride});
  final RideItem ride;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(top: 4),
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: const Color(0xFF0f2d1e),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF166534)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Claim auto-triggered · ${ride.claimTime ?? "—"}',
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: Color(0xFF4ade80),
            ),
          ),
          const SizedBox(height: 2),
          Text(
            '₹${ride.payoutAmount?.toStringAsFixed(0) ?? "—"} income protection coming to you',
            style: const TextStyle(fontSize: 10, color: Color(0xFF86efac)),
          ),
        ],
      ),
    );
  }
}
