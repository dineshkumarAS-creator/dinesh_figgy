import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:figgy_app/services/api_service.dart';
import 'package:figgy_app/services/navigation_service.dart';
import 'package:figgy_app/screens/claim_details_screen.dart';
import 'package:figgy_app/features/profile/profile_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';

class NotificationService {
  static final NotificationService _instance = NotificationService._internal();
  factory NotificationService() => _instance;
  NotificationService._internal();

  final FirebaseMessaging _fcm = FirebaseMessaging.instance;
  final FlutterLocalNotificationsPlugin _localNotifications = FlutterLocalNotificationsPlugin();
  
  bool _initialized = false;

  Future<void> init() async {
    if (_initialized) return;

    // 1. Request permissions
    NotificationSettings settings = await _fcm.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );

    if (settings.authorizationStatus == AuthorizationStatus.authorized) {
      debugPrint('[NotificationService] User granted permission');
    } else {
      debugPrint('[NotificationService] User declined permission');
      return;
    }

    // 2. Setup Local Notifications
    if (!kIsWeb) {
      const AndroidInitializationSettings initSettingsAndroid = AndroidInitializationSettings('@mipmap/ic_launcher');
      const InitializationSettings initSettings = InitializationSettings(android: initSettingsAndroid);
      await _localNotifications.initialize(
        initSettings,
        onDidReceiveNotificationResponse: (details) {
          // This handles taps on local notifications (foreground notifications we showed manually)
          // details.payload could contain screen/id JSON
        }
      );
    }

    // 3. Get FCM Token
    try {
      String? token = await _fcm.getToken();
      if (token != null) await _syncFCMToken(token);
    } catch (e) {
      debugPrint('[NotificationService] Token fetch failed: $e');
    }
    _fcm.onTokenRefresh.listen(_syncFCMToken);

    // 4. Foreground notifications
    FirebaseMessaging.onMessage.listen(_showLocalNotification);

    // 5. TAP HANDLERS (Deep-linking)
    
    // Background taps
    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
      _handleNotificationTap(message);
    });

    // Terminated taps
    _fcm.getInitialMessage().then((RemoteMessage? message) {
      if (message != null) {
        _handleNotificationTap(message);
      }
    });
    
    _initialized = true;
  }

  void _handleNotificationTap(RemoteMessage message) {
    debugPrint('[NotificationService] Tapped with Data: ${message.data}');
    final screen = message.data['screen'];
    final claimId = message.data['claim_id'];

    if (screen == 'claim_details' && claimId != null) {
      NavigationService.navigatorKey.currentState?.push(
        MaterialPageRoute(builder: (_) => ClaimDetailsScreen(claimId: claimId))
      );
    } else if (screen == 'profile_upi_edit' || screen == 'profile') {
      NavigationService.navigatorKey.currentState?.push(
        MaterialPageRoute(builder: (_) => const ProfileScreen())
      );
    }
  }

  Future<void> _syncFCMToken(String token) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('fcm_token', token);
      final workerId = prefs.getString('worker_id');
      if (workerId == null) return;
      await ApiService().updateFcmToken(token);
    } catch (e) {
      debugPrint('[NotificationService] Sync failed: $e');
    }
  }

  Future<void> _showLocalNotification(RemoteMessage message) async {
    RemoteNotification? notification = message.notification;
    if (notification != null && !kIsWeb) {
      const AndroidNotificationDetails androidDetails = AndroidNotificationDetails(
        'figgy_claim_updates',
        'Claim Updates',
        channelDescription: 'Notifications regarding your GigShield claims',
        importance: Importance.max,
        priority: Priority.high,
        icon: '@mipmap/ic_launcher',
      );
      await _localNotifications.show(
        notification.hashCode,
        notification.title,
        notification.body,
        const NotificationDetails(android: androidDetails),
        payload: message.data['screen'],
      );
    } else if (notification != null && kIsWeb) {
      debugPrint('[NotificationService] Web Push: ${notification.title} - ${notification.body}');
    }
  }
}
