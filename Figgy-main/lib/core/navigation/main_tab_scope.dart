import 'package:flutter/material.dart';

/// Wraps the main tab shell so nested widgets can call [BuildContext.goToMainTab]
/// without importing the shell widget (avoids import cycles).
class MainTabScope extends InheritedWidget {
  final void Function(int index) goToTab;

  const MainTabScope({
    super.key,
    required this.goToTab,
    required super.child,
  });

  static MainTabScope? maybeOf(BuildContext context) {
    return context.getInheritedWidgetOfExactType<MainTabScope>();
  }

  @override
  bool updateShouldNotify(MainTabScope oldWidget) => goToTab != oldWidget.goToTab;
}

extension MainTabScopeX on BuildContext {
  void goToMainTab(int index) {
    MainTabScope.maybeOf(this)?.goToTab(index);
  }
}
