import 'package:flutter/foundation.dart';

/// Backend origin for HTTP calls. Override at build time, e.g.
/// `flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:5050`
String get figgyApiBaseUrl {
  const fromEnv = String.fromEnvironment('API_BASE_URL');
  if (fromEnv.isNotEmpty) return fromEnv;
  return kIsWeb ? 'http://localhost:5000' : 'http://10.0.2.2:5000';
}
