import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:figgy_app/screens/onboarding_screen.dart';
import 'package:figgy_app/screens/registration_screen.dart';
import 'package:figgy_app/app/main_wrapper.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:figgy_app/routes.dart';

import 'package:figgy_app/services/navigation_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Show error details instead of red block
  ErrorWidget.builder = (FlutterErrorDetails details) {
    debugPrint('⚠️ WIDGET ERROR: ${details.exception}');
    debugPrint('⚠️ STACK: ${details.stack}');
    return Container(
      padding: const EdgeInsets.all(12),
      margin: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: const Color(0xFFFEE2E2),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFFEF4444)),
      ),
      child: Text(
        'Error: ${details.exception}',
        style: const TextStyle(color: Color(0xFF991B1B), fontSize: 12),
      ),
    );
  };

  final prefs = await SharedPreferences.getInstance();
  
  // For hackathon demo: You can comment this back in to force onboarding if needed
  // await prefs.setBool('has_onboarded', false); 
  
  final String launchUrl = Uri.base.toString().toLowerCase();
  final bool forceRegistration = kIsWeb &&
      (launchUrl.contains('registration=1') ||
          launchUrl.contains('register=1') ||
          launchUrl.contains('/register'));
  final bool hasOnboarded = forceRegistration ? false : (prefs.getBool('has_onboarded') ?? false);
  
  runApp(MyApp(
    initialHome: forceRegistration
        ? const RegistrationScreen()
        : hasOnboarded
            ? const MainWrapper(initialIndex: 1) // Shield timeline tab
            : const OnboardingScreen(), // Start at Welcome flow
  ));
}

class MyApp extends StatelessWidget {
  final Widget initialHome;
  const MyApp({super.key, required this.initialHome});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      navigatorKey: NavigationService.navigatorKey,
      title: 'Figgy',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFFFF6B35)),
        useMaterial3: true,
      ),
      home: initialHome,
      onGenerateRoute: AppRoutes.generateRoute,
    );
  }
}
