// lib/screens/parametric_screen.dart
// ---------------------------------------------------------------------------
// Figgy GigShield — Parametric Insurance Screen (Worker-Friendly Redesign)
// Dark theme · Orange (#D85A30) accents · Wired to GET /api/weather/zone/
// ---------------------------------------------------------------------------

import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:figgy_app/config/api_base_url.dart';
import 'package:figgy_app/screens/earnings_gap_widget.dart';
import 'package:figgy_app/screens/payout_preview_card.dart';
import 'package:figgy_app/screens/trigger_card_widget.dart';
import 'package:figgy_app/routes.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

// ── Dark design tokens (screen-local) ─────────────────────────────────────
class _C {
  static const bg      = Color(0xFF0F1117);
  static const surface = Color(0xFF1A1D27);
  static const card    = Color(0xFF22263A);
  static const orange  = Color(0xFFD85A30);
  static const green   = Color(0xFF10B981);
  static const blue    = Color(0xFF3B82F6);
  static const amber   = Color(0xFFF59E0B);
  static const txt1    = Color(0xFFF1F5F9);
  static const txt2    = Color(0xFF94A3B8);
  static const txt3    = Color(0xFF475569);
  static const border  = Color(0xFF2D3148);
}

TextStyle _t(double size, FontWeight w, Color c, {double ls = 0, double h = 1.4}) =>
    GoogleFonts.outfit(fontSize: size, fontWeight: w, color: c, letterSpacing: ls, height: h);

const _cacheKey = 'parametric_weather_cache';

// ===========================================================================
class ParametricScreen extends StatefulWidget {
  const ParametricScreen({super.key});
  @override State<ParametricScreen> createState() => _ParametricScreenState();
}

