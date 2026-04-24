/// api_service.dart
/// -----------------
/// Central HTTP client for the Figgy Flutter app.
/// All communication with the Flask backend goes through this class.
///
/// Base URL: http://10.0.2.2:5000 (Android emulator → localhost)
///           http://localhost:5000  (web / desktop)
///
/// Sections:
///   - Worker
///   - Payment (Razorpay order creation)
///   - Claims  ← added in this session

import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:figgy_app/config/api_base_url.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

// ---------------------------------------------------------------------------
// Custom exception used across all API calls
// ---------------------------------------------------------------------------
class ApiException implements Exception {
  final String message;
  final int? statusCode;

  const ApiException(this.message, {this.statusCode});

  @override
  String toString() => 'ApiException($statusCode): $message';
}

// ---------------------------------------------------------------------------
// ApiService
// ---------------------------------------------------------------------------
class ApiService {
  // Base URL: see [figgyApiBaseUrl] in lib/config/api_base_url.dart
  static final String _baseUrl = figgyApiBaseUrl;

  static const Map<String, String> _jsonHeaders = {
    'Content-Type': 'application/json',
    'Accept':       'application/json',
  };

  static const Duration _timeout = Duration(seconds: 25);

  // ─────────────────────────────────────────────────────────────────────────
  // WORKER
  // ─────────────────────────────────────────────────────────────────────────

