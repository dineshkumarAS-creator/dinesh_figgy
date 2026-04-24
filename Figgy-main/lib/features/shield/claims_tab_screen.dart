import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:figgy_app/features/shield/screens/claims_screen.dart';
import 'package:figgy_app/features/shield/shield_theme.dart';

/// Main-tab Claims list (mudiayalaba “Claims” pane).
class ClaimsTabScreen extends StatelessWidget {
  const ClaimsTabScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                Color(0xFFF8FAFC),
                Color(0xFFF1F5F9),
                Color(0xFFFFF7ED),
                Color(0xFFF0FDF4),
              ],
              stops: [0.0, 0.3, 0.7, 1.0],
            ),
          ),
        ),
        Positioned(
          top: -50,
          right: -50,
          child: Container(
            width: 400,
            height: 400,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(
                colors: [
                  ShieldColors.primary.withOpacity(0.06),
                  ShieldColors.primary.withOpacity(0),
                ],
              ),
            ),
          ),
        ),
        Positioned.fill(
          child: Scaffold(
          backgroundColor: Colors.transparent,
          extendBodyBehindAppBar: true,
          appBar: AppBar(
            backgroundColor: Colors.white.withOpacity(0.4),
            surfaceTintColor: Colors.transparent,
            elevation: 0,
            automaticallyImplyLeading: false,
            flexibleSpace: ClipRRect(
              child: BackdropFilter(
                filter: ImageFilter.blur(sigmaX: 15, sigmaY: 15),
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 800),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      child: NavigationToolbar(
                        leading: IconButton(onPressed: () {}, icon: const Icon(Icons.menu, color: Colors.black)),
                        middle: const Text(
                          'Your Claims',
                          style: TextStyle(color: Colors.black, fontWeight: FontWeight.w900, fontSize: 20, letterSpacing: -0.5),
                        ),
                        trailing: IconButton(onPressed: () {}, icon: const Icon(Icons.notifications_none, color: Colors.black)),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
          body: const SafeArea(
            child: ClaimsScreen(),
          ),
        ),
        ),
      ],
    );
  }
}
