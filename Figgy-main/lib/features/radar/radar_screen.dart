import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:figgy_app/theme/app_theme.dart';
import 'package:figgy_app/models/radar_summary.dart';
import 'package:shared_preferences/shared_preferences.dart';
// import removed

// ─────────────────────────────────────────────────────────────────────────
// RadarNotifier — State Management
// ─────────────────────────────────────────────────────────────────────────

class RadarNotifier extends ChangeNotifier {
  RadarSummary? _data;
  bool _isLoading = true;
  String? _error;
  DateTime? _lastFetch;
  Timer? _pollTimer;

  RadarSummary? get data => _data;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get isStale =>
      _lastFetch != null &&
      DateTime.now().difference(_lastFetch!) > const Duration(seconds: 90);

  final String workerId;

  RadarNotifier({required this.workerId});

  Future<void> fetchSummary() async {
    if (_isLoading && _data == null) {
      _isLoading = true;
      notifyListeners();
    }

    try {
      // TODO: Replace with actual API call
      // final response = await http.get(
      //   Uri.parse('http://localhost:5000/radar/summary?worker_id=$workerId'),
      // );
      // if (response.statusCode == 200) {
      //   _data = RadarSummary.fromJson(jsonDecode(response.body));
      // }

      // Mock data for MVP
      _data = _getMockRadarSummary();
      _lastFetch = DateTime.now();
      _error = null;
    } catch (e) {
      _error = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  void startPolling() {
    fetchSummary();
    _pollTimer = Timer.periodic(const Duration(seconds: 60), (_) {
      fetchSummary();
    });
  }

  void stopPolling() {
    _pollTimer?.cancel();
  }

  @override
  void dispose() {
    stopPolling();
    super.dispose();
  }

  RadarSummary _getMockRadarSummary() {
    return RadarSummary(
      alert: const RadarAlert(
          severity: 'Moderate',
          message:
              'Rain active in T Nagar. Zone C and A are clear — good to ride there now.'),
      zones: [
        const ZoneData(
          zoneId: 'C',
          zoneName: 'Adyar',
          zoneLetter: 'C',
          distanceKm: 3.2,
          etaMin: 8,
          orderCount: 12,
          boostInr: 180,
          riskScore: 14.0,
          riskLabel: 'Safe',
          primarySignal: 'none',
          alertText: 'No rain · Low traffic',
          opportunityIndex: 0.86,
          recommended: true,
        ),
        const ZoneData(
          zoneId: 'A',
          zoneName: 'Anna Nagar',
          zoneLetter: 'A',
          distanceKm: 1.8,
          etaMin: 5,
          orderCount: 9,
          boostInr: 90,
          riskScore: 25.0,
          riskLabel: 'Safe',
          primarySignal: 'none',
          alertText: 'Partly cloudy',
          opportunityIndex: 0.72,
          recommended: false,
        ),
        const ZoneData(
          zoneId: 'B',
          zoneName: 'T Nagar',
          zoneLetter: 'B',
          distanceKm: 0.0,
          etaMin: 0,
          orderCount: 5,
          boostInr: 50,
          riskScore: 55.0,
          riskLabel: 'Caution',
          primarySignal: 'rain',
          alertText: 'Rain active',
          opportunityIndex: 0.35,
          recommended: false,
        ),
        const ZoneData(
          zoneId: 'D',
          zoneName: 'Nungambakkam',
          zoneLetter: 'D',
          distanceKm: 4.1,
          etaMin: 11,
          orderCount: 2,
          boostInr: 0,
          riskScore: 75.0,
          riskLabel: 'Avoid',
          primarySignal: 'strike',
          alertText: 'Strike signal',
          opportunityIndex: 0.08,
          recommended: false,
        ),
      ],
      earningsToday: EarningsToday(
        earnedInr: 300.0,
        protectedInr: 498.0,
        ridesDone: 3,
        claimPending: ClaimPending(
          amountInr: 198.0,
          reason: 'rain disruption',
          claimId: 'FIG-ABC12345',
          status: 'pending',
        ),
      ),
      riderRisk: const RiderRisk(
        inRiskZone: true,
        zoneId: 'B',
        riskLabel: 'Caution',
        protectionAutoOn: true,
      ),
    );
  }
}

class RadarScreen extends StatefulWidget {
  const RadarScreen({super.key});

  @override
  State<RadarScreen> createState() => _RadarScreenState();
}

class _RadarScreenState extends State<RadarScreen>
    with WidgetsBindingObserver {
  late RadarNotifier _radarNotifier;
  late ScrollController _scrollController;
  String _workerZone = 'Central';
  String _policyStatus = 'active';
  int _selectedTab = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _scrollController = ScrollController();
    _radarNotifier = RadarNotifier(workerId: 'worker_123');
    _radarNotifier.startPolling();
    _initData();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _radarNotifier.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _radarNotifier.startPolling();
    } else if (state == AppLifecycleState.paused) {
      _radarNotifier.stopPolling();
    }
  }

