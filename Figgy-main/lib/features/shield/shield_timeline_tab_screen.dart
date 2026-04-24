import 'package:flutter/material.dart';
import 'screens/my_shield_screen.dart';

class ShieldTimelineTabScreen extends StatefulWidget {
  const ShieldTimelineTabScreen({super.key});

  @override
  State<ShieldTimelineTabScreen> createState() => _ShieldTimelineTabScreenState();
}

class _ShieldTimelineTabScreenState extends State<ShieldTimelineTabScreen> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFBFBF9), // Premium cream background
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        surfaceTintColor: Colors.transparent,
        automaticallyImplyLeading: false,
        centerTitle: false,
        titleSpacing: 16,
        title: Row(
          children: [
            const Text(
              'figgy',
              style: TextStyle(color: Color(0xFFE96A10), fontWeight: FontWeight.w900, fontSize: 22, letterSpacing: -0.5),
            ),
            const Expanded(
              child: Center(
                child: Text(
                  'My Shield',
                  style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold, fontSize: 18),
                ),
              ),
            ),
            // REMOVED THE SIMULATION TOGGLE BADGE
            Container(
              padding: const EdgeInsets.all(8),
              decoration: const BoxDecoration(
                color: Color(0xFFF1F5F9),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.notifications_none, color: Colors.blueGrey, size: 20),
            ),
          ],
        ),
      ),
      body: SingleChildScrollView(
        child: Center(
          child: ConstrainedBox(
            constraints: BoxConstraints(maxWidth: 800),
            child: MyShieldScreenContent(),
          ),
        ),
      ),
    );
  }
}
