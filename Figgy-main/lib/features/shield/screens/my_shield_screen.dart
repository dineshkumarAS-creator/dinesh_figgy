import 'package:flutter/material.dart';
import '../widgets/alert_cards.dart';
import '../widgets/summary_card.dart';
import '../widgets/shake_transition.dart';
import '../core/simulation_controller.dart';
import 'package:figgy_app/core/ride_sync_controller.dart';

class MyShieldScreenContent extends StatefulWidget {
  const MyShieldScreenContent({super.key});

  @override
  State<MyShieldScreenContent> createState() => _MyShieldScreenContentState();
}

class _MyShieldScreenContentState extends State<MyShieldScreenContent> with TickerProviderStateMixin {
  late AnimationController _pulseCtrl;
  late AnimationController _shakeCtrl;
  late AnimationController _claimCtrl;

  // Ride data
  static const List<Map<String, dynamic>> _rides = [
    {'num': 1, 'route': 'Nungambakkam → Anna Nagar',   'time': '9:10 AM',  'earn': '+₹80'},
    {'num': 2, 'route': 'Anna Nagar → Velachery',       'time': '10:05 AM', 'earn': '+₹120'},
    {'num': 3, 'route': 'Velachery → T Nagar',           'time': '10:58 AM', 'earn': '+₹100'},
    {'num': 4, 'route': 'T Nagar → Mylapore',            'time': '11:30 AM', 'earn': '+₹90'},
    {'num': 5, 'route': 'Mylapore → Adyar',              'time': '1:40 PM',  'earn': '-₹300'},
  ];