  Future<void> _initData() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _workerZone = prefs.getString('zone') ?? 'Central';
      _policyStatus = prefs.getString('policy_status') ?? 'active';
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        scrolledUnderElevation: 0,
        leadingWidth: 100,
        leading: Padding(
          padding: const EdgeInsets.only(left: 20.0),
          child: Center(
            child: Text(
              'figgy',
              style: AppTypography.h2.copyWith(
                color: AppColors.brandPrimary,
                fontWeight: FontWeight.w900,
                fontSize: 24,
              ),
            ),
          ),
        ),
        title: Text(
          'Radar',
          style: AppTypography.h3.copyWith(
            fontWeight: FontWeight.w500,
            color: AppColors.textPrimary,
          ),
        ),
        centerTitle: true,
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 20.0),
            child: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: const Color(0xFFF3F4F6),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.notifications_none_rounded, color: Colors.black, size: 24),
            ),
          ),
        ],
      ),
      body: ListenableBuilder(
        listenable: _radarNotifier,
        builder: (context, _) {
          final data = _radarNotifier.data;
          final isLoading = _radarNotifier.isLoading && data == null;
          final isStale = _radarNotifier.isStale;

          return CustomScrollView(
            controller: _scrollController,
            slivers: [
              // ── Alert banner (new) ───────────────────────────────────
              if (data != null && data.alert.severity != 'None')
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: _buildAlertBanner(data.alert),
                  ),
                ),

              // ── ALL EXISTING UI (wrapped in SliverToBoxAdapter) ──────
              SliverToBoxAdapter(
                child: SingleChildScrollView(
                  physics: const NeverScrollableScrollPhysics(),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (isStale)
                        Padding(
                          padding: const EdgeInsets.only(
                              top: 16, left: 20, right: 20, bottom: 8),
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 12, vertical: 6),
                            decoration: BoxDecoration(
                              color: const Color(0xFFFEF08A),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: const Text(
                              '⟳ Data older than 90 seconds',
                              style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                  color: Color(0xFF78350F)),
                            ),
                          ),
                        ),
                      const SizedBox(height: 16),
                      Padding(
                        padding:
                            const EdgeInsets.symmetric(horizontal: 20.0),
                        child: _buildTopTabs(),
                      ),
                      const SizedBox(height: 24),
                      Padding(
                        padding:
                            const EdgeInsets.symmetric(horizontal: 20.0),
                        child: _buildRiskBanner(),
                      ),
                      const SizedBox(height: 32),
                      Padding(
                        padding:
                            const EdgeInsets.symmetric(horizontal: 20.0),
                        child: Text('ZONE COMPASS',
                            style: AppTypography.small.copyWith(
                                color: AppColors.textSecondary,
                                fontWeight: FontWeight.w700,
                                letterSpacing: 1.0)),
                      ),
                      const SizedBox(height: 16),
                      _buildZoneCompassChart(),
                      const SizedBox(height: 32),
                      Padding(
                        padding:
                            const EdgeInsets.symmetric(horizontal: 20.0),
                        child: Text('ZONES — TAP TO GO',
                            style: AppTypography.small.copyWith(
                                color: AppColors.textSecondary,
                                fontWeight: FontWeight.w700,
                                letterSpacing: 1.0)),
                      ),
                      const SizedBox(height: 16),
                      Padding(
                        padding:
                            const EdgeInsets.symmetric(horizontal: 20.0),
                        child: _buildZoneList(),
                      ),
                      const SizedBox(height: 32),
                      Padding(
                        padding:
                            const EdgeInsets.symmetric(horizontal: 20.0),
                        child: Text('YOUR EARNINGS TODAY',
                            style: AppTypography.small.copyWith(
                                color: AppColors.textSecondary,
                                fontWeight: FontWeight.w700,
                                letterSpacing: 1.0)),
                      ),
                      const SizedBox(height: 16),
                      Padding(
                        padding:
                            const EdgeInsets.symmetric(horizontal: 20.0),
                        child: _buildEarningsRow(),
                      ),
                      const SizedBox(height: 16),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 20.0),
                        child: _buildClaimStatusBanner(),
                      ),
                      const SizedBox(height: 100),
                    ],
                  ),
                ),
              ),

              // ── Radar zone cards (new) ──────────────────────────────
              if (data != null && data.zones.isNotEmpty)
                SliverList(
                  delegate: SliverChildBuilderDelegate(
                    (context, index) => _buildRadarZoneCard(data.zones[index]),
                    childCount: data.zones.length,
                  ),
                ),

              // ── Earnings protected section (new) ────────────────────
              if (data != null)
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(height: 16),
                        Text('PROTECTED EARNINGS',
                            style: AppTypography.small.copyWith(
                                color: AppColors.textSecondary,
                                fontWeight: FontWeight.w700,
                                letterSpacing: 1.0)),
                        const SizedBox(height: 12),
                        Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: AppColors.brandOrange.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                                color: AppColors.brandOrange.withOpacity(0.3)),
                          ),
                          child: Row(
                            mainAxisAlignment:
                                MainAxisAlignment.spaceBetween,
                            children: [
                              Expanded(
                                child: Column(
                                  crossAxisAlignment:
                                      CrossAxisAlignment.start,
                                  children: [
                                    const Text('Earnings Protected',
                                        style: TextStyle(
                                            fontSize: 12,
                                            color: Color(0xFF6B7280))),
                                    const SizedBox(height: 4),
                                    Text(
                                        '₹${data.earningsToday.protectedInr.toStringAsFixed(0)}',
                                        style: AppTypography.h1
                                            .copyWith(
                                                color:
                                                    AppColors.brandOrange)),
                                  ],
                                ),
                              ),
                              if (data.riderRisk.protectionAutoOn)
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 8, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: AppColors.brandOrange,
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                  child: const Text('Shield ON',
                                      style: TextStyle(
                                          fontSize: 11,
                                          fontWeight: FontWeight.w700,
                                          color: Colors.white)),
                                )
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

              // ── Claim pending section (new) ─────────────────────────
              if (data != null && data.earningsToday.claimPending != null)
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: _buildClaimPendingStrip(
                        data.earningsToday.claimPending!),
                  ),
                ),

              // ── Bottom spacing ─────────────────────────────────────
              SliverToBoxAdapter(
                child: SizedBox(height: isLoading ? 100 : 50),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildTopTabs() {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: const Color(0xFFF3F4F6),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          _buildTabItem(0, 'Right now'),
          const SizedBox(width: 4),
          _buildTabItem(1, 'Next 4 hrs'),
          const SizedBox(width: 4),
          _buildTabItem(2, 'All alerts'),
        ],
      ),
    );
  }

  Widget _buildTabItem(int index, String label) {
    bool isSelected = _selectedTab == index;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _selectedTab = index),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: isSelected ? Colors.white : Colors.transparent,
            borderRadius: BorderRadius.circular(8),
            boxShadow: isSelected ? [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 4, offset: const Offset(0, 2))] : null,
          ),
          child: Text(
            label,
            textAlign: TextAlign.center,
            style: AppTypography.bodySmall.copyWith(
              color: isSelected ? AppColors.brandPrimary : AppColors.textSecondary,
              fontWeight: isSelected ? FontWeight.w800 : FontWeight.w500,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildRiskBanner() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF7ED),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: const Color(0xFFFED7AA)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Be careful out there', style: AppTypography.h3.copyWith(fontWeight: FontWeight.w800, color: const Color(0xFF9A3412))),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: const Color(0xFFFFEDD5),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text('Moderate', style: AppTypography.small.copyWith(color: const Color(0xFF9A3412), fontWeight: FontWeight.w800)),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Rain active in T Nagar. Zone C and A are clear — good to ride there now.',
            style: AppTypography.bodyMedium.copyWith(color: const Color(0xFF9A3412), height: 1.5, fontWeight: FontWeight.w400),
          ),
        ],
      ),
    );
  }

  Widget _buildZoneCompassChart() {
    // Fixed chart diameter — keeps it compact regardless of screen width
    const double chartDiameter = 280.0;
    const double cx = chartDiameter / 2;
    const double cy = chartDiameter / 2;

    // Ring radii (proportional to fixed chart size)
    const rInner  = chartDiameter * 0.10;
    const rSafe   = chartDiameter * 0.22;
    const rCaution = chartDiameter * 0.38;
    const rAvoid  = chartDiameter * 0.50;

    // Zone positions
    final dD = Offset(cx + math.cos(-math.pi * 0.5)  * rCaution * 0.9,
                      cy + math.sin(-math.pi * 0.5)  * rCaution * 0.9);
    final dB = Offset(cx + math.cos(math.pi * 0.9)   * rCaution * 0.78,
                      cy + math.sin(math.pi * 0.9)   * rCaution * 0.78);
    final dE = Offset(cx + math.cos(-math.pi * 0.08) * rCaution * 0.85,
                      cy + math.sin(-math.pi * 0.08) * rCaution * 0.85);
    final dA = Offset(cx + math.cos(math.pi * 0.65)  * rSafe * 1.5,
                      cy + math.sin(math.pi * 0.65)  * rSafe * 1.5);
    final dC = Offset(cx + math.cos(math.pi * 0.28)  * rSafe * 1.5,
                      cy + math.sin(math.pi * 0.28)  * rSafe * 1.5);

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.symmetric(horizontal: 20),
      padding: const EdgeInsets.symmetric(vertical: 16),
      decoration: BoxDecoration(
        color: const Color(0xFFF9F5F2),
        borderRadius: BorderRadius.circular(24),
      ),
      child: Center(
        child: SizedBox(
          width: chartDiameter,
          height: chartDiameter,
          child: Stack(
            clipBehavior: Clip.none,
            children: [
              // ── Rings painter ──────────────────────────────────────────────
              Positioned.fill(
                child: CustomPaint(
                  painter: _CompassPainter(
                    rInner: rInner,
                    rSafe: rSafe,
                    rCaution: rCaution,
                    rAvoid: rAvoid,
                    zoneCOffset: dC,
                    center: const Offset(cx, cy),
                  ),
                ),
              ),

              // ── Avoid label (top) ───────────────────────────────────────────
              const Positioned(
                top: 6, left: 0, right: 0,
                child: Center(
                  child: Text('Avoid',
                    style: TextStyle(color: Color(0xFFEF4444), fontWeight: FontWeight.w700, fontSize: 10)),
                ),
              ),
              // ── Safe label (left) ──────────────────────────────────────────
              Positioned(
                left: 6, top: cy - 8,
                child: const Text('Safe',
                  style: TextStyle(color: Color(0xFF22C55E), fontWeight: FontWeight.w700, fontSize: 10)),
              ),
              // ── Caution label (right) ──────────────────────────────────────
              Positioned(
                right: 6, top: cy - 8,
                child: const Text('Caution',
                  style: TextStyle(color: Color(0xFFF59E0B), fontWeight: FontWeight.w700, fontSize: 10)),
              ),
              // ── Safe label (bottom) ────────────────────────────────────────
              const Positioned(
                bottom: 6, left: 0, right: 0,
                child: Center(
                  child: Text('Safe',
                    style: TextStyle(color: Color(0xFF22C55E), fontWeight: FontWeight.w700, fontSize: 10)),
                ),
              ),

              // ── Zone D (top — red avoid) ───────────────────────────────────
              Positioned(
                left: dD.dx - 22, top: dD.dy - 26,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(width: 12, height: 12,
                      decoration: const BoxDecoration(color: Color(0xFFEF4444), shape: BoxShape.circle)),
                    const SizedBox(height: 3),
                    const Text('Zone D', style: TextStyle(color: Color(0xFF7F1D1D), fontWeight: FontWeight.w700, fontSize: 10)),
                  ],
                ),
              ),

              // ── Zone B (left — orange) ─────────────────────────────────────
              Positioned(
                left: dB.dx - 22, top: dB.dy - 22,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(width: 11, height: 11,
                      decoration: const BoxDecoration(color: Color(0xFFF97316), shape: BoxShape.circle)),
                    const SizedBox(height: 3),
                    const Text('Zone B', style: TextStyle(color: Color(0xFF1C1917), fontWeight: FontWeight.w700, fontSize: 10)),
                  ],
                ),
              ),

              // ── Zone E (right — orange) ────────────────────────────────────
              Positioned(
                left: dE.dx - 22, top: dE.dy - 22,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(width: 11, height: 11,
                      decoration: const BoxDecoration(color: Color(0xFFF97316), shape: BoxShape.circle)),
                    const SizedBox(height: 3),
                    const Text('Zone E', style: TextStyle(color: Color(0xFF1C1917), fontWeight: FontWeight.w700, fontSize: 10)),
                  ],
                ),
              ),

              // ── Zone A (bottom-left — green + check) ──────────────────────
              Positioned(
                left: dA.dx - 26, top: dA.dy - 20,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(width: 10, height: 10,
                          decoration: const BoxDecoration(color: Color(0xFF22C55E), shape: BoxShape.circle)),
                        const SizedBox(width: 2),
                        const Icon(Icons.check_circle_rounded, color: Color(0xFF22C55E), size: 12),
                      ],
                    ),
                    const SizedBox(height: 3),
                    const Text('Zone A', style: TextStyle(color: Color(0xFF1C1917), fontWeight: FontWeight.w700, fontSize: 10)),
                  ],
                ),
              ),

              // ── Zone C (bottom-right — badge) ──────────────────────────────
              Positioned(
                left: dC.dx - 30, top: dC.dy - 20,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(width: 10, height: 10,
                      decoration: const BoxDecoration(color: Color(0xFFF97316), shape: BoxShape.circle)),
                    const SizedBox(height: 3),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Color(0xFFFBD38D), width: 1.5),
                        boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 4)],
                      ),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text('Zone C', style: TextStyle(
                            color: Colors.black, fontWeight: FontWeight.w900, fontSize: 10, height: 1.2)),
                          Text('Best now', style: TextStyle(
                            color: Color(0xFF9A3412), fontWeight: FontWeight.w600, fontSize: 8, height: 1.2)),
                        ],
                      ),
                    ),
                  ],
                ),
              ),

              // ── Center — You / T Nagar ─────────────────────────────────────
              Positioned(
                left: cx - 28, top: cy - 28,
                child: Container(
                  width: 56, height: 56,
                  decoration: BoxDecoration(
                    color: const Color(0xFFEA7B4B).withOpacity(0.9),
                    shape: BoxShape.circle,
                    boxShadow: [BoxShadow(color: const Color(0xFFEA7B4B).withOpacity(0.3), blurRadius: 8)],
                  ),
                  alignment: Alignment.center,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: const [
                      Text('You', style: TextStyle(
                        color: Colors.white, fontWeight: FontWeight.w900, fontSize: 11, height: 1.1)),
                      Text('T Nagar', style: TextStyle(
                        color: Colors.white70, fontSize: 8, height: 1.1)),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }


  Widget _buildZoneList() {
    return Column(
      children: [
        _buildZoneCard(
          zone: 'Adyar',
          zoneKey: 'C',
          distance: '3.2 km',
          time: '8 min away',
          status: 'Best now',
          statusColor: AppColors.brandPrimary,
          badges: ['+₹180 boost', '12 orders', 'No rain', 'Low traffic'],
          isRecommended: true,
        ),
        const SizedBox(height: 16),
        _buildZoneCard(
          zone: 'Anna Nagar',
          zoneKey: 'A',
          distance: '1.8 km',
          time: '5 min away',
          status: 'Safe',
          statusColor: Colors.green,
          badges: ['+₹90 est.', '9 orders', 'Partly cloudy'],
          isAlternative: true,
        ),
        const SizedBox(height: 16),
        _buildZoneCard(
          zone: 'T Nagar',
          zoneKey: 'B',
          distance: '0 km',
          time: 'you are here',
          status: 'Caution',
          statusColor: Colors.orange,
          badges: ['5 orders', 'Rain active', 'Orders dropping'],
          child: _buildZoneActionRow('Protection auto-on', 'View shield'),
        ),
        const SizedBox(height: 16),
        _buildZoneCard(
          zone: 'Nungambakkam',
          zoneKey: 'D',
          distance: '4.1 km',
          time: '11 min away',
          status: 'Avoid',
          statusColor: Colors.red,
          badges: ['Strike signal', '2 orders only'],
        ),
      ],
    );
  }

  Widget _buildZoneCard({
    required String zone,
    required String zoneKey,
    required String distance,
    required String time,
    required String status,
    required Color statusColor,
    required List<String> badges,
    bool isRecommended = false,
    bool isAlternative = false,
    Widget? child,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: isRecommended ? AppColors.brandPrimary : AppColors.border, width: isRecommended ? 1.5 : 1),
      ),
      clipBehavior: Clip.antiAlias,
      child: Stack(
        children: [
          if (isRecommended)
            Positioned(
              left: 0, top: 0, bottom: 0,
              child: Container(width: 4, color: AppColors.brandPrimary),
            ),
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        color: statusColor.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Center(
                        child: Text(zoneKey, style: AppTypography.h3.copyWith(color: statusColor)),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(zone, style: AppTypography.bodyLarge.copyWith(fontWeight: FontWeight.w800, color: Colors.black)),
                          Text('$distance • $time', style: AppTypography.bodySmall),
                        ],
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: statusColor.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(status, style: AppTypography.small.copyWith(color: statusColor, fontWeight: FontWeight.w800, fontSize: 11)),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: badges.map((b) => _buildBadge(b)).toList(),
                ),
                if (child != null) ...[
                  const SizedBox(height: 16),
                  const Divider(height: 1, color: Color(0xFFF3F4F6)),
                  const SizedBox(height: 16),
                  child,
                ] else if (isRecommended) ...[
                  const SizedBox(height: 16),
                  const Divider(height: 1, color: Color(0xFFF3F4F6)),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('Recommended for you', style: AppTypography.small),
                      _buildActionChip('Head here →'),
                    ],
                  ),
                ] else if (isAlternative) ...[
                  const SizedBox(height: 16),
                  const Divider(height: 1, color: Color(0xFFF3F4F6)),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('Good alternative', style: AppTypography.small),
                      _buildActionChip('Go here'),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBadge(String label) {
    bool isBoost = label.contains('₹');
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: isBoost ? const Color(0xFFECFDF5) : const Color(0xFFF3F4F6),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: isBoost ? const Color(0xFF10B981).withOpacity(0.5) : Colors.transparent),
      ),
      child: Text(
        label,
        style: AppTypography.small.copyWith(
          color: isBoost ? const Color(0xFF059669) : AppColors.textSecondary,
          fontWeight: FontWeight.w600,
          fontSize: 11,
        ),
      ),
    );
  }

  Widget _buildActionChip(String label) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.border),
      ),
      child: Text(label, style: AppTypography.bodySmall.copyWith(color: Colors.black, fontWeight: FontWeight.w800)),
    );
  }

  Widget _buildZoneActionRow(String label, String action) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: AppTypography.small),
        _buildActionChip(action),
      ],
    );
  }

  Widget _buildEarningsRow() {
    return Row(
      children: [
        Expanded(
          child: _buildEarningCard('Earned so far', '₹300', '3 rides done'),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: _buildEarningCard('With protection', '₹498', '+₹198 claim', isHighlight: true),
        ),
      ],
    );
  }

  Widget _buildEarningCard(String label, String value, String sub, {bool isHighlight = false}) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFF9FAFB),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: AppTypography.small),
          const SizedBox(height: 4),
          Text(value, style: AppTypography.h1.copyWith(fontSize: 24, fontWeight: FontWeight.w900)),
          Text(sub, style: AppTypography.small.copyWith(color: isHighlight ? AppColors.brandPrimary : AppColors.textSecondary, fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }

  Widget _buildClaimStatusBanner() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF7ED),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFFED7AA).withOpacity(0.5)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFFFED7AA)),
            ),
            child: const Icon(Icons.verified_user_outlined, color: Colors.orange, size: 24),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Smart Plan · claim processing', style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w800, color: Colors.black)),
                Text('₹198 coming for rain disruption · tap to track', style: AppTypography.bodySmall.copyWith(fontSize: 12)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ══════════════════════════════════════════════════════════════════════════
  // NEW RADAR WIDGETS (Block 09 continuation)
  // ══════════════════════════════════════════════════════════════════════════

  Widget _buildAlertBanner(RadarAlert alert) {
    final bgColor = alert.severity == 'Critical'
        ? const Color(0xFFFEE2E2)
        : alert.severity == 'Warning'
            ? const Color(0xFFFEF08A)
            : const Color(0xFFE0F2FE);

    final borderColor = alert.severity == 'Critical'
        ? const Color(0xFFFCA5A5)
        : alert.severity == 'Warning'
            ? const Color(0xFFFCD34D)
            : const Color(0xFF38BDF8);

    final textColor = alert.severity == 'Critical'
        ? const Color(0xFF991B1B)
        : alert.severity == 'Warning'
            ? const Color(0xFF78350F)
            : const Color(0xFF0C4A6E);

    final icon = alert.severity == 'Critical'
        ? Icons.warning_amber_rounded
        : alert.severity == 'Warning'
            ? Icons.info_outline
            : Icons.shield_outlined;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: borderColor),
      ),
      child: Row(
        children: [
          Icon(icon, color: textColor, size: 24),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Disruption Alert',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: textColor,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  alert.message,
                  style: TextStyle(
                    fontSize: 12,
                    color: textColor.withOpacity(0.8),
                    height: 1.4,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRadarZoneCard(ZoneData zone) {
    final isRiskZone = zone.riskLabel == 'Avoid' || zone.riskLabel == 'Caution';
    final chipColor = zone.riskLabel == 'Avoid'
        ? const Color(0xFFFEE2E2)
        : zone.riskLabel == 'Caution'
            ? const Color(0xFFFEF08A)
            : const Color(0xFFECFDF5);

    final chipTextColor = zone.riskLabel == 'Avoid'
        ? const Color(0xFFDC2626)
        : zone.riskLabel == 'Caution'
            ? const Color(0xFBB5000)
            : const Color(0xFF059669);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isRiskZone
                ? const Color(0xFFFCA5A5).withOpacity(0.3)
                : const Color(0xFFD1D5DB),
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.02),
              blurRadius: 4,
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        zone.zoneId.toUpperCase(),
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w800,
                          color: Colors.black,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Opportunity: ${(zone.opportunityIndex * 100).toStringAsFixed(0)}%',
                        style: const TextStyle(
                          fontSize: 12,
                          color: Color(0xFF6B7280),
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: chipColor,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    zone.riskLabel,
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: chipTextColor,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Risk Score',
                        style: const TextStyle(
                          fontSize: 12,
                          color: Color(0xFF9CA3AF),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${zone.riskScore.toStringAsFixed(0)}/100',
                        style: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                          color: Colors.black,
                        ),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Orders',
                        style: const TextStyle(
                          fontSize: 12,
                          color: Color(0xFF9CA3AF),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${zone.orderCount}',
                        style: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                          color: Colors.black,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildClaimPendingStrip(ClaimPending claim) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            AppColors.brandOrange.withOpacity(0.1),
            AppColors.brandOrange.withOpacity(0.05),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: AppColors.brandOrange.withOpacity(0.2),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppColors.brandOrange.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.verified_user_outlined,
                  color: AppColors.brandOrange,
                  size: 18,
                ),
              ),
              const SizedBox(width: 12),
              Text(
                'Protected with Smart Plan',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: AppColors.brandOrange,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            '₹${claim.amountInr.toStringAsFixed(0)} claim filed',
            style: const TextStyle(
              fontSize: 12,
              color: Color(0xFF374151),
              height: 1.5,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Reason: ${claim.reason}',
            style: const TextStyle(
              fontSize: 11,
              color: Color(0xFF9CA3AF),
            ),
          ),
          const SizedBox(height: 2),
          Text(
            'Status: ${claim.status}',
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: claim.status == 'approved'
                  ? const Color(0xFF059669)
                  : claim.status == 'pending'
                      ? const Color(0xFBB5000)
                      : const Color(0xFF6B7280),
            ),
          ),
        ],
      ),
    );
  }


}

