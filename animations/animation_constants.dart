import 'package:flutter/material.dart';

abstract class ShieldAnimations {
  static const Duration entranceDuration     = Duration(milliseconds: 800);
  static const Duration staggerStepDelay     = Duration(milliseconds: 120);
  static const Curve    entranceCurve        = Curves.elasticOut;
  static const Duration progressDemoDuration = Duration(milliseconds: 3000);
  static const Curve    progressCurve        = Curves.linear;
  static const Duration monitorExpandDur     = Duration(milliseconds: 400);
  static const Curve    monitorCurve         = Curves.easeOutCubic;
  static const Duration monitorTextStep      = Duration(milliseconds: 600);
  static const Duration monitorTextFade      = Duration(milliseconds: 200);
  static const Duration disruptionSlideDur   = Duration(milliseconds: 350);
  static const Curve    disruptionCurve      = Curves.easeOutBack;
  static const Duration circleColorDur       = Duration(milliseconds: 300);
  static const Duration pulseDuration        = Duration(milliseconds: 1400);
  static const Duration shakeDuration        = Duration(milliseconds: 350);
  static const Duration claimBounceDur       = Duration(milliseconds: 500);
  static const Curve    claimBounceCurve     = Curves.elasticOut;
  static const Duration bannerSlideDur       = Duration(milliseconds: 400);
  static const Curve    bannerCurve          = Curves.easeOutCubic;
  static const Duration step1To2Delay        = Duration(milliseconds: 1200);
  static const Duration step2To3Delay        = Duration(milliseconds: 2400);
  static const Duration step3To4Delay        = Duration(milliseconds: 1800);
  static const Duration step4To5Delay        = Duration(milliseconds: 1500);
  static const Duration step5To6Delay        = Duration(milliseconds: 2000);
  static const Duration step6To7Delay        = Duration(milliseconds: 1500);
  static const Duration step7To8Delay        = Duration(milliseconds: 1200);
}
