// lib/screens/payout_preview_card.dart
// ---------------------------------------------------------------------------
// Figgy GigShield — Live Payout Preview Card
//
// Shown on the Parametric Insurance Engine screen when a trigger is active.
// Polls GET /api/claim/calculate_preview/<workerId> every 60 seconds and
// animates the payout amount counting up/down via a Tween animation.
//
// Constructor params
// ------------------
//   workerId       : String  — e.g. "W-00123"
//   triggerType    : String  — "RAIN" | "AQI" | "CURFEW"
//   detectedValue  : double  — live sensor reading (mm/hr, AQI index, …)
//   tierName       : String  — "Lite" | "Smart" | "Elite"
//   isTriggered    : bool    — if false, shows the standby state
//   disruptionHours: double  — hours elapsed since trigger (auto-increments)
//
// API called
// ----------
//   GET /api/claim/calculate_preview/<workerId>
//     ?disruption_hours=X&trigger_type=RAIN&detected_value=Y
//
// State management: local setState + AnimationController (no Provider needed)
// ---------------------------------------------------------------------------

import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'package:figgy_app/config/api_base_url.dart';
import 'package:figgy_app/screens/payout_explainer_sheet.dart';

// ── Design tokens ─────────────────────────────────────────────────────────
class _P {
  static const bg       = Color(0xFF1A1A2E); // card background (spec)
  static const surface  = Color(0xFF22263A);
  static const orange   = Color(0xFFD85A30);
  static const green    = Color(0xFF10B981);
  static const blue     = Color(0xFF3B82F6);
  static const amber    = Color(0xFFF59E0B);
  static const txt1     = Color(0xFFF1F5F9);
  static const txt2     = Color(0xFF94A3B8);
  static const txt3     = Color(0xFF475569);
  static const border   = Color(0xFF2D3148);
  static const standby  = Color(0xFF334155);
}

TextStyle _ts(double sz, FontWeight w, Color c,
    {double ls = 0, double h = 1.4}) =>
    GoogleFonts.outfit(
        fontSize: sz, fontWeight: w, color: c, letterSpacing: ls, height: h);

// ===========================================================================
class PayoutPreviewCard extends StatefulWidget {
  final String workerId;
  final String triggerType;    // "RAIN" | "AQI" | "CURFEW"
  final double detectedValue;
  final String tierName;       // "Lite" | "Smart" | "Elite"
  final bool   isTriggered;
  final double disruptionHours;

  const PayoutPreviewCard({
    super.key,
    required this.workerId,
    required this.triggerType,
    required this.detectedValue,
    required this.tierName,
    required this.isTriggered,
    this.disruptionHours = 1.0,
  });

  @override
  State<PayoutPreviewCard> createState() => _PayoutPreviewCardState();
}

