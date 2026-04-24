import 'dart:async';
import 'dart:math';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:figgy_app/theme/app_theme.dart';
import 'package:figgy_app/app/main_wrapper.dart';
import 'package:figgy_app/models/ride.dart';

// ─────────────────────────────────────────────────────
// DEMAND SCREEN
// ─────────────────────────────────────────────────────
class DemandScreen extends StatefulWidget {
  const DemandScreen({super.key});

  @override
  State<DemandScreen> createState() => _DemandScreenState();
}

class _DemandScreenState extends State<DemandScreen> {
  bool _smartMode = true;

  // ── Simulation State ────────────────────────
  Ride? currentRide;
  List<Ride> completedRides = [];
  List<LatLng> routeCoordinates = [];
  LatLng riderPosition = const LatLng(13.0418, 80.2341);

  Timer? _stepTimer;
  int _routeIndex = 0;
  int _subStep = 0;
  int _subSteps = 25;
  Duration _stepDuration = const Duration(milliseconds: 80);
  bool _autoCenter = true;

  final MapController _mapController = MapController();

  // ── Chennai Locations ─────────────────────
  static const List<Map<String, dynamic>> _locations = [
    {'name': 'T Nagar',      'lat': 13.0418, 'lng': 80.2341},
    {'name': 'Anna Nagar',   'lat': 13.0850, 'lng': 80.2101},
    {'name': 'Velachery',    'lat': 12.9791, 'lng': 80.2241},
    {'name': 'Adyar',        'lat': 13.0067, 'lng': 80.2578},
    {'name': 'Kodambakkam',  'lat': 13.0524, 'lng': 80.2237},
    {'name': 'Mylapore',     'lat': 13.0339, 'lng': 80.2696},
    {'name': 'Nungambakkam', 'lat': 13.0605, 'lng': 80.2449},
  ];

  // ── Chennai Restaurants ────────────────────
  static const List<Map<String, dynamic>> _restaurants = [
    {'name': 'Saravana Bhavan',   'tag': 'South Indian'},
    {'name': 'Murugan Idli Shop', 'tag': 'Tiffin & Snacks'},
    {'name': 'Buhari Hotel',      'tag': 'Biriyani & Tandoori'},
    {'name': 'Junior Kuppanna',   'tag': 'Chettinad Cuisine'},
    {'name': 'Dindigul Thalappakatti', 'tag': 'Biriyani'},
    {'name': 'Hot Breads',        'tag': 'Bakery & Café'},
    {'name': 'Sangeetha Restaurant', 'tag': 'Vegetarian'},
    {'name': 'Ponnusamy Hotel',   'tag': 'Non-Veg Specials'},
  ];

  // ── Menu Items per category ────────────────
  static const List<List<String>> _menuItems = [
    ['Masala Dosa', 'Filter Coffee', 'Sambar Vada'],
    ['Plain Idli ×2', 'Pongal', 'Coconut Chutney'],
    ['Chicken Biriyani', 'Mutton Chops', 'Raita'],
    ['Kuzhi Paniyaram', 'Kari Dosai', 'Curd Rice'],
    ['Veg Biriyani', 'Chicken 65', 'Lassi'],
    ['Chocolate Croissant', 'Cappuccino', 'Sandwich'],
    ['Meals Thali', 'Butter Milk', 'Papad'],
    ['Egg Curry', 'Parotta ×3', 'Onion Raita'],
  ];

  // ── Street Addresses per zone ─────────────
  static const Map<String, List<String>> _addresses = {
    'T Nagar':       ['14, Pondy Bazaar, T Nagar', '7, GN Chetty Rd, T Nagar', '22-A, Usman Road, T Nagar'],
    'Anna Nagar':    ['3rd Ave, Block C, Anna Nagar', '15, 7th Main Rd, Anna Nagar West', 'Tower Park Area, Anna Nagar'],
    'Velachery':     ['42, Vijaya Nagar, Velachery', '8, 100 Feet Rd, Velachery', 'Phoenix Mall Complex, Velachery'],
    'Adyar':         ['5, Gandhi Nagar, Adyar', '18, 4th Cross St, Adyar', 'Besant Nagar Beach Rd, Adyar'],
    'Kodambakkam':   ['11A, KH Road, Kodambakkam', '23, Arcot Road, Kodambakkam', '6, Mahalingapuram, Kodambakkam'],
    'Mylapore':      ['12, Kutchery Road, Mylapore', 'Near Kapaleeshwarar Temple, Mylapore', '3, R K Mutt Rd, Mylapore'],
    'Nungambakkam':  ['45, Haddows Rd, Nungambakkam', 'Khader Nawaz Khan Rd, Nungambakkam', '8, Sterling Road, Nungambakkam'],
  };

  static const List<String> _customerNames = [
    'Arjun S.', 'Priya M.', 'Karthik R.', 'Divya K.',
    'Suresh P.', 'Anitha B.', 'Rahul V.', 'Meena L.',
  ];

  List<Ride> _generateInitialHistory() {
    final rng = Random();
    final List<Ride> history = [];
    final now = DateTime.now();

    // Generate exactly 30 rich delivery records spanning the last 60 days
    for (int i = 0; i < 30; i++) {
      // Intentionally bias a few towards "today / yesterday", others completely random
      int daysAgo = rng.nextInt(60);
      if (i < 3) daysAgo = 0;
      if (i >= 3 && i < 6) daysAgo = 1;
      
      final hoursAgo = rng.nextInt(24);
      final minsAgo = rng.nextInt(60);
      final rideTime = now.subtract(Duration(days: daysAgo, hours: hoursAgo, minutes: minsAgo));
      
      final ride = _generateMockRide(overrideTime: rideTime);
      ride.status = 'delivered';
      ride.endTime = rideTime.add(Duration(minutes: rng.nextInt(20) + 12)); // 12-32 mins duration
      history.add(ride);
    }
    
    // Reverse chronological order mirroring real systems
    history.sort((a, b) => b.endTime!.compareTo(a.endTime!));
    
    return history;
  }

  @override
  void initState() {
    super.initState();
    completedRides = _generateInitialHistory();
    globalCompletedRidesNotifier.value = List.from(completedRides);
    _startNewRide();
  }

  @override
  void dispose() {
    _stepTimer?.cancel();
    super.dispose();
  }

