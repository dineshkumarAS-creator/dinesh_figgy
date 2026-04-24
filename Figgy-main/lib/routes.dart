import 'package:flutter/material.dart';
import 'package:figgy_app/screens/parametric_screen.dart';
import 'package:figgy_app/screens/pow_token_screen.dart';
import 'package:figgy_app/screens/pow_verification_screen.dart';
import 'package:figgy_app/screens/claim_processing_screen.dart';
import 'package:figgy_app/screens/claim_details_screen.dart';

class PowTokenArgs {
  final String workerId;
  final String? claimId;
  PowTokenArgs({required this.workerId, this.claimId});
}

class PowVerifyArgs {
  final String claimId;
  PowVerifyArgs({required this.claimId});
}

class ClaimProcessingArgs {
  final String claimId;
  final String? initialStatus;
  ClaimProcessingArgs({required this.claimId, this.initialStatus});
}

class AppRoutes {
  static const String parametric = '/parametric';
  static const String powToken = '/pow-token';
  static const String powVerify = '/pow-verify';
  static const String claimProcessing = '/claim-processing';
  static const String claimDetails = '/claim-details';

  static Route<dynamic> generateRoute(RouteSettings settings) {
    switch (settings.name) {
      case parametric:
        return MaterialPageRoute(
          builder: (_) => const ParametricScreen(),
        );
      case powToken:
        final args = settings.arguments as PowTokenArgs;
        return MaterialPageRoute(
          builder: (_) => PowTokenScreen(workerId: args.workerId, claimId: args.claimId),
        );
      case powVerify:
        final args = settings.arguments as PowVerifyArgs;
        return MaterialPageRoute(
          builder: (_) => ProofOfWorkScreen(claimId: args.claimId),
        );
      case claimProcessing:
        final args = settings.arguments as ClaimProcessingArgs;
        return MaterialPageRoute(
          builder: (_) => ClaimProcessingScreen(
            claimId: args.claimId,
            initialStatus: args.initialStatus,
          ),
        );
      case claimDetails:
        final args = settings.arguments as ClaimDetailsArgs;
        return MaterialPageRoute(
          builder: (_) => ClaimDetailsScreen(claimId: args.claimId),
        );
      default:
        return MaterialPageRoute(
          builder: (_) => Scaffold(
            body: Center(child: Text('No route defined for ${settings.name}')),
          ),
        );
    }
  }
}
