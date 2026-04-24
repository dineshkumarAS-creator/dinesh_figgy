import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_base_url.dart';

class PolicyService {
  static String get baseUrl => "$figgyApiBaseUrl/api/policy";

  static Future<List<dynamic>> matchPolicy(Map<String, dynamic> workerProfile) async {
    try {
      final response = await http.post(
        Uri.parse("$baseUrl/match"),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode(workerProfile),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception("Failed to match policies: ${response.statusCode}");
      }
    } catch (e) {
      // Return empty list if there's an error to prevent UI crash
      return [];
    }
  }

  static Future<List<dynamic>> getPolicies() async {
    final response = await http.get(Uri.parse(baseUrl));
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception("Failed to load all policies");
    }
  }
}