  // ── Route Generation (Fallback smooth curve) ────────
  List<LatLng> _generateRouteFallback(LatLng from, LatLng to) {
    const int segments = 14;
    final List<LatLng> points = [from];
    for (int i = 1; i <= segments; i++) {
      final t = i / segments;
      final offset = (i < segments ~/ 2 ? 0.002 : -0.001);
      final lat = from.latitude + (to.latitude - from.latitude) * t + offset;
      final lng = from.longitude + (to.longitude - from.longitude) * t;
      points.add(LatLng(lat, lng));
    }
    points.add(to);
    return points;
  }

  // ── Fetch Real Street Route (OSRM) ───────────
  Future<List<LatLng>> _fetchRealRoute(LatLng from, LatLng to) async {
    try {
      final url = 'https://router.project-osrm.org/route/v1/driving/${from.longitude},${from.latitude};${to.longitude},${to.latitude}?overview=full&geometries=geojson';
      final response = await http.get(Uri.parse(url)).timeout(const Duration(seconds: 4));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final coordinates = data['routes'][0]['geometry']['coordinates'] as List;
        return coordinates.map((c) => LatLng((c[1] as num).toDouble(), (c[0] as num).toDouble())).toList();
      }
    } catch (_) {}
    return _generateRouteFallback(from, to);
  }

  // ── Mock Ride Generator ─────────────────────
  Ride _generateMockRide({DateTime? overrideTime}) {
    final rng = Random();
    final pickup = _locations[rng.nextInt(_locations.length)];
    Map<String, dynamic> drop;
    do { drop = _locations[rng.nextInt(_locations.length)]; }
    while (drop['name'] == pickup['name']);

    final restIdx = rng.nextInt(_restaurants.length);
    final restaurant = _restaurants[restIdx];
    final items = _menuItems[restIdx];
    final pickedItems = (items.toList()..shuffle(rng)).take(rng.nextInt(2) + 1).toList();

    final pickupAddrs = _addresses[pickup['name']] ?? ['Main Road, ${pickup['name']}'];
    final dropAddrs = _addresses[drop['name']] ?? ['Main Road, ${drop['name']}'];
    final orderId = '#SW${rng.nextInt(9000) + 1000}';

    // Fare breakdown
    final baseFare = 30 + rng.nextInt(20);           // 30-50
    final distanceFare = (rng.nextDouble() * 8 + 2).round() * 8; // per km
    final surgeBonus = [0, 10, 15, 20, 25][rng.nextInt(5)];
    final tip = [0, 0, 0, 10, 15, 17, 20, 25, 30][rng.nextInt(9)];
    final totalEarnings = baseFare + distanceFare + surgeBonus + tip;
    final paymentModes = ['UPI', 'Cash', 'Card', 'Prepaid'];
    final rating = 3.5 + (rng.nextInt(16) * 0.1); // 3.5 - 5.0

    return Ride(
      pickupName: pickup['name'],
      pickupLat: pickup['lat'],
      pickupLng: pickup['lng'],
      dropName: drop['name'],
      dropLat: drop['lat'],
      dropLng: drop['lng'],
      status: 'assigned',
      startTime: overrideTime ?? DateTime.now(),
      distance: double.parse((rng.nextDouble() * 8 + 2).toStringAsFixed(1)),
      earnings: totalEarnings,
      restaurantName: restaurant['name'],
      restaurantAddress: pickupAddrs[rng.nextInt(pickupAddrs.length)],
      customerName: _customerNames[rng.nextInt(_customerNames.length)],
      customerAddress: dropAddrs[rng.nextInt(dropAddrs.length)],
      orderItems: pickedItems,
      orderId: orderId,
      baseFare: baseFare,
      distanceFare: distanceFare,
      surgeBonus: surgeBonus,
      tip: tip,
      paymentMode: paymentModes[rng.nextInt(paymentModes.length)],
      customerRating: double.parse(rating.toStringAsFixed(1)),
    );
  }

  // ── New Ride Kick-off ───────────────────────
  Future<void> _startNewRide() async {
    final ride = _generateMockRide();
    
    // Quick mount to render UI immediately before awaiting
    if (mounted) setState(() => currentRide = ride);

    final route = await _fetchRealRoute(ride.pickupLatLng, ride.dropLatLng);

    if (!mounted) return;

    if (route.length > 50) {
      // OSRM highly-dense route -> skip `subStep` interpolation or just do 2 steps quickly
      _subSteps = 2;
      _stepDuration = const Duration(milliseconds: 140);
    } else {
      // Minimal fallback route -> Smooth interpolation required
      _subSteps = 25;
      _stepDuration = const Duration(milliseconds: 80);
    }

    setState(() {
      currentRide = ride;
      routeCoordinates = route;
      riderPosition = route.first;
      _routeIndex = 0;
      _subStep = 0;
    });

    Future.delayed(const Duration(milliseconds: 400), () {
      if (mounted) _mapController.move(ride.pickupLatLng, 13.5);
    });

    // Phase: assigned → picked_up (2s) → on_the_way → begin movement
    Future.delayed(const Duration(seconds: 2), () {
      if (!mounted) return;
      setState(() => currentRide?.status = 'picked_up');
      Future.delayed(const Duration(seconds: 2), () {
        if (!mounted) return;
        setState(() => currentRide?.status = 'on_the_way');
        _beginMovement();
      });
    });
  }

  void _beginMovement() {
    _stepTimer?.cancel();
    _stepTimer = Timer.periodic(_stepDuration, (_) => _tick());
  }

  void _tick() {
    if (!mounted || currentRide == null) return;
    final route = routeCoordinates;

    if (_routeIndex >= route.length - 1) {
      _stepTimer?.cancel();
      setState(() {
        riderPosition = route.last;
        currentRide!.status = 'delivered';
        currentRide!.endTime = DateTime.now();
        completedRides.insert(0, currentRide!);
        // Sync to global notifier for active Profile history!
        globalCompletedRidesNotifier.value = List.from(completedRides);
        currentRide = null;
      });
      Future.delayed(const Duration(seconds: 5), () {
        if (mounted) _startNewRide();
      });
      return;
    }

    final from = route[_routeIndex];
    final to = route[_routeIndex + 1];
    final t = _subStep / _subSteps;

    setState(() {
      riderPosition = LatLng(
        from.latitude + (to.latitude - from.latitude) * t,
        from.longitude + (to.longitude - from.longitude) * t,
      );
    });

    if (_autoCenter) {
      try {
        _mapController.move(riderPosition, _mapController.camera.zoom);
      } catch (_) {}
    }

    _subStep++;
    if (_subStep >= _subSteps) { _subStep = 0; _routeIndex++; }
  }

  // ── Status helpers ──────────────────────────
  String _statusLabel(String s) {
    switch (s) {
      case 'assigned':   return 'Assigned';
      case 'picked_up':  return 'Picked Up';
      case 'on_the_way': return 'On The Way';
      case 'delivered':  return 'Delivered';
      default:           return s;
    }
  }

  Color _statusColor(String s) {
    switch (s) {
      case 'assigned':   return Colors.blue;
      case 'picked_up':  return AppColors.warning;
      case 'on_the_way': return AppColors.brandPrimary;
      case 'delivered':  return AppColors.success;
      default:           return AppColors.textMuted;
    }
  }

  // ─────────────────────────────────────────────
  // BUILD
  // ─────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: _buildAppBar(context),
      body: SingleChildScrollView(
        child: Column(
          children: [
            _buildTopSearch(),
            _buildSmartRiderToggle(),
            _buildHotspotCard(),
            _buildMapSection(),        // ← Live map (replaces static)
            _buildCompletedDeliveries(), // ← Completed list below map
            _buildAIForecastCard(),
            _buildSectionHeader('EARNINGS INTELLIGENCE'),
            _buildEarningsIntelCards(),
            _buildSectionHeader('RISK VS REWARD', badge: 'High Intensity'),
            _buildRiskRewardCard(),
            _buildSectionHeader('LIVE DRIVERS'),
            _buildLiveFactorsRow(),
            _buildForecastChart(),
            _buildAiStrategy(),
            _buildInsuranceAdvisory(),
            const SizedBox(height: 60),
          ],
        ),
      ),
    );
  }

  // ─────────────────────────────────────────────
  // LIVE MAP SECTION (replaces static map)
  // ─────────────────────────────────────────────
  Widget _buildMapSection() {
    final status = currentRide?.status ?? 'waiting';
    final statusColor = currentRide != null ? _statusColor(status) : AppColors.textMuted;
    final statusLabel = currentRide != null
        ? '${_statusLabel(status)}  ·  ${currentRide!.pickupName} → ${currentRide!.dropName}'
        : 'Waiting for orders in high-demand zones...';

    return Column(
      children: [
        // ── Demand Horizon Header ───────────────────────────────────────────
        Container(
          width: double.infinity,
          margin: const EdgeInsets.fromLTRB(20, 16, 20, 0),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFF111827),
            borderRadius: BorderRadius.circular(16),
            boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.1), blurRadius: 10)],
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(color: AppColors.brandPrimary.withOpacity(0.2), borderRadius: BorderRadius.circular(8)),
                child: const Icon(Icons.auto_graph_rounded, color: AppColors.brandPrimary, size: 20),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('DEMAND PREDICTION', style: AppTypography.small.copyWith(color: Colors.white.withOpacity(0.5), fontWeight: FontWeight.w800, letterSpacing: 1.2)),
                    const SizedBox(height: 2),
                    Text('Horizon: Next 2 Hours', style: AppTypography.bodyMedium.copyWith(color: Colors.white, fontWeight: FontWeight.w700)),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(color: AppColors.success.withOpacity(0.2), borderRadius: BorderRadius.circular(20)),
                child: Text('LIVE', style: AppTypography.small.copyWith(color: AppColors.success, fontWeight: FontWeight.w900, fontSize: 10)),
              ),
            ],
          ),
        ),

        // Status Banner (mini)
        Container(
          margin: const EdgeInsets.fromLTRB(20, 12, 20, 0),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
          decoration: BoxDecoration(
            color: statusColor.withOpacity(0.09),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: statusColor.withOpacity(0.25)),
          ),
          child: Row(
            children: [
              Container(
                width: 9,
                height: 9,
                decoration: BoxDecoration(
                  color: statusColor,
                  shape: BoxShape.circle,
                  boxShadow: [BoxShadow(color: statusColor.withOpacity(0.5), blurRadius: 5)],
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(statusLabel,
                    style: AppTypography.small.copyWith(
                        color: statusColor, fontWeight: FontWeight.w700)),
              ),
            ],
          ),
        ),

        // Map
        Container(
          height: 240,
          margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppColors.border),
            boxShadow: AppStyles.softShadow,
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(15),
            child: Stack(
              children: [
                Listener(
                  onPointerDown: (_) {
                    if (_autoCenter) {
                      setState(() => _autoCenter = false);
                    }
                  },
                  child: FlutterMap(
                    mapController: _mapController,
                  options: MapOptions(
                    initialCenter: riderPosition,
                    initialZoom: 13.5,
                  ),
                  children: [
                    TileLayer(
                      urlTemplate: 'https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
                      userAgentPackageName: 'com.figgy.app',
                    ),
                    // ── Hotspot Layers ───────────────────────────
                    CircleLayer(circles: [
                      // High Demand (Red)
                      CircleMarker(
                        point: const LatLng(13.0418, 80.2341), // T Nagar
                        color: Colors.red.withOpacity(0.3),
                        useRadiusInMeter: true,
                        radius: 800,
                      ),
                      // Medium Demand (Amber)
                      CircleMarker(
                        point: const LatLng(13.0850, 80.2101), // Anna Nagar
                        color: Colors.orange.withOpacity(0.25),
                        useRadiusInMeter: true,
                        radius: 1200,
                      ),
                      // Low Demand (Green)
                      CircleMarker(
                        point: const LatLng(12.9791, 80.2241), // Velachery
                        color: Colors.green.withOpacity(0.2),
                        useRadiusInMeter: true,
                        radius: 1000,
                      ),
                    ]),

                    // ── Route Polyline (Premium Glow Stack) ──────
                    PolylineLayer(
                      polylines: [
                        if (routeCoordinates.isNotEmpty)
                          Polyline(
                            points: routeCoordinates,
                            strokeWidth: 8.0,
                            color: AppColors.brandPrimary.withOpacity(0.15), // Soft Outer Glow
                            strokeCap: StrokeCap.round,
                            strokeJoin: StrokeJoin.round,
                          ),
                        if (routeCoordinates.isNotEmpty)
                          Polyline(
                            points: routeCoordinates,
                            strokeWidth: 4.5,
                            color: AppColors.brandPrimary, // Sharp Inner Core
                            strokeCap: StrokeCap.round,
                            strokeJoin: StrokeJoin.round,
                          ),
                      ],
                    ),

                    // Markers
                    MarkerLayer(markers: [
                      // Pickup
                      if (currentRide != null)
                        Marker(
                          point: currentRide!.pickupLatLng,
                          width: 32, height: 32,
                          child: const Icon(Icons.radio_button_checked_rounded,
                              color: Colors.green, size: 26),
                        ),
                      // Drop
                      if (currentRide != null)
                        Marker(
                          point: currentRide!.dropLatLng,
                          width: 32, height: 32,
                          child: const Icon(Icons.location_on_rounded,
                              color: AppColors.error, size: 30),
                        ),
                      // Rider (animated) ── CUSTOM REQUEST: Moped Icon + Specific Glow
                      Marker(
                        point: riderPosition,
                        width: 54, height: 54,
                        rotate: true,
                        child: Container(
                          decoration: BoxDecoration(
                            color: Colors.white,
                            shape: BoxShape.circle,
                            border: Border.all(color: Colors.white, width: 2),
                            boxShadow: [
                              BoxShadow(
                                color: const Color(0xFFFF8C42).withOpacity(0.4),
                                blurRadius: 12,
                                offset: const Offset(0, 4),
                              ),
                            ],
                          ),
                          padding: const EdgeInsets.all(8),
                          child: const Icon(
                            Icons.moped_rounded, // Improved scooter icon
                            color: Color(0xFFFF6A2A),
                            size: 26,
                          ),
                        ),
                      ),
                      // Hotspot Labels
                      ..._locations.take(3).map((loc) => Marker(
                        point: LatLng(loc['lat'], loc['lng']),
                        width: 80, height: 40,
                        child: GestureDetector(
                          onTap: () => _showZoneDetail(context, loc),
                          child: Column(
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(color: Colors.black.withOpacity(0.7), borderRadius: BorderRadius.circular(4)),
                                child: Text(loc['name'], style: const TextStyle(color: Colors.white, fontSize: 8, fontWeight: FontWeight.bold)),
                              ),
                              const Icon(Icons.local_fire_department, color: Colors.orange, size: 16),
                            ],
                          ),
                        ),
                      )),
                    ]),
                  ],
                ),
              ),
              if (!_autoCenter)
                Positioned(
                  bottom: 12,
                  right: 12,
                  child: FloatingActionButton.small(
                    backgroundColor: AppColors.surface,
                    elevation: 4,
                    child: const Icon(Icons.my_location_rounded, color: AppColors.brandPrimary),
                    onPressed: () {
                      setState(() => _autoCenter = true);
                      try {
                        _mapController.move(riderPosition, 14.5);
                      } catch (_) {}
                    },
                  ),
                ),
              // Zoom controls overlay (preserved from original)
              Positioned(
                  right: 8, top: 8,
                  child: Column(
                    children: [
                      _buildMapTool(Icons.add_rounded),
                      const SizedBox(height: 4),
                      _buildMapTool(Icons.remove_rounded),
                    ],
                  ),
                ),
                // Legend overlay
                Positioned(
                  bottom: 8, left: 8,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(8)),
                    child: Row(
                      children: [
                        const Icon(Icons.delivery_dining_rounded, color: AppColors.brandPrimary, size: 14),
                        const SizedBox(width: 4),
                        Text('Rider', style: AppTypography.small.copyWith(fontSize: 10)),
                        const SizedBox(width: 8),
                        const Icon(Icons.radio_button_checked_rounded, color: Colors.green, size: 12),
                        const SizedBox(width: 4),
                        Text('Pickup', style: AppTypography.small.copyWith(fontSize: 10)),
                        const SizedBox(width: 8),
                        const Icon(Icons.location_on_rounded, color: AppColors.error, size: 12),
                        const SizedBox(width: 4),
                        Text('Drop', style: AppTypography.small.copyWith(fontSize: 10)),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  // ─────────────────────────────────────────────
  // COMPLETED DELIVERIES (directly below map)
  // ─────────────────────────────────────────────
  Widget _buildCompletedDeliveries() {
    if (completedRides.isEmpty) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text('Completed Deliveries',
                  style: AppTypography.bodyLarge.copyWith(fontWeight: FontWeight.w800)),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: AppColors.success.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text('${completedRides.length} rides',
                    style: AppTypography.small.copyWith(
                        color: AppColors.success, fontWeight: FontWeight.w800, fontSize: 10)),
              ),
              const Spacer(),
              if (completedRides.length > 4)
                InkWell(
                  onTap: () => MainWrapper.of(context)?.setIndex(4),
                  child: Padding(
                    padding: const EdgeInsets.all(4.0),
                    child: Text('View History', style: AppTypography.small.copyWith(color: AppColors.brandPrimary, fontWeight: FontWeight.w800)),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 10),
          ListView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: min(completedRides.length, 4),
            itemBuilder: (ctx, i) {
              final ride = completedRides[i];
              final mins = ride.endTime!.difference(ride.startTime).inMinutes;
              return Card(
                margin: const EdgeInsets.only(bottom: 8),
                elevation: 0,
                color: AppColors.surface,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                  side: const BorderSide(color: AppColors.border),
                ),
                child: InkWell(
                  borderRadius: BorderRadius.circular(14),
                  onTap: () => _showRideDetail(ctx, ride),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    child: Row(
                      children: [
                        // Green check icon
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: AppColors.success.withOpacity(0.1),
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(Icons.check_circle_rounded,
                              color: AppColors.success, size: 20),
                        ),
                        const SizedBox(width: 12),
                        // Route & Stats
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '${ride.pickupName} → ${ride.dropName}',
                                style: AppTypography.bodySmall.copyWith(
                                    fontWeight: FontWeight.w800),
                              ),
                              const SizedBox(height: 3),
                              Text(
                                '${ride.distance.toStringAsFixed(1)} km  •  ₹${ride.earnings}  •  $mins mins',
                                style: AppTypography.small.copyWith(
                                    color: AppColors.textSecondary),
                              ),
                            ],
                          ),
                        ),
                        // Delivered badge
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: AppColors.success.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text('Delivered',
                              style: AppTypography.small.copyWith(
                                  color: AppColors.success,
                                  fontWeight: FontWeight.w800,
                                  fontSize: 10)),
                        ),
                        const SizedBox(width: 8),
                        // ➤ Chevron (View Full Detail)
                        const Icon(Icons.chevron_right_rounded,
                            color: AppColors.textMuted, size: 22),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  // ─────────────────────────────────────────────
  // RIDE DETAIL BOTTOM SHEET
  // ─────────────────────────────────────────────
  void _showRideDetail(BuildContext ctx, Ride ride) {
    final mins = ride.endTime!.difference(ride.startTime).inMinutes;
    final timeStr = '${ride.startTime.hour.toString().padLeft(2, '0')}:${ride.startTime.minute.toString().padLeft(2, '0')}';
    final endStr = '${ride.endTime!.hour.toString().padLeft(2, '0')}:${ride.endTime!.minute.toString().padLeft(2, '0')}';

    showModalBottomSheet(
      context: ctx,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (_) => DraggableScrollableSheet(
        initialChildSize: 0.92,
        maxChildSize: 0.96,
        minChildSize: 0.5,
        builder: (_, scrollCtrl) => Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: ListView(
            controller: scrollCtrl,
            padding: const EdgeInsets.fromLTRB(24, 16, 24, 36),
            children: [
              // Handle bar
              Center(
                child: Container(
                  width: 40, height: 4,
                  decoration: BoxDecoration(color: AppColors.border, borderRadius: BorderRadius.circular(2)),
                ),
              ),
              const SizedBox(height: 20),

              // ── HEADER ─────────────────────────────────
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(children: [
                    const Icon(Icons.check_circle_rounded, color: AppColors.success, size: 22),
                    const SizedBox(width: 8),
                    Text('DELIVERY COMPLETED', style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w900, letterSpacing: 0.5)),
                  ]),
                  Text(ride.orderId, style: AppTypography.small.copyWith(fontWeight: FontWeight.w800, color: AppColors.textMuted)),
                ],
              ),
              const Divider(height: 24, color: AppColors.border),
              Row(children: [
                const Icon(Icons.radio_button_checked_rounded, color: AppColors.success, size: 14),
                const SizedBox(width: 8),
                Text('Status: Delivered Successfully', style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w800, color: AppColors.textSecondary)),
              ]),

              const SizedBox(height: 28),

              // ── DELIVERY SUMMARY ─────────────────────
              _buildDetailSectionHeader('📊 DELIVERY SUMMARY'),
              _buildInfoRow('📍 Distance', '${ride.distance.toStringAsFixed(1)} km'),
              _buildInfoRow('⏱ Duration', '${mins < 1 ? "<1" : mins} mins'),
              _buildInfoRow('🕒 Order Time', '$timeStr → $endStr'),

              const SizedBox(height: 28),

              // ── EARNINGS BREAKDOWN ───────────────────
              _buildDetailSectionHeader('💰 EARNINGS BREAKDOWN'),
              _buildInfoRow('Base Fare', '₹${ride.baseFare}'),
              _buildInfoRow('Distance Fare', '₹${ride.distanceFare}'),
              _buildInfoRow('Surge Bonus', '₹${ride.surgeBonus}'),
              _buildInfoRow('Customer Tip', '₹${ride.tip}'),
              const Divider(height: 16, color: AppColors.border),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('💵 Total Earnings', style: AppTypography.bodyMedium.copyWith(fontWeight: FontWeight.w900)),
                  Text('₹${ride.earnings}', style: AppTypography.h3.copyWith(color: AppColors.success, fontSize: 20)),
                ],
              ),
              const Divider(height: 24, color: AppColors.border),

              // ── PICKUP DETAILS ───────────────────────
              _buildDetailSectionHeader('📦 PICKUP DETAILS'),
              _buildInfoRow('🏪 Hotel', ride.restaurantName, isBoldValue: true),
              _buildInfoRow('📍 Address', ride.restaurantAddress, maxLines: 2),
              _buildInfoRow('🕒 Picked Up At', timeStr),
              _buildInfoRow('🧾 Order ID', ride.orderId),
              _buildInfoRow('💳 Payment Mode', ride.paymentMode),

              const SizedBox(height: 28),

              // ── ORDER ITEMS ──────────────────────────
              _buildDetailSectionHeader('🍽 ORDER ITEMS'),
              ...ride.orderItems.map((item) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('• ', style: AppTypography.bodyMedium.copyWith(color: AppColors.textMuted, fontWeight: FontWeight.w800)),
                    Expanded(child: Text('$item ×1', style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w600))),
                  ],
                ),
              )),
              const SizedBox(height: 6),
              const Divider(height: 24, color: AppColors.border),

              // ── DELIVERY ROUTE ───────────────────────
              _buildDetailSectionHeader('🚚 DELIVERY ROUTE'),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Column(
                    children: [
                      Container(width: 12, height: 12, decoration: const BoxDecoration(color: Colors.green, shape: BoxShape.circle)),
                      Container(width: 2, height: 34, color: AppColors.border),
                      Container(width: 12, height: 12, decoration: BoxDecoration(color: AppColors.error, borderRadius: BorderRadius.circular(2))),
                    ],
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('${ride.restaurantName} (Pickup)', style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w800)),
                        const SizedBox(height: 8),
                        Text('${ride.distance.toStringAsFixed(1)} km • $mins mins', style: AppTypography.small.copyWith(color: AppColors.textMuted)),
                        const SizedBox(height: 8),
                        Text('${ride.customerName} (Drop)', style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w800)),
                      ],
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 28),

              // ── DELIVERY DETAILS ─────────────────────
              _buildDetailSectionHeader('📍 DELIVERY DETAILS'),
              _buildInfoRow('👤 Customer', ride.customerName, isBoldValue: true),
              _buildInfoRow('📍 Address', ride.customerAddress, maxLines: 2),
              _buildInfoRow('🕒 Delivered At', endStr),
              _buildInfoRow('⭐ Customer Rating', '${ride.customerRating}'),
              _buildInfoRow('💰 Tip Received', '₹${ride.tip}'),

              const SizedBox(height: 36),

              // ── CLOSE BUTTON ─────────────────────────
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () => Navigator.pop(ctx),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.brandPrimary,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    elevation: 0,
                  ),
                  child: Text('CLOSE DELIVERY', style: AppTypography.bodySmall.copyWith(color: Colors.white, fontWeight: FontWeight.w900, letterSpacing: 1.0)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDetailSectionHeader(String title) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w900, letterSpacing: 0.5)),
        const Divider(height: 16, color: AppColors.border),
      ],
    );
  }

  Widget _buildInfoRow(String label, String value, {bool isBoldValue = false, int maxLines = 1}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 130,
            child: Text(label, style: AppTypography.bodySmall.copyWith(color: AppColors.textSecondary, fontWeight: FontWeight.w600)),
          ),
          const SizedBox(width: 8),
          const Text(':  ', style: TextStyle(color: AppColors.textMuted, fontWeight: FontWeight.w600)),
          Expanded(
            child: Text(
              value,
              maxLines: maxLines,
              overflow: TextOverflow.ellipsis,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.textPrimary,
                fontWeight: isBoldValue ? FontWeight.w800 : FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
  // ─────────────────────────────────────────────

  // ALL ORIGINAL WIDGETS BELOW (UNCHANGED)
  // ─────────────────────────────────────────────
  PreferredSizeWidget _buildAppBar(BuildContext context) {
    return AppBar(
      backgroundColor: AppColors.surface,
      elevation: 0,
      leading: Padding(
        padding: const EdgeInsets.only(left: 16.0),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: Image.asset('logo.png'),
        ),
      ),
      title: Text(
        'FIGGY',
        style: AppTypography.h1.copyWith(
          color: AppColors.brandPrimary,
          fontSize: 22,
          fontWeight: FontWeight.w900,
          letterSpacing: 1.0,
        ),
      ),
      actions: [
        IconButton(icon: const Icon(Icons.notifications_none_rounded, color: AppColors.textPrimary), onPressed: () {}),
        Padding(
          padding: const EdgeInsets.only(right: 12),
          child: IconButton(icon: const Icon(Icons.menu_rounded, color: AppColors.textPrimary), onPressed: () {}),
        ),
      ],
      bottom: PreferredSize(
        preferredSize: const Size.fromHeight(1),
        child: Container(color: AppColors.border, height: 1),
      ),
    );
  }

  Widget _buildTopSearch() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            height: 48,
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: AppColors.border),
              boxShadow: AppStyles.softShadow,
            ),
            child: Row(
              children: [
                const Icon(Icons.search_rounded, color: AppColors.brandPrimary),
                const SizedBox(width: 12),
                Text('Search demand zones...', style: AppTypography.bodyMedium.copyWith(color: AppColors.textMuted)),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            decoration: BoxDecoration(
              color: AppColors.brandPrimary.withOpacity(0.1),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.my_location_rounded, color: AppColors.brandPrimary, size: 14),
                const SizedBox(width: 6),
                Text('Current Location', style: AppTypography.small.copyWith(color: AppColors.brandPrimary, fontWeight: FontWeight.w700)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSmartRiderToggle() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
        boxShadow: AppStyles.softShadow,
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(color: AppColors.brandPrimary.withOpacity(0.1), shape: BoxShape.circle),
            child: const Icon(Icons.smart_toy_rounded, color: AppColors.brandPrimary, size: 20),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Smart Rider Mode', style: AppTypography.bodyMedium.copyWith(fontWeight: FontWeight.w800)),
                Text('High Earnings vs Safety', style: AppTypography.small.copyWith(color: AppColors.textSecondary)),
              ],
            ),
          ),
          Switch(
            value: _smartMode,
            onChanged: (val) => setState(() => _smartMode = val),
            activeColor: AppColors.brandPrimary,
          ),
        ],
      ),
    );
  }

  Widget _buildHotspotCard() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFFFF8B5E), AppColors.brandPrimary],
          begin: Alignment.topLeft, end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [BoxShadow(color: AppColors.brandPrimary.withOpacity(0.3), blurRadius: 10, offset: const Offset(0, 4))],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('ACTIVE HOTSPOT', style: AppTypography.small.copyWith(color: Colors.white70, fontWeight: FontWeight.w800, letterSpacing: 1.0)),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(color: Colors.white.withOpacity(0.2), borderRadius: BorderRadius.circular(12)),
                child: Text('HIGH DEMAND', style: AppTypography.small.copyWith(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 9)),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text('T Nagar, Chennai', style: AppTypography.h3.copyWith(color: Colors.white, fontSize: 22)),
          const SizedBox(height: 20),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  RichText(text: TextSpan(children: [
                    TextSpan(text: '450 ', style: AppTypography.h1.copyWith(color: Colors.white, fontSize: 32)),
                    TextSpan(text: 'orders/hr', style: AppTypography.bodySmall.copyWith(color: Colors.white)),
                  ])),
                  const SizedBox(height: 4),
                  Text('Level: 9.8/10 Extreme High', style: AppTypography.small.copyWith(color: Colors.white70)),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
                child: Text('Live Peak', style: AppTypography.bodySmall.copyWith(color: AppColors.brandPrimary, fontWeight: FontWeight.w800)),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMapTool(IconData icon) {
    return Container(
      width: 32, height: 32,
      decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(8), boxShadow: AppStyles.softShadow),
      child: Icon(icon, color: AppColors.textPrimary, size: 18),
    );
  }

  Widget _buildAIForecastCard() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(16), border: Border.all(color: AppColors.border), boxShadow: AppStyles.softShadow),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: AppColors.brandPrimary.withOpacity(0.1), shape: BoxShape.circle),
            child: const Icon(Icons.auto_awesome_rounded, color: AppColors.brandPrimary),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('AI FORECAST', style: AppTypography.small.copyWith(color: AppColors.brandPrimary, fontWeight: FontWeight.w800, fontSize: 10, letterSpacing: 0.5)),
                const SizedBox(height: 4),
                Text('High demand expected in T Nagar from 7:00 PM to 9:00 PM today', style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w600, height: 1.3)),
              ],
            ),
          ),
          const SizedBox(width: 12),
          ElevatedButton(
            onPressed: () {},
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.brandPrimary, elevation: 0, padding: const EdgeInsets.symmetric(horizontal: 16), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8))),
            child: Text('MOVE TO ZONE', style: AppTypography.small.copyWith(color: Colors.white, fontWeight: FontWeight.w800)),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(String title, {String? badge}) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(title, style: AppTypography.small.copyWith(color: AppColors.textSecondary, fontWeight: FontWeight.w800, letterSpacing: 1.0)),
          if (badge != null)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(color: AppColors.warning.withOpacity(0.1), borderRadius: BorderRadius.circular(12)),
              child: Text(badge, style: AppTypography.small.copyWith(color: AppColors.warning, fontWeight: FontWeight.w800, fontSize: 9)),
            ),
        ],
      ),
    );
  }

  Widget _buildEarningsIntelCards() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(16), border: Border.all(color: AppColors.border), boxShadow: AppStyles.softShadow),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('Average Base', style: AppTypography.small.copyWith(color: AppColors.textSecondary, fontWeight: FontWeight.w600)),
                      const SizedBox(height: 4),
                      RichText(text: TextSpan(children: [
                        TextSpan(text: '₹120', style: AppTypography.h3.copyWith(fontWeight: FontWeight.w900, color: AppColors.textPrimary)),
                        TextSpan(text: '/hr', style: AppTypography.bodySmall.copyWith(color: AppColors.textSecondary)),
                      ])),
                    ]),
                    Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                      Text('AI Prediction', style: AppTypography.small.copyWith(color: AppColors.brandPrimary, fontWeight: FontWeight.w800)),
                      const SizedBox(height: 4),
                      RichText(text: TextSpan(children: [
                        TextSpan(text: '₹220', style: AppTypography.h3.copyWith(color: AppColors.brandPrimary, fontWeight: FontWeight.w900)),
                        TextSpan(text: '/hr', style: AppTypography.bodySmall.copyWith(color: AppColors.brandPrimary)),
                      ])),
                    ]),
                  ],
                ),
                const SizedBox(height: 16),
                Stack(alignment: Alignment.centerLeft, children: [
                  Container(height: 8, decoration: BoxDecoration(color: AppColors.border, borderRadius: BorderRadius.circular(4))),
                  FractionallySizedBox(widthFactor: 0.83, child: Container(height: 8, decoration: BoxDecoration(color: AppColors.brandPrimary, borderRadius: BorderRadius.circular(4)))),
                ]),
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('+₹100/hr Potential Boost', style: AppTypography.small.copyWith(color: AppColors.brandPrimary, fontWeight: FontWeight.w800)),
                    Text('83% Confidence', style: AppTypography.small.copyWith(color: AppColors.textSecondary)),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(child: _buildSmallCard(Icons.bolt_rounded, AppColors.brandPrimary, 'SURGE PREDICTION', '₹30', '/order', 'Window: 7 PM - 9 PM')),
              const SizedBox(width: 12),
              Expanded(child: _buildSmallCard(Icons.shield_rounded, Colors.blueAccent, 'INSURANCE', '₹350', ' cover', 'Parametric Active')),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSmallCard(IconData icon, Color color, String tag, String value, String unit, String sub) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(16), border: Border.all(color: AppColors.border), boxShadow: AppStyles.softShadow),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(icon, color: color, size: 14),
          const SizedBox(width: 4),
          Text(tag, style: AppTypography.small.copyWith(color: color, fontWeight: FontWeight.w800, fontSize: 8)),
        ]),
        const SizedBox(height: 12),
        RichText(text: TextSpan(children: [
          TextSpan(text: value, style: AppTypography.h2.copyWith(fontWeight: FontWeight.w900, color: AppColors.textPrimary, fontSize: 20)),
          TextSpan(text: unit, style: AppTypography.small.copyWith(color: AppColors.textSecondary)),
        ])),
        const SizedBox(height: 6),
        Text(sub, style: AppTypography.small.copyWith(color: color, fontSize: 10)),
      ]),
    );
  }

  Widget _buildRiskRewardCard() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(16), border: Border.all(color: AppColors.border), boxShadow: AppStyles.softShadow),
      child: Column(children: [
        Stack(alignment: Alignment.center, children: [
          Container(height: 4, decoration: BoxDecoration(borderRadius: BorderRadius.circular(2), gradient: const LinearGradient(colors: [AppColors.success, AppColors.brandPrimary, AppColors.error]))),
          const Align(alignment: Alignment(0.6, 0), child: CircleAvatar(radius: 8, backgroundColor: Colors.white, child: CircleAvatar(radius: 6, backgroundColor: Colors.transparent))),
        ]),
        const SizedBox(height: 16),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(children: [
              const Icon(Icons.water_drop_rounded, color: Colors.blueAccent, size: 14),
              const SizedBox(width: 4),
              Text('Rain: 70%', style: AppTypography.small.copyWith(fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
            ]),
            Row(children: [
              const Icon(Icons.trending_up_rounded, color: AppColors.brandPrimary, size: 14),
              const SizedBox(width: 4),
              Text('Surge: High', style: AppTypography.small.copyWith(fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
            ]),
          ],
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: AppColors.background, borderRadius: BorderRadius.circular(8)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('"System suggests: High risk but high reward strategy"', style: AppTypography.small.copyWith(fontStyle: FontStyle.italic, color: AppColors.textSecondary)),
            const SizedBox(height: 8),
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
              Text('+₹150 earnings increase', style: AppTypography.small.copyWith(color: AppColors.success, fontWeight: FontWeight.w800, fontSize: 10)),
              Text('Moderate disruption risk', style: AppTypography.small.copyWith(color: AppColors.error, fontWeight: FontWeight.w800, fontSize: 10)),
            ]),
          ]),
        ),
      ]),
    );
  }

  Widget _buildLiveFactorsRow() {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Row(children: [
        _buildFactorCard(Icons.cloudy_snowing, Colors.blueAccent, 'Weather', 'Rain in 2h'),
        const SizedBox(width: 12),
        _buildFactorCard(Icons.sports_cricket_rounded, AppColors.brandPrimary, 'Local Event', 'Cricket match'),
        const SizedBox(width: 12),
        _buildFactorCard(Icons.stadium_rounded, AppColors.brandAccent, 'Festival', 'Temple event'),
      ]),
    );
  }

  Widget _buildFactorCard(IconData icon, Color color, String title, String subtitle) {
    return Container(
      width: 110, padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(16), border: Border.all(color: AppColors.border), boxShadow: AppStyles.softShadow),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(icon, color: color, size: 24),
        const SizedBox(height: 12),
        Text(title, style: AppTypography.small.copyWith(fontWeight: FontWeight.w800, color: AppColors.textPrimary)),
        const SizedBox(height: 2),
        Text(subtitle, style: AppTypography.small.copyWith(color: AppColors.textSecondary, fontSize: 10)),
      ]),
    );
  }

  Widget _buildForecastChart() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(16), border: Border.all(color: AppColors.border), boxShadow: AppStyles.softShadow),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('2 Hour Forecast', style: AppTypography.bodyLarge.copyWith(fontWeight: FontWeight.w800)),
            Row(children: [
              const Icon(Icons.arrow_upward_rounded, color: AppColors.success, size: 14),
              const SizedBox(width: 4),
              Text('+24% Trend', style: AppTypography.small.copyWith(color: AppColors.success, fontWeight: FontWeight.w800)),
            ]),
          ],
        ),
        const SizedBox(height: 24),
        Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: [
            _buildChartBar('5PM', 0.2, AppColors.border.withOpacity(0.5)),
            _buildChartBar('6PM', 0.4, AppColors.border),
            _buildChartBar('7PM', 0.6, const Color(0xFFFFBCA3)),
            _buildChartBar('8PM', 1.0, AppColors.brandPrimary),
            _buildChartBar('9PM', 0.1, Colors.transparent),
          ],
        ),
      ]),
    );
  }

  Widget _buildChartBar(String label, double fillPct, Color color) {
    return Column(children: [
      Container(height: 80 * fillPct, width: 38, decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(6))),
      const SizedBox(height: 12),
      Text(label, style: AppTypography.small.copyWith(color: AppColors.textMuted, fontWeight: FontWeight.w700, fontSize: 10)),
    ]);
  }

  Widget _buildAiStrategy() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: const Color(0xFF0F172A), borderRadius: BorderRadius.circular(16), boxShadow: AppStyles.softShadow),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.lightbulb_rounded, color: AppColors.brandPrimary, size: 18),
          const SizedBox(width: 8),
          Text('AI STRATEGY SUGGESTIONS', style: AppTypography.small.copyWith(color: Colors.white, fontWeight: FontWeight.w800, letterSpacing: 0.5)),
        ]),
        const SizedBox(height: 16),
        _buildBullet('Move to T Nagar before 7 PM to catch the initial surge window.'),
        const SizedBox(height: 12),
        _buildBullet('Heavy rain may increase demand; ensure rain gear is ready for higher tips.'),
      ]),
    );
  }

  Widget _buildBullet(String text) {
    return Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Padding(padding: const EdgeInsets.only(top: 6), child: Container(width: 5, height: 5, decoration: const BoxDecoration(color: AppColors.brandPrimary, shape: BoxShape.circle))),
      const SizedBox(width: 12),
      Expanded(child: Text(text, style: AppTypography.small.copyWith(color: Colors.white70, height: 1.4))),
    ]);
  }

  Widget _buildInsuranceAdvisory() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: Colors.blueAccent.withOpacity(0.08), borderRadius: BorderRadius.circular(16), border: Border.all(color: Colors.blueAccent.withOpacity(0.2))),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Icon(Icons.info_rounded, color: Colors.blueAccent, size: 20),
        const SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('INSURANCE ADVISORY', style: AppTypography.small.copyWith(color: Colors.blueAccent, fontWeight: FontWeight.w800, letterSpacing: 0.5)),
          const SizedBox(height: 6),
          Text('Rain disruption likely in 2h. Parametric insurance may activate.', style: AppTypography.small.copyWith(color: AppColors.textPrimary, height: 1.4)),
          const SizedBox(height: 6),
          Text('Estimated coverage: ₹350', style: AppTypography.small.copyWith(color: Colors.blueAccent, fontWeight: FontWeight.w800)),
        ])),
      ]),
    );
  }

  // ── Zone Detail Bottom Sheet ────────────────
  void _showZoneDetail(BuildContext context, Map<String, dynamic> loc) {
    final rng = Random();
    final orders = rng.nextInt(40) + 10;
    final bonus = (rng.nextInt(5) + 1) * 10;
    
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (_) => Container(
        padding: const EdgeInsets.all(24),
        decoration: const BoxDecoration(color: Colors.white, borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(loc['name'], style: AppTypography.h2.copyWith(fontSize: 22, color: AppColors.textPrimary)),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(color: Colors.red.withOpacity(0.1), borderRadius: BorderRadius.circular(20)),
                  child: Text('HIGH DEMAND', style: AppTypography.small.copyWith(color: Colors.red, fontWeight: FontWeight.w900, fontSize: 10)),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Text('Forecast for next 2 hours based on historical patterns and live app traffic.', 
                 style: AppTypography.bodySmall.copyWith(color: AppColors.textSecondary)),
            const SizedBox(height: 24),
            Row(
              children: [
                _buildZoneStat('ORDERS', '$orders', Icons.shopping_bag_outlined),
                const SizedBox(width: 16),
                _buildZoneStat('EST. BONUS', '₹$bonus/hr', Icons.currency_rupee_rounded),
              ],
            ),
            const SizedBox(height: 32),
            SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton(
                onPressed: () => Navigator.pop(context),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.brandPrimary,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.directions_outlined, color: Colors.white),
                    const SizedBox(width: 12),
                    Text('NAVIGATE TO ZONE', style: AppTypography.bodyMedium.copyWith(color: Colors.white, fontWeight: FontWeight.bold)),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildZoneStat(String label, String value, IconData icon) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: AppColors.background, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.border)),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: AppColors.brandPrimary, size: 20),
            const SizedBox(height: 8),
            Text(label, style: AppTypography.small.copyWith(fontSize: 10, color: AppColors.textSecondary)),
            Text(value, style: AppTypography.h3.copyWith(fontSize: 18, color: AppColors.textPrimary)),
          ],
        ),
      ),
    );
  }
}