class _ParametricScreenState extends State<ParametricScreen>
    with SingleTickerProviderStateMixin {

  // ── State ─────────────────────────────────────────────────────────────
  int    _navIndex   = 2;
  bool   _isLoading  = true;
  bool   _isOffline  = false;
  String _workerZone = 'Central';
  String _tier       = 'Smart';
  String _workerId   = '';
  double _expected   = 180.0;
  double _current    = 42.0;

  /// Disruption timer — tracks hours since first trigger fired this session.
  DateTime? _triggerStartTime;
  double get _disruptionHours {
    if (!_triggered || _triggerStartTime == null) return 1.0;
    return DateTime.now().difference(_triggerStartTime!).inMinutes / 60.0;
  }

  Map<String, dynamic>? _weather;   // live data
  Map<String, dynamic>? _cached;    // offline fallback

  Timer? _timer;
  late AnimationController _pulse;
  late Animation<double>   _pulseAnim;

  // ── Lifecycle ─────────────────────────────────────────────────────────
  @override
  void initState() {
    super.initState();
    _pulse = AnimationController(vsync: this, duration: const Duration(milliseconds: 1100))
      ..repeat(reverse: true);
    _pulseAnim = Tween<double>(begin: 0.25, end: 1.0)
        .animate(CurvedAnimation(parent: _pulse, curve: Curves.easeInOut));
    _init();
  }

  @override
  void dispose() {
    _timer?.cancel();
    _pulse.dispose();
    super.dispose();
  }

  Future<void> _init() async {
    final prefs = await SharedPreferences.getInstance();
    _workerZone = prefs.getString('zone')         ?? 'Central';
    _tier       = (prefs.getString('selected_tier') ?? 'Smart').trim();
    _workerId   = prefs.getString('worker_id')    ?? '';

    // Load offline cache for instant display
    final raw = prefs.getString(_cacheKey);
    if (raw != null) {
      try { _cached = json.decode(raw) as Map<String, dynamic>; } catch (_) {}
    }

    await _fetch();
    _timer = Timer.periodic(const Duration(minutes: 5), (_) => _fetch());
  }

  Future<void> _fetch() async {
    if (_weather == null) setState(() => _isLoading = true);
    try {
      final resp = await http
          .get(Uri.parse('${figgyApiBaseUrl}/api/weather/zone/$_workerZone'),
               headers: {'Accept': 'application/json'})
          .timeout(const Duration(seconds: 10));

      if (!mounted) return;
      if (resp.statusCode == 200) {
        final data = json.decode(resp.body) as Map<String, dynamic>;
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString(_cacheKey, resp.body);
        // Start disruption timer on first trigger detection
        if ((data['disruption_triggered'] as bool?) == true &&
            _triggerStartTime == null) {
          _triggerStartTime = DateTime.now();
        } else if ((data['disruption_triggered'] as bool?) != true) {
          _triggerStartTime = null;
        }
        setState(() { _weather = data; _isOffline = false; _isLoading = false; });
        return;
      }
    } catch (_) {}

    if (!mounted) return;
    setState(() {
      _isOffline = true;
      _isLoading = false;
      _weather ??= _cached; // fall back to cache when offline
    });
  }

  // ── Helpers ───────────────────────────────────────────────────────────
  bool get _triggered => (_weather?['disruption_triggered'] as bool?) ?? false;

  Map<String, dynamic> _th(String key) =>
      ((_weather?['thresholds'] as Map?)?.cast<String, dynamic>()[key]) ?? {};

  double get _gapRatio =>
      _expected > 0 ? (_expected - _current).clamp(0, _expected) / _expected : 0;

  Color get _barColor => _gapRatio > 0.30 ? _C.orange : _C.green;

  // ── Build ─────────────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _C.bg,
      body: SafeArea(
        child: Column(children: [
          _appBar(),
          if (_isOffline) _offlineBanner(),
          Expanded(
            child: _isLoading
                ? _skeleton()
                : RefreshIndicator(
                    color: _C.orange,
                    backgroundColor: _C.surface,
                    onRefresh: _fetch,
                    child: SingleChildScrollView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          EarningsGapWidget(
                            currentEarnings:   _current,
                            expectedEarnings:  _expected,
                            tier:              _tier,
                            isDisruptionActive: _triggered,
                          ),
                          const SizedBox(height: 24),
                          _label('REAL-TIME TRIGGERS'),
                          const SizedBox(height: 12),
                          TriggerCardWidget(
                            triggerKey:    'RAIN',
                            label:         'Rainfall',
                            icon:          Icons.water_drop_rounded,
                            unit:          'mm',
                            thresholdData: _th('RAIN'),
                            hasLiveData:   _weather != null,
                          ),
                          const SizedBox(height: 10),
                          TriggerCardWidget(
                            triggerKey:    'AQI',
                            label:         'Air Pollution',
                            icon:          Icons.smoke_free_rounded,
                            unit:          '',
                            thresholdData: _th('AQI'),
                            hasLiveData:   _weather != null,
                          ),
                          const SizedBox(height: 10),
                          TriggerCardWidget(
                            triggerKey:    'CURFEW',
                            label:         'Curfew Status',
                            icon:          Icons.flag_rounded,
                            unit:          '',
                            thresholdData: _th('CURFEW'),
                            hasLiveData:   _weather != null,
                          ),
                          const SizedBox(height: 20),
                          // ── Payout Preview Card ─────────────────────────
                          _buildPayoutPreviewCard(),
                          const SizedBox(height: 28),
                          _label('HOW FIGGY PROTECTS YOU'),
                          const SizedBox(height: 14),
                          _ruleFlow(),
                          const SizedBox(height: 24),
                          _cta(),
                          const SizedBox(height: 16),
                        ],
                      ),
                    ),
                  ),
          ),
        ]),
      ),
      bottomNavigationBar: _bottomNav(),
    );
  }

  // ── App Bar ───────────────────────────────────────────────────────────
  Widget _appBar() => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
    child: Row(children: [
      Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('GigShield', style: _t(22, FontWeight.w900, _C.txt1, ls: -0.5)),
        Row(children: [
          Container(width: 7, height: 7,
            decoration: BoxDecoration(
              color: _triggered ? _C.orange : _C.green,
              shape: BoxShape.circle,
            )),
          const SizedBox(width: 5),
          Text(
            _triggered ? 'Disruption · $_workerZone' : 'All Clear · $_workerZone',
            style: _t(12, FontWeight.w500, _C.txt2),
          ),
        ]),
      ]),
      const Spacer(),
      Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: _C.surface, borderRadius: BorderRadius.circular(20),
          border: Border.all(color: _C.border),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.location_on_rounded, color: _C.orange, size: 13),
          const SizedBox(width: 4),
          Text(_workerZone, style: _t(12, FontWeight.w700, _C.txt1)),
        ]),
      ),
    ]),
  );

  Widget _offlineBanner() => Container(
    width: double.infinity,
    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
    color: _C.amber.withOpacity(0.12),
    child: Row(children: [
      const Icon(Icons.wifi_off_rounded, color: _C.amber, size: 13),
      const SizedBox(width: 8),
      Text('Offline — showing cached data', style: _t(11, FontWeight.w600, _C.amber)),
    ]),
  );

  // ── Skeleton ──────────────────────────────────────────────────────────
  Widget _skeleton() => Padding(
    padding: const EdgeInsets.all(20),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _skel(140, r: 20),
      const SizedBox(height: 24),
      _skel(14, w: 160),
      const SizedBox(height: 12),
      _skel(90),
      const SizedBox(height: 10),
      _skel(90),
      const SizedBox(height: 10),
      _skel(90),
      const SizedBox(height: 28),
      _skel(14, w: 200),
      const SizedBox(height: 14),
      _skel(80),
      const SizedBox(height: 24),
      _skel(54),
    ]),
  );

  Widget _skel(double h, {double? w, double r = 12}) => Container(
    height: h, width: w ?? double.infinity,
    margin: const EdgeInsets.only(bottom: 0),
    decoration: BoxDecoration(color: _C.surface, borderRadius: BorderRadius.circular(r)),
  );

  Widget _label(String t) => Text(t, style: _t(10, FontWeight.w800, _C.txt3, ls: 1.5));

  // ── Payout Preview Card ───────────────────────────────────────────────
  Widget _buildPayoutPreviewCard() {
    // Determine which trigger is currently firing (prioritise RAIN > AQI > CURFEW)
    String activeTrigger = 'RAIN';
    double detectedValue = 0.0;

    if (_th('RAIN')['triggered'] == true) {
      activeTrigger = 'RAIN';
      detectedValue = (_th('RAIN')['detected_value'] as num?)?.toDouble() ?? 0;
    } else if (_th('AQI')['triggered'] == true) {
      activeTrigger = 'AQI';
      detectedValue = (_th('AQI')['detected_value'] as num?)?.toDouble() ?? 0;
    } else if (_th('CURFEW')['triggered'] == true) {
      activeTrigger = 'CURFEW';
      detectedValue = _th('CURFEW')['detected_value'] == true ? 1.0 : 0.0;
    }

    return PayoutPreviewCard(
      workerId:        _workerId,
      triggerType:     activeTrigger,
      detectedValue:   detectedValue,
      tierName:        _tier,
      isTriggered:     _triggered,
      disruptionHours: _disruptionHours,
    );
  }

  // ── Rule Engine 3-step flow ───────────────────────────────────────────
  Widget _ruleFlow() {
    const steps = [
      ('Disruption\ndetected', _C.orange),
      ('Activity\nverified',   _C.blue),
      ('Claim\ntriggered',     _C.green),
    ];
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
      decoration: BoxDecoration(
        color: _C.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: _C.border),
      ),
      child: Row(
        children: [
          for (int i = 0; i < steps.length; i++) ...[
            _flowStep(steps[i].$1, steps[i].$2),
            if (i < steps.length - 1) Expanded(child: _arrow()),
          ],
        ],
      ),
    );
  }

  Widget _flowStep(String label, Color color) => Column(children: [
    Container(
      width: 28, height: 28,
      decoration: BoxDecoration(
        color: color.withOpacity(0.12), shape: BoxShape.circle,
        border: Border.all(color: color.withOpacity(0.45), width: 1.5),
      ),
      child: Center(child: Container(
        width: 10, height: 10,
        decoration: BoxDecoration(color: color, shape: BoxShape.circle),
      )),
    ),
    const SizedBox(height: 8),
    Text(label, textAlign: TextAlign.center, style: _t(10, FontWeight.w600, _C.txt2)),
  ]);

  Widget _arrow() => Row(children: [
    Expanded(child: Container(height: 1, color: _C.border)),
    const Icon(Icons.arrow_forward_ios_rounded, color: _C.txt3, size: 11),
  ]);

  // ── CTA ───────────────────────────────────────────────────────────────
  Widget _cta() => _triggered ? _ctaTriggered() : _ctaNormal();

  Widget _ctaNormal() => SizedBox(
    width: double.infinity,
    child: OutlinedButton(
      onPressed: () {},
      style: OutlinedButton.styleFrom(
        padding: const EdgeInsets.symmetric(vertical: 16),
        side: BorderSide(color: _C.orange.withOpacity(0.4), width: 1.5),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      ),
      child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
        Text('View My Coverage Details', style: _t(14, FontWeight.w700, _C.txt1)),
        const SizedBox(width: 8),
        const Icon(Icons.arrow_forward_rounded, color: _C.orange, size: 17),
      ]),
    ),
  );

  Widget _ctaTriggered() => SizedBox(
    width: double.infinity,
    child: ElevatedButton(
      onPressed: () {
        Navigator.pushNamed(context, AppRoutes.powToken, arguments: PowTokenArgs(workerId: _workerId));
      },
      style: ElevatedButton.styleFrom(
        backgroundColor: _C.orange,
        padding: const EdgeInsets.symmetric(vertical: 16),
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        shadowColor: _C.orange.withOpacity(0.4),
      ),
      child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
        AnimatedBuilder(
          animation: _pulseAnim,
          builder: (_, __) => Opacity(
            opacity: _pulseAnim.value,
            child: Container(
              width: 8, height: 8,
              decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle),
            ),
          ),
        ),
        const SizedBox(width: 10),
        Flexible(child: Text('Continue to Fraud Verification',
            style: _t(13, FontWeight.w800, Colors.white),
            overflow: TextOverflow.ellipsis)),
        const SizedBox(width: 6),
        const Icon(Icons.arrow_forward_rounded, color: Colors.white, size: 16),
      ]),
    ),
  );

  // ── Bottom Nav ────────────────────────────────────────────────────────
  Widget _bottomNav() {
    const items = [
      (Icons.home_outlined,                    'Home'),
      (Icons.receipt_long_outlined,            'Claims'),
      (Icons.shield_rounded,                   'Insurance'),
      (Icons.account_balance_wallet_outlined,  'Wallet'),
      (Icons.person_outline_rounded,           'Profile'),
    ];
    return Container(
      padding: const EdgeInsets.fromLTRB(0, 10, 0, 24),
      decoration: BoxDecoration(
        color: _C.surface,
        border: Border(top: BorderSide(color: _C.border, width: 0.5)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          for (int i = 0; i < items.length; i++) _navItem(i, items[i].$1, items[i].$2),
        ],
      ),
    );
  }

  Widget _navItem(int index, IconData icon, String label) {
    final active = index == _navIndex;
    final color  = active ? _C.orange : _C.txt3;
    return GestureDetector(
      onTap: () => setState(() => _navIndex = index),
      behavior: HitTestBehavior.opaque,
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Stack(alignment: Alignment.center, children: [
          if (active)
            Container(
              width: 44, height: 28,
              decoration: BoxDecoration(
                color: _C.orange.withOpacity(0.12),
                borderRadius: BorderRadius.circular(14),
              ),
            ),
          Icon(icon, color: color, size: 22),
        ]),
        const SizedBox(height: 4),
        Text(label, style: _t(10, active ? FontWeight.w800 : FontWeight.w500, color)),
      ]),
    );
  }
}