  @override
  void initState() {
    super.initState();
    _pulseCtrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 1200));
    _shakeCtrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 400));
    _claimCtrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 600));

    RideSyncController.instance.addListener(_onSync);
  }

  void _onSync() {
    if (!mounted) return;
    final sync = RideSyncController.instance;
    setState(() {});

    if (sync.currentRideIndex == 4 && !_pulseCtrl.isAnimating) {
      _pulseCtrl.repeat(reverse: true);
    }
    if (sync.currentRideIndex == 5 && !_shakeCtrl.isAnimating) {
      _shakeCtrl.repeat(reverse: true); // Shake repeatedly while blocked
    }
    if (sync.currentRideIndex > 5) {
      _shakeCtrl.stop();
      if (_claimCtrl.value == 0) {
        _pulseCtrl.stop();
        _claimCtrl.forward();
      }
    }
  }

  @override
  void dispose() {
    RideSyncController.instance.removeListener(_onSync);
    _pulseCtrl.dispose();
    _shakeCtrl.dispose();
    _claimCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final sync = RideSyncController.instance;
    final currentIdx = sync.currentRideIndex;
    final progress = sync.rideProgress;

    return Stack(
      children: [
        SingleChildScrollView(
          physics: const BouncingScrollPhysics(),
          child: Column(
            children: [
              const SizedBox(height: 16),
              _buildPlanCard(),

              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      "TODAY'S RIDES — LIVE",
                      style: TextStyle(color: Color(0xFF6B7280), letterSpacing: 1.2, fontWeight: FontWeight.w600, fontSize: 11),
                    ),
                    const SizedBox(height: 20),

                    // Build each ride
                    for (int i = 0; i < _rides.length; i++)
                      if (currentIdx >= _rides[i]['num'])
                        _buildRideNode(i, currentIdx, progress),

                    // Disruption card after Ride 4
                    if (currentIdx >= 4)
                      _buildRevealWrapper(
                        key: const ValueKey('disruption_card'),
                        child: _buildDisruptionCard(),
                      ),

                    // Blocked card after Ride 5
                    if (currentIdx >= 5)
                      _buildRevealWrapper(
                        key: const ValueKey('blocked_card'),
                        child: _buildBlockedCard(),
                      ),

                    // Claim card
                    if (currentIdx > 5)
                      _buildRevealWrapper(
                        key: const ValueKey('claim_card'),
                        child: _buildClaimCard(),
                      ),
                  ],
                ),
              ),

              if (currentIdx > 5) SummaryCard(mode: DemoDisruption.rain),
              const ManualFileButton(),
              const SizedBox(height: 100),
            ],
          ),
        ),

        // Bottom green banner
        if (currentIdx > 5)
          Positioned(
            bottom: 0, left: 0, right: 0,
            child: SlideTransition(
              position: Tween<Offset>(begin: const Offset(0, 1), end: Offset.zero).animate(
                CurvedAnimation(parent: _claimCtrl, curve: Curves.easeOutCubic),
              ),
              child: _buildBottomBanner(),
            ),
          ),
      ],
    );
  }

  // ──────────────────────────────────────────────
  // SINGLE RIDE NODE (circle + line + progress)
  // ──────────────────────────────────────────────
  Widget _buildRideNode(int rideIdx, int currentIdx, double progress) {
    final ride = _rides[rideIdx];
    final rideNum = ride['num'] as int;
    final route = ride['route'] as String;
    final time = ride['time'] as String;
    final earn = ride['earn'] as String;

    final bool isCompleted = currentIdx > rideNum;
    final bool isActive = currentIdx == rideNum;
    final bool isBlocked = rideNum == 5;
    final bool isRainWarning = rideNum == 4 && (isActive || currentIdx == 4);
    final bool isLast = rideIdx == _rides.length - 1;

    // Circle colors
    Color circleBg, circleText, circleBorder;
    if (isBlocked && !isCompleted) {
      circleBg = const Color(0xFFFEE2E2);
      circleText = const Color(0xFFEF4444);
      circleBorder = const Color(0xFFEF4444).withOpacity(0.4);
    } else if (isActive && !isBlocked) {
      circleBg = isRainWarning ? const Color(0xFFEA580C) : const Color(0xFF3B82F6);
      circleBorder = isRainWarning ? const Color(0xFFEA580C) : const Color(0xFF3B82F6);
      circleText = Colors.white;
    } else if (isCompleted) {
      circleBg = const Color(0xFFF0FDF4);
      circleText = const Color(0xFF16A34A);
      circleBorder = const Color(0xFF16A34A).withOpacity(0.4);
    } else {
      circleBg = const Color(0xFFF0FDF4);
      circleText = const Color(0xFF16A34A);
      circleBorder = const Color(0xFF16A34A).withOpacity(0.4);
    }

    // Amount color
    Color amountColor = earn.startsWith('-') ? const Color(0xFFEF4444) : const Color(0xFF1A1A1A);

    Widget circleWidget = Container(
      width: 36,
      height: 36,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: circleBg,
        border: Border.all(color: circleBorder, width: 1.5),
      ),
      child: Center(
        child: Text(
          '$rideNum',
          style: TextStyle(color: circleText, fontWeight: FontWeight.w900, fontSize: 14),
        ),
      ),
    );

    // Pulse for Ride 4
    if (isRainWarning && !isCompleted) {
      circleWidget = AnimatedBuilder(
        animation: _pulseCtrl,
        child: circleWidget,
        builder: (_, childWidget) => Transform.scale(
          scale: 1.0 + (_pulseCtrl.value * 0.15),
          child: childWidget,
        ),
      );
    }

    // Build the connector line widget
    Widget connectorLine = const SizedBox(height: 16); // padding for the last item
    if (!isLast || (isLast && currentIdx > rideNum)) {
      connectorLine = AnimatedBuilder(
        animation: RideSyncController.instance,
        builder: (_, __) {
          final double rawProgress = RideSyncController.instance.rideProgress;
          final double safeProgress = (rawProgress.isNaN || rawProgress.isInfinite) ? 0.0 : rawProgress.clamp(0.0, 1.0);
          final double hFact = isCompleted ? 1.0 : (isActive ? safeProgress : 0.0);
          final lineColor = isCompleted ? const Color(0xFF16A34A) : (isBlocked ? const Color(0xFFEF4444) : (isRainWarning ? const Color(0xFFEA580C) : const Color(0xFF3B82F6)));
          
          return Container(
            width: 52,
            height: (isActive && !isBlocked) ? 60.0 : 36.0,
            alignment: Alignment.topCenter,
            child: Stack(
              alignment: Alignment.topCenter,
              children: [
                // Background track
                Container(
                  width: 3,
                  color: const Color(0xFFE5E7EB),
                ),
                // Animated fill
                Container(
                  width: 3,
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(2),
                    child: FractionallySizedBox(
                      heightFactor: hFact,
                      alignment: Alignment.topCenter,
                      child: Container(
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            begin: Alignment.topCenter, end: Alignment.bottomCenter,
                            colors: [lineColor.withOpacity(0.9), lineColor.withOpacity(0.1)],
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      );
    }

    Widget rideContent = Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // LEFT SIDE: Circle + Connector
        Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            circleWidget,
            connectorLine,
          ],
        ),
        
        // RIGHT SIDE: Content
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 6),
              Padding(
                padding: const EdgeInsets.only(left: 4),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Ride $rideNum${isBlocked && !isCompleted ? ' — Blocked' : ''}',
                            style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15, color: Color(0xFF1A1A1A)),
                          ),
                          const SizedBox(height: 3),
                          Text(
                            '$route · $time',
                            style: const TextStyle(color: Color(0xFF6B7280), fontSize: 11, fontWeight: FontWeight.w500),
                          ),
                        ],
                      ),
                    ),
                    if (isCompleted || (isBlocked && !isCompleted))
                      Padding(
                        padding: const EdgeInsets.only(right: 16),
                        child: Text(earn, style: TextStyle(color: amountColor, fontWeight: FontWeight.w800, fontSize: 15)),
                      ),
                  ],
                ),
              ),

              // Sub-content
              if (isActive && !isBlocked) ...[
                const SizedBox(height: 12),
                Padding(
                  padding: const EdgeInsets.only(left: 4),
                  child: _buildLiveProgress(isRainWarning),
                ),
              ],
              
              if (isCompleted && !isBlocked) ...[
                const SizedBox(height: 8),
                Padding(
                  padding: const EdgeInsets.only(left: 4),
                  child: Row(
                    children: [
                      Icon(Icons.check_circle, color: const Color(0xFF16A34A), size: 14),
                      const SizedBox(width: 6),
                      const Text('Completed', style: TextStyle(color: Color(0xFF16A34A), fontSize: 11, fontWeight: FontWeight.w600)),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ],
    );

    return _buildRevealWrapper(
      key: ValueKey('ride_node_$rideNum'),
      child: isBlocked && !isCompleted ? ShakeTransition(animation: _shakeCtrl, child: rideContent) : rideContent,
    );
  }

  Widget _buildRevealWrapper({required Key key, required Widget child}) {
    return KeyedSubtree(
      key: key,
      child: AnimatedSize(
        duration: const Duration(milliseconds: 600),
        curve: Curves.easeOutQuart,
        child: TweenAnimationBuilder<double>(
          tween: Tween(begin: 0.0, end: 1.0),
          duration: const Duration(milliseconds: 800),
          curve: Curves.easeOutBack,
          builder: (context, value, child) {
            return Opacity(
              opacity: value,
              child: Transform.translate(
                offset: Offset(0, 20 * (1.0 - value)),
                child: child,
              ),
            );
          },
          child: child,
        ),
      ),
    );
  }

  Widget _buildLiveProgress(bool isRainWarning) {
    return Padding(
      padding: const EdgeInsets.only(right: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(width: 6, height: 6, decoration: BoxDecoration(shape: BoxShape.circle, color: isRainWarning ? const Color(0xFFEA580C) : const Color(0xFF3B82F6))),
              const SizedBox(width: 8),
              Text(
                isRainWarning ? 'Heavy rain nearby — monitoring...' : 'Analysing telemetry...',
                style: TextStyle(color: isRainWarning ? const Color(0xFFEA580C) : const Color(0xFF3B82F6), fontSize: 11, fontWeight: FontWeight.w700),
              ),
            ],
          ),
          const SizedBox(height: 8),
          AnimatedBuilder(
            animation: RideSyncController.instance,
            builder: (_, __) => Container(
              height: 6, width: double.infinity,
              decoration: BoxDecoration(color: isRainWarning ? const Color(0xFFFFF7ED) : const Color(0xFFEFF6FF), borderRadius: BorderRadius.circular(10)),
              child: FractionallySizedBox(
                alignment: Alignment.centerLeft,
                widthFactor: ((RideSyncController.instance.rideProgress.isNaN || RideSyncController.instance.rideProgress.isInfinite) 
                    ? 0.0 
                    : RideSyncController.instance.rideProgress).clamp(0.0, 1.0),
                child: Container(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(colors: isRainWarning ? [const Color(0xFFEA580C), const Color(0xFFF59E0B)] : [const Color(0xFF3B82F6), const Color(0xFF16A34A)]),
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );



  }

  // ──────────────────────────────────────────────
  // DISRUPTION CARD
  // ──────────────────────────────────────────────
  Widget _buildDisruptionCard() {
    return Padding(
      padding: const EdgeInsets.only(left: 52, bottom: 16, right: 8),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: const Color(0xFFF0F9FF),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: const Color(0xFFBAE6FD).withOpacity(0.8)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.thunderstorm_rounded, color: Colors.blue.shade600, size: 18),
                const SizedBox(width: 8),
                const Text('Heavy Rain Detected', style: TextStyle(color: Color(0xFF0369A1), fontWeight: FontWeight.w800, fontSize: 13)),
              ],
            ),
            const SizedBox(height: 10),
            const Text('Area: T Nagar · Deliveries slowing — orders dropped 80%',
                style: TextStyle(color: Color(0xFF0369A1), fontSize: 11, fontWeight: FontWeight.w500, height: 1.5)),
            const SizedBox(height: 10),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: const [
                Text('Duration: 2 hrs 15 min', style: TextStyle(color: Color(0xFF6B7280), fontSize: 10, fontWeight: FontWeight.w500)),
                Text('Protection: Active', style: TextStyle(color: Color(0xFF059669), fontSize: 10, fontWeight: FontWeight.bold)),
              ],
            ),
          ],
        ),
      ),
    );
  }

  // ──────────────────────────────────────────────
  // BLOCKED CARD (Ride 5)
  // ──────────────────────────────────────────────
  Widget _buildBlockedCard() {
    return Padding(
      padding: const EdgeInsets.only(left: 52, bottom: 16, right: 8),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: const Color(0xFFFEF2F2),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: const Color(0xFFF87171).withOpacity(0.4)),
        ),
        child: Row(
          children: const [
            Icon(Icons.block_rounded, color: Color(0xFFEF4444), size: 18),
            SizedBox(width: 12),
            Expanded(
              child: Text(
                'Income loss detected\n-₹300 expected earnings lost',
                style: TextStyle(color: Color(0xFF991B1B), fontSize: 12, fontWeight: FontWeight.w700, height: 1.5),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ──────────────────────────────────────────────
  // CLAIM CARD
  // ──────────────────────────────────────────────
  Widget _buildClaimCard() {
    return ScaleTransition(
      scale: Tween<double>(begin: 0.8, end: 1.0).animate(
        CurvedAnimation(parent: _claimCtrl, curve: Curves.elasticOut),
      ),
      child: Padding(
        padding: const EdgeInsets.only(left: 12, bottom: 16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Shield icon with connector
            SizedBox(
              width: 52,
              child: Column(
                children: [
                  Container(
                    width: 36, height: 36,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: const Color(0xFFFEF3C7),
                      border: Border.all(color: const Color(0xFFE96A10).withOpacity(0.4), width: 1.5),
                    ),
                    child: const Center(
                      child: Icon(Icons.shield_rounded, color: Color(0xFFE96A10), size: 18),
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 6),
                  const Text('Claim auto-triggered', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15, color: Color(0xFF1A1A1A))),
                  const SizedBox(height: 3),
                  const Text('1:45 PM', style: TextStyle(color: Color(0xFF6B7280), fontSize: 11, fontWeight: FontWeight.w500)),
                  const SizedBox(height: 16),
                  const ClaimAlertCard(),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ──────────────────────────────────────────────
  // PLAN CARD
  // ──────────────────────────────────────────────
  Widget _buildPlanCard() {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 36),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: const Color(0xFFF9DDD0), width: 1.5),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.02), blurRadius: 10, offset: const Offset(0, 4))],
      ),
      child: Stack(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                        decoration: BoxDecoration(color: const Color(0xFFEA580C), borderRadius: BorderRadius.circular(20)),
                        child: const Text('Smart Plan', style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold)),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                        decoration: BoxDecoration(
                          color: const Color(0xFFF0FDF4),
                          border: Border.all(color: const Color(0xFF86EFAC).withOpacity(0.6)),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: const Text('active', style: TextStyle(color: Color(0xFF16A34A), fontSize: 12, fontWeight: FontWeight.bold)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  const Text('₹20/week · Renews Apr 9', style: TextStyle(color: Color(0xFF6B7280), fontSize: 14, fontWeight: FontWeight.w600)),
                ],
              ),
              const Icon(Icons.gpp_good_outlined, color: Color(0xFFE96A10), size: 30),
            ],
          ),
          Positioned(
            right: 0, top: 0,
            child: IconButton(
              icon: const Icon(Icons.refresh, color: Colors.grey, size: 22),
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(),
              onPressed: () {
                _pulseCtrl.reset();
                _shakeCtrl.reset();
                _claimCtrl.reset();
                RideSyncController.instance.reset();
              },
            ),
          ),
        ],
      ),
    );
  }

  bool _isClaimed = false;

  void _handleClaim() {
    setState(() {
      _isClaimed = true;
    });
    // Shake effect for celebration
    _shakeCtrl.forward(from: 0);
  }

  // ──────────────────────────────────────────────
  // BOTTOM BANNER
  // ──────────────────────────────────────────────
  Widget _buildBottomBanner() {
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 500),
      child: _isClaimed 
        ? _buildSuccessBanner()
        : Container(
            key: const ValueKey('claim_pending'),
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: const Color(0xFF22C55E),
              borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
              boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.1), blurRadius: 20, offset: const Offset(0, -5))],
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
                  InkWell(
                    onTap: _handleClaim,
                    borderRadius: BorderRadius.circular(12),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
                      child: const Text('Track', style: TextStyle(color: Color(0xFF16A34A), fontWeight: FontWeight.w900, fontSize: 15)),
                    ),
                  ),
                ],
              ),
            ),
          ),
    );
  }

  Widget _buildSuccessBanner() {
    return Container(
      key: const ValueKey('claim_success'),
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      decoration: BoxDecoration(
        color: const Color(0xFF15803D),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.2), blurRadius: 20, offset: const Offset(0, -5))],
      ),
      child: SafeArea(
        top: false,
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: const BoxDecoration(color: Colors.white24, shape: BoxShape.circle),
              child: const Icon(Icons.check_rounded, color: Colors.white, size: 24),
            ),
            const SizedBox(width: 16),
            const Expanded(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('COMPLETED', style: TextStyle(color: Colors.white70, fontSize: 10, fontWeight: FontWeight.w900, letterSpacing: 1.1)),
                  SizedBox(height: 2),
                  Text('₹198 successfully claimed', style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w800)),
                ],
              ),
            ),
            const Text('ID: #FGY9921', style: TextStyle(color: Colors.white54, fontSize: 10, fontWeight: FontWeight.w600)),
          ],
        ),
      ),
    );
  }
}

