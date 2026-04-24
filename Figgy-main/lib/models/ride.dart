import 'package:flutter/material.dart';
import 'package:latlong2/latlong.dart';

// ─────────────────────────────────────────────────────
// GLOBAL COMPLETED RIDES NOTIFIER
// ─────────────────────────────────────────────────────
final ValueNotifier<List<Ride>> globalCompletedRidesNotifier = ValueNotifier<List<Ride>>([]);

// ─────────────────────────────────────────────────────
// RIDE DATA MODEL
// ─────────────────────────────────────────────────────
class Ride {
  final String pickupName;
  final double pickupLat;
  final double pickupLng;
  final String dropName;
  final double dropLat;
  final double dropLng;
  String status;
  final DateTime startTime;
  DateTime? endTime;
  final double distance;
  final int earnings;

  // ── Rich Job Details ─────────────────────────
  final String restaurantName;
  final String restaurantAddress;
  final String customerName;
  final String customerAddress;
  final List<String> orderItems;
  final String orderId;

  // ── Earnings Breakdown ─────────────────────
  final int baseFare;
  final int distanceFare;
  final int surgeBonus;
  final int tip;
  final String paymentMode;
  final double customerRating;

  Ride({
    required this.pickupName,
    required this.pickupLat,
    required this.pickupLng,
    required this.dropName,
    required this.dropLat,
    required this.dropLng,
    required this.status,
    required this.startTime,
    required this.distance,
    required this.earnings,
    required this.restaurantName,
    required this.restaurantAddress,
    required this.customerName,
    required this.customerAddress,
    required this.orderItems,
    required this.orderId,
    required this.baseFare,
    required this.distanceFare,
    required this.surgeBonus,
    required this.tip,
    required this.paymentMode,
    required this.customerRating,
    this.endTime,
  });

  LatLng get pickupLatLng => LatLng(pickupLat, pickupLng);
  LatLng get dropLatLng => LatLng(dropLat, dropLng);
}
