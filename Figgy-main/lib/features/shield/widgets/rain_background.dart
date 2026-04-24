import 'dart:math';
import 'package:flutter/material.dart';

class RainBackground extends StatefulWidget {
  final bool isActive;
  const RainBackground({super.key, required this.isActive});

  @override
  State<RainBackground> createState() => _RainBackgroundState();
}

class _RainBackgroundState extends State<RainBackground> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  final List<Drop> _drops = List.generate(40, (index) => Drop());

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(vsync: this, duration: const Duration(seconds: 1))..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.isActive) return const SizedBox.shrink();

    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        for (var drop in _drops) {
          drop.update();
        }
        return CustomPaint(
          painter: RainPainter(drops: _drops),
          size: Size.infinite,
        );
      },
    );
  }
}

class Drop {
  double x = Random().nextDouble();
  double y = Random().nextDouble();
  double speed = 0.01 + Random().nextDouble() * 0.02;
  double length = 10 + Random().nextDouble() * 15;

  void update() {
    y += speed;
    if (y > 1.0) {
      y = -0.1;
      x = Random().nextDouble();
    }
  }
}

class RainPainter extends CustomPainter {
  final List<Drop> drops;
  RainPainter({required this.drops});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.blue.withOpacity(0.2)
      ..strokeWidth = 1.5
      ..strokeCap = StrokeCap.round;

    for (var drop in drops) {
      final start = Offset(drop.x * size.width, drop.y * size.height);
      final end = Offset(drop.x * size.width, drop.y * size.height + drop.length);
      canvas.drawLine(start, end, paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}