class _PayoutPreviewCardState extends State<PayoutPreviewCard>
    with TickerProviderStateMixin {

  // ── API state ──────────────────────────────────────────────────────────
  Map<String, dynamic>? _data;
  bool   _loading  = false;
  String _error    = '';
  Timer? _pollTimer;

  // ── Counter animation (payout amount) ─────────────────────────────────
  late AnimationController _counterCtrl;
  late Animation<double>   _counterAnim;
  double _prevPayout = 0;
  double _targetPayout = 0;

  // ── Pulse animation (live indicator) ──────────────────────────────────
  late AnimationController _pulseCtrl;
  late Animation<double>   _pulseAnim;

  // ── Lifecycle ──────────────────────────────────────────────────────────
  @override
  void initState() {
    super.initState();

    // Counter animation — 800 ms ease-out
    _counterCtrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 800));
    _counterAnim = Tween<double>(begin: 0, end: 0).animate(
        CurvedAnimation(parent: _counterCtrl, curve: Curves.easeOut));

    // Pulse animation — repeating breathe
    _pulseCtrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 1400))
      ..repeat(reverse: true);
    _pulseAnim = Tween<double>(begin: 0.5, end: 1.0).animate(
        CurvedAnimation(parent: _pulseCtrl, curve: Curves.easeInOut));

    if (widget.isTriggered) _fetchPreview();
  }

  @override
  void didUpdateWidget(PayoutPreviewCard old) {
    super.didUpdateWidget(old);
    // Re-fetch if trigger state or key params changed
    if (widget.isTriggered &&
        (old.workerId       != widget.workerId       ||
         old.triggerType    != widget.triggerType    ||
         old.detectedValue  != widget.detectedValue  ||
         old.disruptionHours!= widget.disruptionHours ||
         !old.isTriggered)) {
      _fetchPreview();
      _pollTimer?.cancel();
      _schedulePoll();
    }
    if (!widget.isTriggered) {
      _pollTimer?.cancel();
    }
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _counterCtrl.dispose();
    _pulseCtrl.dispose();
    super.dispose();
  }

  void _schedulePoll() {
    _pollTimer = Timer.periodic(const Duration(seconds: 60), (_) {
      if (widget.isTriggered && mounted) _fetchPreview();
    });
  }

  // ── API call ───────────────────────────────────────────────────────────
  Future<void> _fetchPreview() async {
    if (!mounted) return;
    setState(() { _loading = _data == null; _error = ''; });

    try {
      final uri = Uri.parse('${figgyApiBaseUrl}/api/claim/calculate_preview/${widget.workerId}')
          .replace(queryParameters: {
        'disruption_hours': widget.disruptionHours.toStringAsFixed(2),
        'trigger_type':     widget.triggerType,
        'detected_value':   widget.detectedValue.toStringAsFixed(2),
      });

      final resp = await http
          .get(uri, headers: {'Accept': 'application/json'})
          .timeout(const Duration(seconds: 10));

      if (!mounted) return;

      if (resp.statusCode == 200) {
        final body = json.decode(resp.body) as Map<String, dynamic>;
        final newPayout = (body['eligible_payout'] as num?)?.toDouble() ?? 0;
        _animateCounter(newPayout);
        setState(() { _data = body; _loading = false; });
        if (_pollTimer == null) _schedulePoll();
      } else {
        final msg = (json.decode(resp.body)['message'] as String?) ?? 'API error';
        setState(() { _error = msg; _loading = false; });
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error   = 'Could not reach server';
        _loading = false;
      });
      debugPrint('[PayoutPreviewCard] fetch error: $e');
    }
  }

  void _animateCounter(double newTarget) {
    _prevPayout    = _targetPayout;
    _targetPayout  = newTarget;
    _counterAnim   = Tween<double>(begin: _prevPayout, end: newTarget)
        .animate(CurvedAnimation(parent: _counterCtrl, curve: Curves.easeOut));
    _counterCtrl
      ..reset()
      ..forward();
  }

  // ── Build ──────────────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: _P.bg,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: _P.border),
        // Orange top border (3 px accent)
        boxShadow: [
          BoxShadow(
            color: widget.isTriggered
                ? _P.orange.withOpacity(0.20)
                : Colors.black.withOpacity(0.12),
            blurRadius: 16,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        // ── Orange top accent bar ──────────────────────────────────────
        Container(
          height: 3,
          decoration: BoxDecoration(
            color: widget.isTriggered ? _P.orange : _P.standby,
            borderRadius: const BorderRadius.only(
              topLeft:  Radius.circular(18),
              topRight: Radius.circular(18),
            ),
          ),
        ),

        Padding(
          padding: const EdgeInsets.fromLTRB(18, 16, 18, 16),
          child: widget.isTriggered ? _activeBody() : _standbyBody(),
        ),
      ]),
    );
  }

  // ── Active state body ──────────────────────────────────────────────────
  Widget _activeBody() {
    if (_loading) return _skeleton();

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      // "Your Protection Value" title row
      Row(children: [
        Text('YOUR PROTECTION VALUE',
            style: _ts(10, FontWeight.w800, _P.txt2, ls: 1.3)),
        const Spacer(),
        // Live pulse dot
        AnimatedBuilder(
          animation: _pulseAnim,
          builder: (_, __) => Opacity(
            opacity: _pulseAnim.value,
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Container(width: 6, height: 6,
                  decoration: const BoxDecoration(
                      color: _P.orange, shape: BoxShape.circle)),
              const SizedBox(width: 4),
              Text('LIVE', style: _ts(9, FontWeight.w800, _P.orange, ls: 0.8)),
            ]),
          ),
        ),
      ]),
      const SizedBox(height: 4),
      Text('Estimated Payout',
          style: _ts(12, FontWeight.w500, _P.txt3)),
      const SizedBox(height: 14),

      // ── Animated ₹ Amount ──────────────────────────────────────────
      Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
        AnimatedBuilder(
          animation: _counterAnim,
          builder: (_, __) {
            final val = _counterAnim.value;
            return AnimatedBuilder(
              animation: _pulseAnim,
              builder: (_, __) => Transform.scale(
                scale: 1.0 + (_pulseAnim.value - 0.75) * 0.012,
                child: RichText(text: TextSpan(children: [
                  TextSpan(text: '₹',
                      style: _ts(22, FontWeight.w700, _P.orange)),
                  TextSpan(text: val.toInt().toString(),
                      style: _ts(48, FontWeight.w900, _P.txt1,
                          ls: -1.5, h: 1.0)),
                ])),
              ),
            );
          },
        ),
        const SizedBox(width: 10),
        // Surge badge
        if (_data?['surge_bonus_applied'] == true)
          _surgePill(),
      ]),
      const SizedBox(height: 12),

      // ── Breakdown row ──────────────────────────────────────────────
      if (_data != null) _breakdownRow(),
      const SizedBox(height: 4),

      // ── Error hint ─────────────────────────────────────────────────
      if (_error.isNotEmpty)
        Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Row(children: [
            const Icon(Icons.wifi_off_rounded, color: _P.amber, size: 12),
            const SizedBox(width: 4),
            Text(_error, style: _ts(10, FontWeight.w600, _P.amber)),
          ]),
        ),

      const SizedBox(height: 14),
      const Divider(color: _P.border, thickness: 0.5),
      const SizedBox(height: 10),

      // ── How is this calculated? ────────────────────────────────────
      GestureDetector(
        onTap: _showExplanationSheet,
        child: Row(children: [
          const Icon(Icons.info_outline_rounded, color: _P.blue, size: 14),
          const SizedBox(width: 6),
          Text('How is this calculated?',
              style: _ts(12, FontWeight.w600, _P.blue)),
          const Spacer(),
          const Icon(Icons.chevron_right_rounded, color: _P.txt3, size: 16),
        ]),
      ),
    ]);
  }

  // ── Breakdown row: Expected · Earned · Loss ────────────────────────────
  Widget _breakdownRow() {
    final exp  = (_data!['expected_earnings'] as num?)?.toInt() ?? 0;
    final act  = (_data!['actual_earnings']   as num?)?.toInt() ?? 0;
    final loss = (_data!['income_loss']       as num?)?.toInt() ?? 0;

    return Wrap(spacing: 0, children: [
      _bItem('Expected', '₹$exp'),
      _bDot(),
      _bItem('Earned', '₹$act'),
      _bDot(),
      _bItem('Loss', '₹$loss', highlight: true),
    ]);
  }

  Widget _bItem(String label, String value, {bool highlight = false}) =>
      RichText(text: TextSpan(
        style: _ts(11, FontWeight.w500, _P.txt3),
        children: [
          TextSpan(text: '$label '),
          TextSpan(text: value,
              style: _ts(11, FontWeight.w800,
                  highlight ? _P.orange : _P.txt2)),
        ],
      ));

  Widget _bDot() => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 6),
    child: Text('·', style: _ts(11, FontWeight.w400, _P.txt3)),
  );

  // ── Surge pill ─────────────────────────────────────────────────────────
  Widget _surgePill() {
    final mult = (_data?['surge_multiplier'] as num?)?.toDouble() ?? 1.0;
    final pct  = ((mult - 1) * 100).toInt();
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        gradient: LinearGradient(
            colors: [_P.orange.withOpacity(0.8), _P.amber]),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [BoxShadow(
            color: _P.orange.withOpacity(0.35), blurRadius: 8)],
      ),
      child: Text(
        'ELITE SURGE +$pct%',
        style: _ts(9, FontWeight.w900, Colors.white, ls: 0.5),
      ),
    );
  }

  // ── Skeleton loading ───────────────────────────────────────────────────
  Widget _skeleton() => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      _skelBox(12, w: 160),
      const SizedBox(height: 14),
      _skelBox(52),
      const SizedBox(height: 10),
      _skelBox(12, w: double.infinity),
      const SizedBox(height: 14),
      _skelBox(12, w: 180),
    ],
  );

  Widget _skelBox(double h, {double? w}) => Container(
    height: h, width: w ?? 120,
    margin: const EdgeInsets.only(bottom: 0),
    decoration: BoxDecoration(
        color: _P.surface, borderRadius: BorderRadius.circular(6)),
  );

  // ── Standby (no trigger) body ──────────────────────────────────────────
  Widget _standbyBody() => Row(children: [
    Container(
      width: 44, height: 44,
      decoration: BoxDecoration(
        color: _P.standby.withOpacity(0.3),
        borderRadius: BorderRadius.circular(12),
      ),
      child: const Icon(Icons.shield_rounded, color: _P.txt3, size: 22),
    ),
    const SizedBox(width: 14),
    Expanded(child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('No active disruption',
            style: _ts(14, FontWeight.w700, _P.txt2)),
        const SizedBox(height: 3),
        Text('Your coverage is on standby · Ready to protect you',
            style: _ts(11, FontWeight.w500, _P.txt3)),
      ],
    )),
  ]);

  // ── Explanation BottomSheet ────────────────────────────────────────────
  void _showExplanationSheet() {
    final tier = _data?['tier'] as String? ?? widget.tierName;
    final cap  = _data?['tier_cap'] as int?;
    final capStr = cap != null ? '₹$cap' : 'your plan limit';

    showPayoutExplainerSheet(context, tier: tier, capStr: capStr);
  }
}