class _CompassPainter extends CustomPainter {
  final double rInner;
  final double rSafe;
  final double rCaution;
  final double rAvoid;
  final Offset zoneCOffset;
  final Offset center;

  const _CompassPainter({
    required this.rInner,
    required this.rSafe,
    required this.rCaution,
    required this.rAvoid,
    required this.zoneCOffset,
    required this.center,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // ── Filled zones (outermost to innermost) ─────────────────────────────
    // Avoid zone — light red
    canvas.drawCircle(center, rAvoid, Paint()
      ..color = const Color(0xFFFEE2E2)
      ..style = PaintingStyle.fill);

    // Ring outline for avoid
    canvas.drawCircle(center, rAvoid, Paint()
      ..color = const Color(0xFFFCA5A5)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1);

    // Caution zone — light amber
    canvas.drawCircle(center, rCaution, Paint()
      ..color = const Color(0xFFFEF3C7)
      ..style = PaintingStyle.fill);

    canvas.drawCircle(center, rCaution, Paint()
      ..color = const Color(0xFFFCD34D)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1);

    // Safe zone — light green
    canvas.drawCircle(center, rSafe, Paint()
      ..color = const Color(0xFFDCFCE7)
      ..style = PaintingStyle.fill);

    canvas.drawCircle(center, rSafe, Paint()
      ..color = const Color(0xFF86EFAC)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1);

    // Inner (You) zone — salmon/coral
    canvas.drawCircle(center, rInner + 4, Paint()
      ..color = const Color(0xFFEA7B4B).withOpacity(0.15)
      ..style = PaintingStyle.fill);

    // ── Dashed line from center to Zone C ────────────────────────────────
    final dashPaint = Paint()
      ..color = const Color(0xFFF97316).withOpacity(0.6)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5
      ..strokeCap = StrokeCap.round;

    final dx = zoneCOffset.dx - center.dx;
    final dy = zoneCOffset.dy - center.dy;
    final len = math.sqrt(dx * dx + dy * dy);
    const dashLen = 5.0;
    const gapLen = 4.0;
    double drawn = rInner + 6;
    while (drawn < len - 10) {
      final t0 = drawn / len;
      final t1 = math.min((drawn + dashLen) / len, 1.0);
      canvas.drawLine(
        Offset(center.dx + dx * t0, center.dy + dy * t0),
        Offset(center.dx + dx * t1, center.dy + dy * t1),
        dashPaint,
      );
      drawn += dashLen + gapLen;
    }
  }

  @override
  bool shouldRepaint(covariant _CompassPainter old) =>
      old.rInner != rInner || old.rCaution != rCaution;
}
