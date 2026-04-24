import 'package:flutter/material.dart';
import 'dart:math' as math;
import '../widgets/timeline_feed.dart';
import '../widgets/alert_cards.dart';
import '../widgets/summary_card.dart';
import '../widgets/shake_transition.dart';
import '../core/simulation_controller.dart';

class MyShieldScreenContent extends StatefulWidget {
  const MyShieldScreenContent({super.key});

  @override
  State<MyShieldScreenContent> createState() => _MyShieldScreenContentState();
}

class _MyShieldScreenContentState extends State<MyShieldScreenContent> with TickerProviderStateMixin {
  int _simulationStep = 0;
  
  // Controllers as requested
  late AnimationController _progressCtrl;
  late AnimationController _pulseCtrl;
  late AnimationController _disruptionCtrl;
  late AnimationController _shakeCtrl;
  late AnimationController _claimCtrl;
  late AnimationController _entranceCtrl; // For initial rides

  @override
  void initState() {
    super.initState();
    
    _progressCtrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 1500));
    _pulseCtrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 1400));
    _disruptionCtrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 350));
    _shakeCtrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 300));
    _claimCtrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 500));
    _entranceCtrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 800));

    // Start simulation automatically for demo purposes
    _runSimulation();
  }

  Future<void> _runSimulation() async {
    // Stage 1: Ride 1 enters with blue circle
    setState(() => _simulationStep = 1);
    await Future.delayed(const Duration(milliseconds: 500));
    
    // Progress bar fills
    await _progressCtrl.forward();
    
    // Stage 2: Circle turns green, bridge expands, Rides 2 & 3 bounce in
    setState(() => _simulationStep = 2);
    _entranceCtrl.forward();
    await Future.delayed(const Duration(milliseconds: 1500));
    
    // Stage 3: Ride 4 enters gray
    setState(() => _simulationStep = 3);
    await Future.delayed(const Duration(milliseconds: 1000));
    
    // Stage 4: Circle turns amber and pulses, Disruption card slides up
    setState(() => _simulationStep = 4);
    _pulseCtrl.repeat(reverse: true);
    _disruptionCtrl.forward();
    await Future.delayed(const Duration(milliseconds: 2000));
    
    // Stage 5: Ride 5 circle turns red, amount flips, Blocked card shakes
    setState(() => _simulationStep = 5);
    await _shakeCtrl.forward();
    await Future.delayed(const Duration(milliseconds: 1500));
    
    // Stage 6: Claim auto-triggers, circle green, card bounces
    setState(() => _simulationStep = 6);
    _pulseCtrl.stop();
    _claimCtrl.forward();
  }

  @override
  void dispose() {
    _progressCtrl.dispose();
    _pulseCtrl.dispose();
    _disruptionCtrl.dispose();
    _shakeCtrl.dispose();
    _claimCtrl.dispose();
    _entranceCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    const d = DemoDisruption.rain;
    final meta = _disruptionMeta(d);

    return Stack(
      children: [
        SingleChildScrollView(
          physics: const BouncingScrollPhysics(),
          child: Column(
            children: [
              const SizedBox(height: 16),
              
              // Smart Plan Card
              _buildPlanCard(),

              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      "TODAY'S RIDES — APR 2",
                      style: TextStyle(color: Color(0xFF6B7280), letterSpacing: 1.2, fontWeight: FontWeight.w500, fontSize: 10),
                    ),
                    const SizedBox(height: 20),
                    
                    // Ride 1 (Animated)
                    _buildRide1(),

                    // Ride 2 & 3 (Staggered Entrance)
                    if (_simulationStep >= 2) ...[
                       _buildStaggeredRide(2, 'Ride 2', 'Koyambedu -> T Nagar · 10:05 AM', '+₹120', delay: 0),
                       _buildStaggeredRide(3, 'Ride 3', 'T Nagar -> Mylapore · 10:58 AM', '+₹100', delay: 120),
                    ],

                    if (_simulationStep >= 3) ...[
                      const SizedBox(height: 16),
                      _buildRide4(),
                    ],

                    if (_simulationStep >= 4)
                      _buildDisruptionSection(meta),
                    
                    if (_simulationStep >= 5) ...[
                      _buildRide5(),
                      const SizedBox(height: 8),
                    ],

                    if (_simulationStep >= 6)
                      _buildClaimSection(),
                  ],
                ),
              ),
              
              if (_simulationStep >= 6)
                SummaryCard(mode: d),
              
              const ManualFileButton(),
              const SizedBox(height: 100), 
            ],
          ),
        ),
        
        // Bottom Banner Slide-up
        if (_simulationStep >= 6)
          Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: SlideTransition(
              position: Tween<Offset>(begin: const Offset(0, 1), end: Offset.zero).animate(
                CurvedAnimation(parent: _claimCtrl, curve: Curves.easeOutCubic)
              ),
              child: _buildBottomBanner(),
            ),
          ),
        
        // Reset button for demo
        Positioned(
          top: 10,
          right: 10,
          child: IconButton(
            icon: const Icon(Icons.refresh, color: Colors.grey),
            onPressed: () {
              _progressCtrl.reset();
              _pulseCtrl.stop();
              _disruptionCtrl.reset();
              _shakeCtrl.reset();
              _claimCtrl.reset();
              _entranceCtrl.reset();
              _runSimulation();
            },
          ),
        ),
      ],
    );
  }

  Widget _buildPlanCard() {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 24),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: const Color(0xFFE96A10).withOpacity(0.15), width: 1),
        boxShadow: [
          BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 10, offset: const Offset(0, 4)),
        ],
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    decoration: BoxDecoration(
                      color: const Color(0xFFEA580C),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: const Text('Smart Plan', style: TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w800)),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF0FDF4),
                      border: Border.all(color: const Color(0xFF16A34A).withOpacity(0.3), width: 1),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: const Text('active', style: TextStyle(color: Color(0xFF16A34A), fontSize: 11, fontWeight: FontWeight.bold)),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              const Text('₹20/week · Renews Apr 9', style: TextStyle(color: Colors.black54, fontSize: 13, fontWeight: FontWeight.bold)),
            ],
          ),
          const Icon(Icons.verified_user_outlined, color: Color(0xFFE96A10), size: 28),
        ],
      ),
    );
  }

  Widget _buildRide1() {
    bool isDone = _simulationStep >= 2;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TimelineItem(
          icon: Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: isDone ? const Color(0xFFF0FDF4) : const Color(0xFFEFF6FF),
              border: Border.all(color: isDone ? const Color(0xFF16A34A).withOpacity(0.3) : const Color(0xFF3B82F6).withOpacity(0.3)),
            ),
            child: Center(
              child: Text(
                'R1', 
                style: TextStyle(
                  color: isDone ? const Color(0xFF16A34A) : const Color(0xFF3B82F6), 
                  fontWeight: FontWeight.w800, 
                  fontSize: 11
                )
              ),
            ),
          ),
          title: 'Ride 1',
          subtitle: 'Anna Nagar -> Vadapalani · 9:10 AM',
          amount: isDone ? '+₹80' : '',
          time: '',
          iconBg: Colors.transparent,
        ),
        AnimatedSize(
          duration: const Duration(milliseconds: 600),
          curve: Curves.easeOutQuart,
          child: _simulationStep == 1
            ? Padding(
                padding: const EdgeInsets.only(left: 48, right: 24, bottom: 24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Analysing telemetry...', style: TextStyle(color: Color(0xFF3B82F6), fontSize: 11, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 12),
                    AnimatedBuilder(
                      animation: _progressCtrl,
                      builder: (context, child) {
                        return Container(
                          height: 6,
                          width: double.infinity,
                          decoration: BoxDecoration(
                            color: const Color(0xFFEFF6FF),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: FractionallySizedBox(
                            alignment: Alignment.centerLeft,
                            widthFactor: _progressCtrl.value,
                            child: Container(
                              decoration: BoxDecoration(
                                color: const Color(0xFF16A34A),
                                borderRadius: BorderRadius.circular(10),
                              ),
                            ),
                          ),
                        );
                      },
                    ),
                  ],
                ),
              )
            : const SizedBox(width: double.infinity, height: 0),
        ),
      ],
    );
  }

  Widget _buildStaggeredRide(int step, String title, String sub, String amount, {required int delay}) {
    return AnimatedBuilder(
      animation: _entranceCtrl,
      builder: (context, child) {
        double t = (_entranceCtrl.value * 1000 - delay) / 500;
        t = t.clamp(0.0, 1.0);
        double curveT = Curves.elasticOut.transform(t);
        if (t <= 0) return const SizedBox.shrink();
        
        return Transform.scale(
          scale: curveT,
          child: Opacity(
            opacity: t.clamp(0.0, 1.0),
            child: TimelineItem(
              icon: Text('R$step', style: const TextStyle(color: Color(0xFF16A34A), fontWeight: FontWeight.w800, fontSize: 11)),
              title: title,
              subtitle: sub,
              amount: amount,
              time: '',
              iconBg: const Color(0xFFF0FDF4),
            ),
          ),
        );
      },
    );
  }

  Widget _buildRide4() {
    bool isPulsing = _simulationStep >= 4;
    return AnimatedBuilder(
      animation: _pulseCtrl,
      builder: (context, child) {
        double pulse = 1.0 + (_pulseCtrl.value * 0.1);
        Color circleColor = isPulsing ? const Color(0xFFFFF7ED) : const Color(0xFFF3F4F6);
        Color textColor = isPulsing ? const Color(0xFFEA580C) : const Color(0xFF6B7280);
        
        return TimelineItem(
          icon: Transform.scale(
            scale: isPulsing ? pulse : 1.0,
            child: Container(
              width: 28,
              height: 28,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: circleColor,
                border: Border.all(color: textColor.withOpacity(0.3)),
              ),
              child: Center(
                child: Text('R4', style: TextStyle(color: textColor, fontWeight: FontWeight.w800, fontSize: 11)),
              ),
            ),
          ),
          title: 'Ride 4',
          subtitle: 'Mylapore · 11:30 AM',
          amount: isPulsing ? '-₹300' : '',
          amountColor: const Color(0xFFEF4444),
          time: '',
          iconBg: Colors.transparent,
        );
      },
    );
  }

  Widget _buildDisruptionSection(_DisruptionCopy meta) {
    return SlideTransition(
      position: Tween<Offset>(begin: const Offset(0, 0.2), end: Offset.zero).animate(
        CurvedAnimation(parent: _disruptionCtrl, curve: Curves.easeOutBack)
      ),
      child: FadeTransition(
        opacity: _disruptionCtrl,
        child: Column(
          children: [
            TimelineItem(
              icon: Icon(meta.icon, color: meta.accent, size: 16),
              title: meta.headline,
              subtitle: '',
              amount: '',
              time: '11:30 AM',
              iconBg: const Color(0xFFE0F2FE),
            ),
            _wrapWithStem(
              DisruptionAlertCard(
                accent: meta.accent,
                areaLabel: meta.area,
                body: meta.detail,
                duration: meta.duration,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRide5() {
    bool isClaimed = _simulationStep >= 6;
    return ShakeTransition(
      animation: _shakeCtrl,
      child: Column(
        children: [
          TimelineItem(
            icon: Container(
              width: 28,
              height: 28,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: isClaimed ? const Color(0xFFF0FDF4) : const Color(0xFFFEE2E2),
                border: Border.all(color: isClaimed ? const Color(0xFF16A34A).withOpacity(0.3) : const Color(0xFFEF4444).withOpacity(0.3)),
              ),
              child: Center(
                child: Text('R5', style: TextStyle(color: isClaimed ? const Color(0xFF16A34A) : const Color(0xFFEF4444), fontWeight: FontWeight.w800, fontSize: 11)),
              ),
            ),
            title: 'Ride 5 blocked',
            subtitle: 'Blocked due to rain · 1:40 PM',
            amount: '-₹300',
            time: '',
            amountColor: const Color(0xFFEF4444),
            iconBg: Colors.transparent,
          ),
          _wrapWithStem(
            Container(
              margin: const EdgeInsets.only(bottom: 16, left: 12, right: 16),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFFFEF2F2),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFF87171).withOpacity(0.3)),
              ),
              child: const Row(
                children: [
                  Icon(Icons.error_outline, color: Color(0xFFEF4444), size: 16),
                  SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'Income loss detected\n-₹300 expected earnings lost',
                      style: TextStyle(color: Color(0xFF991B1B), fontSize: 12, fontWeight: FontWeight.bold, height: 1.4),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildClaimSection() {
    return Column(
      children: [
        const TimelineItem(
          icon: Icon(Icons.shield_outlined, color: Color(0xFFE96A10), size: 16),
          title: 'Claim auto-triggered',
          subtitle: '',
          amount: '',
          time: '1:45 PM',
          iconBg: Color(0xFFFEF3C7),
        ),
        ScaleTransition(
          scale: Tween<double>(begin: 0.8, end: 1.0).animate(
            CurvedAnimation(parent: _claimCtrl, curve: Curves.elasticOut)
          ),
          child: _wrapWithStem(const ClaimAlertCard(), isLast: true),
        ),
      ],
    );
  }

  Widget _buildBottomBanner() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF22C55E),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        boxShadow: [
          BoxShadow(color: Colors.black.withOpacity(0.1), blurRadius: 20, offset: const Offset(0, -5)),
        ],
      ),
      child: SafeArea(
        top: false,
        child: Row(
          children: [
            const Expanded(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Your income protection', style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w500)),
                  SizedBox(height: 4),
                  Text('₹198 coming to you', style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w900)),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Text('Track', style: TextStyle(color: Color(0xFF16A34A), fontWeight: FontWeight.bold)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _wrapWithStem(Widget child, {bool isLast = false}) {
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            width: 48,
            child: Column(
              children: [
                Expanded(
                  child: Container(
                    width: 1.2,
                    color: Colors.grey.withOpacity(0.15),
                  ),
                ),
                if (isLast) const SizedBox(height: 16),
              ],
            ),
          ),
          Expanded(child: child),
        ],
      ),
    );
  }

  _DisruptionCopy _disruptionMeta(DemoDisruption d) {
    return _DisruptionCopy(
      icon: Icons.lightbulb_outline, accent: Colors.blue.shade600,
      headline: 'Heavy rain detected', sub: 'In your active zone',
      time: '11:30 AM', area: 'T Nagar',
      detail: 'Deliveries Slowing · orders dropped 80%', duration: '2 hrs 15 min',
      blockReason: 'Blocked due to rain · Income loss detected',
    );
  }
}

class _DisruptionCopy {
  final IconData icon;
  final Color accent;
  final String headline;
  final String sub;
  final String time;
  final String area;
  final String detail;
  final String duration;
  final String blockReason;

  _DisruptionCopy({
    required this.icon, required this.accent, required this.headline, required this.sub,
    required this.time, required this.area, required this.detail, required this.duration,
    required this.blockReason,
  });
}
