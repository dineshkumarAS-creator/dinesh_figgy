import 'dart:math';
import 'package:flutter/material.dart';
import '../core/animation_constants.dart';

/// Shakes child horizontally with sine-decay curve.
/// Use when a ride is blocked — shakeCtrl.forward(from: 0) triggers it.
class ShakeTransition extends StatelessWidget {
  const ShakeTransition({
    super.key,
    required this.controller,
    required this.child,
  });

  final AnimationController controller;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (_, child) {
        // sin(t * pi * 6) * (1-t) * 4px — decaying shake
        final t = controller.value;
        final dx = sin(t * pi * 6) * (1 - t) * 4.0;
        return Transform.translate(offset: Offset(dx, 0), child: child);
      },
      child: child,
    );
  }
}

/// Expands vertically to reveal monitor panel after ride completion.
class MonitorBridge extends StatelessWidget {
  const MonitorBridge({
    super.key,
    required this.controller,
    required this.monitorContent,
  });

  final AnimationController controller;
  final Widget monitorContent;

  @override
  Widget build(BuildContext context) {
    return SizeTransition(
      axis: Axis.vertical,
      axisAlignment: -1.0,
      sizeFactor: CurvedAnimation(
        parent: controller,
        curve: ShieldAnimations.monitorCurve,
      ),
      child: monitorContent,
    );
  }
}

/// Slides child up from below with easeOutBack spring feel.
class SlideUpTransition extends StatelessWidget {
  const SlideUpTransition({
    super.key,
    required this.controller,
    required this.child,
    this.curve = Curves.easeOutBack,
  });

  final AnimationController controller;
  final Widget child;
  final Curve curve;

  @override
  Widget build(BuildContext context) {
    return SlideTransition(
      position: Tween<Offset>(
        begin: const Offset(0, 0.4),
        end: Offset.zero,
      ).animate(CurvedAnimation(parent: controller, curve: curve)),
      child: FadeTransition(
        opacity: CurvedAnimation(parent: controller, curve: Curves.easeOut),
        child: child,
      ),
    );
  }
}

/// Bounces child in: scale 0.8→1.0 + fade, elasticOut curve.
class BounceInTransition extends StatelessWidget {
  const BounceInTransition({
    super.key,
    required this.controller,
    required this.child,
  });

  final AnimationController controller;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return ScaleTransition(
      scale: Tween<double>(begin: 0.8, end: 1.0).animate(
        CurvedAnimation(
          parent: controller,
          curve: ShieldAnimations.claimBounceCurve,
        ),
      ),
      child: FadeTransition(
        opacity: CurvedAnimation(parent: controller, curve: Curves.easeOut),
        child: child,
      ),
    );
  }
}