  /// Register or fetch a worker.
  Future<Map<String, dynamic>> fetchWorker(String workerId) async {
    final uri = Uri.parse('$_baseUrl/api/worker/$workerId');
    try {
      final response = await http.get(uri, headers: _jsonHeaders)
          .timeout(_timeout);
      final body = json.decode(response.body) as Map<String, dynamic>;
      if (response.statusCode == 200) return body;
      throw ApiException(
        body['message'] ?? 'Failed to fetch worker',
        statusCode: response.statusCode,
      );
    } catch (e) {
      debugPrint('[ApiService.fetchWorker] Error: $e');
      rethrow;
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // PAYMENT
  // ─────────────────────────────────────────────────────────────────────────

  /// Create a Razorpay order for GigShield activation.
  Future<Map<String, dynamic>> createOrder(Map<String, dynamic> payload) async {
    final uri = Uri.parse('$_baseUrl/api/payment/create_order');
    try {
      final response = await http.post(
        uri,
        headers: _jsonHeaders,
        body: json.encode(payload),
      ).timeout(_timeout);
      final body = json.decode(response.body) as Map<String, dynamic>;
      if (response.statusCode == 200 || response.statusCode == 201) return body;
      throw ApiException(
        body['message'] ?? 'Failed to create order',
        statusCode: response.statusCode,
      );
    } catch (e) {
      debugPrint('[ApiService.createOrder] Error: $e');
      rethrow;
    }
  }

  /// POST /api/worker/update_profile
  /// Updates UPI ID or other worker metadata.
  Future<Map<String, dynamic>> updateWorkerProfile(String workerId, Map<String, dynamic> data) async {
    final uri = Uri.parse('$_baseUrl/api/worker/update_profile');
    try {
      final response = await http.post(
        uri,
        headers: _jsonHeaders,
        body: json.encode({'worker_id': workerId, ...data}),
      ).timeout(_timeout);
      final body = json.decode(response.body) as Map<String, dynamic>;
      if (response.statusCode == 200) return body;
      throw ApiException(body['message'] ?? 'Profile update failed', statusCode: response.statusCode);
    } catch (e) {
      debugPrint('[ApiService.updateWorkerProfile] Error: $e');
      rethrow;
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // CLAIMS
  // ─────────────────────────────────────────────────────────────────────────

  /// POST /api/claim/manual
  ///
  /// Called when worker taps "Submit" in manual_claim_screen.dart.
  ///
  /// [claimData] must include:
  ///   worker_id, claim_type, start_time, end_time, estimated_loss
  /// Optional: description, proof_urls
  ///
  /// Returns: { claim_id, claim_status, message }
  Future<Map<String, dynamic>> submitManualClaim(
    Map<String, dynamic> claimData,
  ) async {
    final uri = Uri.parse('$_baseUrl/api/claim/manual');
    try {
      final response = await http.post(
        uri,
        headers: _jsonHeaders,
        body: json.encode(claimData),
      ).timeout(_timeout);

      final body = json.decode(response.body) as Map<String, dynamic>;

      if (response.statusCode == 201) return body;

      // Server returned a structured error
      throw ApiException(
        body['message'] ?? 'Failed to submit claim',
        statusCode: response.statusCode,
      );
    } on http.ClientException catch (e) {
      throw ApiException('Network error: ${e.message}');
    } catch (e) {
      if (e.toString().contains('SocketException') || e.toString().contains('Connection refused')) {
        throw const ApiException('Backend server offline. Is Flask running?');
      }
      debugPrint('[ApiService.submitManualClaim] Error: $e');
      rethrow;
    }
  }

  /// GET /api/claim/status/:claimId
  ///
  /// Called every 5 seconds by claim_processing_screen.dart to poll
  /// the claim lifecycle.
  ///
  /// Returns full claim dict including status, eligible_payout, fraud_risk.
  /// Throws ApiException("Claim not found") on 404.
  Future<Map<String, dynamic>> pollClaimStatus(String claimId) async {
    final uri = Uri.parse('$_baseUrl/api/claim/status/$claimId');
    try {
      final response = await http.get(uri, headers: _jsonHeaders)
          .timeout(_timeout);

      final body = json.decode(response.body) as Map<String, dynamic>;

      if (response.statusCode == 200) return body;
      if (response.statusCode == 404) {
        throw const ApiException('Claim not found', statusCode: 404);
      }

      throw ApiException(
        body['message'] ?? 'Failed to fetch claim status',
        statusCode: response.statusCode,
      );
    } on http.ClientException catch (e) {
      throw ApiException('Network error during poll: ${e.message}');
    } catch (e) {
      if (e.toString().contains('SocketException')) {
        throw const ApiException('Server connection lost. Retrying...');
      }
      debugPrint('[ApiService.pollClaimStatus] $claimId — Error: $e');
      rethrow;
    }
  }

  /// GET /api/claim/list/:workerId
  ///
  /// Returns payout history for Shield / claims dashboards.
  /// List is sorted newest-first by the backend.
  ///
  /// Returns: List of claim summary maps.
  Future<List<Map<String, dynamic>>> getClaimList(String workerId) async {
    final uri = Uri.parse('$_baseUrl/api/claim/list/$workerId');
    try {
      final response = await http.get(uri, headers: _jsonHeaders)
          .timeout(_timeout);

      final body = json.decode(response.body) as Map<String, dynamic>;

      if (response.statusCode == 200) {
        final rawList = body['claims'] as List<dynamic>? ?? [];
        return rawList
            .map((e) => Map<String, dynamic>.from(e as Map))
            .toList();
      }

      throw ApiException(
        body['message'] ?? 'Failed to fetch claim list',
        statusCode: response.statusCode,
      );
    } catch (e) {
      debugPrint('[ApiService.getClaimList] $workerId — Error: $e');
      rethrow;
    }
  }

  /// POST /api/claim/auto_trigger  [DEMO / INTERNAL TESTING ONLY]
  ///
  /// Simulates the APScheduler weather trigger from within the app.
  /// Used for hackathon demos — injects 52mm/hr rain into a zone.
  ///
  /// [zone] — one of: "North", "South", "East", "West", "Central"
  Future<Map<String, dynamic>> submitAutoClaim({
    String zone = 'North',
    double rainMmHr = 52.0,
    double tempC = 36.0,
    int aqi = 350,
  }) async {
    final uri = Uri.parse('$_baseUrl/api/claim/auto_trigger');
    final payload = {
      'zone':       zone,
      'rain_mm_hr': rainMmHr,
      'temp_c':     tempC,
      'aqi':        aqi,
      'timestamp':  DateTime.now().toUtc().toIso8601String(),
    };

    try {
      final response = await http.post(
        uri,
        headers: _jsonHeaders,
        body: json.encode(payload),
      ).timeout(_timeout);

      final body = json.decode(response.body) as Map<String, dynamic>;

      if (response.statusCode == 200) return body;

      throw ApiException(
        body['message'] ?? 'Auto trigger failed',
        statusCode: response.statusCode,
      );
    } catch (e) {
      debugPrint('[ApiService.submitAutoClaim] zone=$zone — Error: $e');
      rethrow;
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // WEATHER
  // ─────────────────────────────────────────────────────────────────────────

  /// GET /api/demand/zone/:zone
  ///
  /// Returns zone demand index and recommendation flags for dispatch logic.
  Future<Map<String, dynamic>> getZoneDemand(String zone) async {
    final uri = Uri.parse('$_baseUrl/api/demand/zone/$zone');
    try {
      final response = await http.get(uri, headers: _jsonHeaders).timeout(_timeout);
      final body = json.decode(response.body) as Map<String, dynamic>;
      if (response.statusCode == 200) return body;

      throw ApiException(
        body['message'] ?? 'Failed to fetch zone demand',
        statusCode: response.statusCode,
      );
    } catch (e) {
      debugPrint('[ApiService.getZoneDemand] $zone — Error: $e');
      rethrow;
    }
  }

  /// GET /api/weather/zone/:zoneName
  ///
  /// Called by the radar feature (`features/radar/radar_screen.dart`) for live weather and
  /// disruption status for the worker's current delivery zone.
  ///
  /// Returns: { zone, rain_mm_hr, temp_c, aqi, disruption_triggered,
  ///            trigger_type, trigger_label, last_updated }
  Future<Map<String, dynamic>> getZoneWeather(String zoneName) async {
    final uri = Uri.parse('$_baseUrl/api/weather/zone/$zoneName');
    try {
      final response = await http.get(uri, headers: _jsonHeaders)
          .timeout(_timeout);

      final body = json.decode(response.body) as Map<String, dynamic>;

      if (response.statusCode == 200) return body;

      throw ApiException(
        body['error'] ?? 'Failed to fetch weather data',
        statusCode: response.statusCode,
      );
    } catch (e) {
      debugPrint('[ApiService.getZoneWeather] $zoneName — Error: $e');
      rethrow;
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // DEMO TRIGGER
  // ─────────────────────────────────────────────────────────────────────────

  /// POST /api/demo/trigger_rain
  ///
  /// Forces a synchronous rain trigger for the hackathon demo.
  Future<Map<String, dynamic>> triggerDemoRain(String zoneName) async {
    final uri = Uri.parse('$_baseUrl/api/demo/trigger_rain');
    try {
      final prefs = await SharedPreferences.getInstance();
      final workerId = prefs.getString('worker_id');
      
      final payload = {
        'zone': zoneName,
        'rain_mm_hr': 55.0,
      };
      if (workerId != null) {
        payload['worker_id'] = workerId;
      }

      final response = await http.post(
        uri, 
        headers: _jsonHeaders,
        body: json.encode(payload),
      ).timeout(_timeout);

      final body = json.decode(response.body) as Map<String, dynamic>;

      if (response.statusCode == 200) return body;

      throw ApiException(
        body['message'] ?? 'Failed to trigger demo rain',
        statusCode: response.statusCode,
      );
    } catch (e) {
      debugPrint('[ApiService.triggerDemoRain] $zoneName — Error: $e');
      rethrow;
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // NOTIFICATIONS
  // ─────────────────────────────────────────────────────────────────────────

  /// POST /api/worker/update_fcm_token
  Future<void> updateFcmToken(String token) async {
    final uri = Uri.parse('$_baseUrl/api/worker/update_fcm_token');
    try {
      final prefs = await SharedPreferences.getInstance();
      final workerId = prefs.getString('worker_id');
      if (workerId == null) return;
      
      await http.post(
        uri, 
        headers: _jsonHeaders,
        body: json.encode({
          'worker_id': workerId,
          'fcm_token': token,
        }),
      ).timeout(_timeout);
    } catch (e) {
      debugPrint('[ApiService.updateFcmToken] Error: $e');
    }
  }
  /// POST /api/claim/retry_payment/:claimId
  ///
  /// Re-triggers a failed payout after the worker fixes their UPI ID.
  Future<Map<String, dynamic>> retryPayment(String claimId) async {
    final uri = Uri.parse('$_baseUrl/api/claim/retry_payment/$claimId');
    try {
      final response = await http.post(uri, headers: _jsonHeaders).timeout(_timeout);
      final body = json.decode(response.body) as Map<String, dynamic>;
      if (response.statusCode == 200) return body;
      throw ApiException(body['message'] ?? 'Failed to retry payment');
    } catch (e) {
      debugPrint('[ApiService.retryPayment] $claimId — Error: $e');
      rethrow;
    }
  }

  /// POST /api/claim/appeal/:claimId
  ///
  /// Disputes a rejected claim by providing a worker statement.
  Future<Map<String, dynamic>> appealClaim(String claimId, {required String statement}) async {
    final uri = Uri.parse('$_baseUrl/api/claim/appeal/$claimId');
    final bodyData = json.encode({'worker_statement': statement});
    try {
      final response = await http.post(uri, headers: _jsonHeaders, body: bodyData).timeout(_timeout);
      final body = json.decode(response.body) as Map<String, dynamic>;
      if (response.statusCode == 201) return body;
      throw ApiException(body['message'] ?? 'Failed to file appeal');
    } catch (e) {
      debugPrint('[ApiService.appealClaim] $claimId — Error: $e');
      rethrow;
    }
  }
}
