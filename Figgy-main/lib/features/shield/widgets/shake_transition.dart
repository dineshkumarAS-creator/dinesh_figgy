import 'package:flutter/material.dart';
import 'dart:math' as math;

class ShakeTransition extends StatelessWidget {
  final Widget child;
  final Animation<double> animation;

  const ShakeTransition({
    super.key,
    required this.child,
    required this.animation,
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: animation,
      builder: (context, child) {
        final double t = animation.value;
        // sine-curve, 300ms, sin(t × π × 6) × (1-t) × 4px
        final double offset = math.sin(t * math.pi * 6) * (1 - t) * 4;
        return Transform.translate(
          offset: Offset(offset, 0),
          child: child,
        );
      },
      child: child,
    );
  }
}
