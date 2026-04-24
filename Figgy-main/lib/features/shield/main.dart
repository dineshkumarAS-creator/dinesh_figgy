import 'package:flutter/material.dart';
import 'core/theme.dart';
import 'main_layout.dart';

void main() {
  runApp(const FiggyApp());
}

class FiggyApp extends StatelessWidget {
  const FiggyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Figgy Shield',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      home: const MainLayout(),
    );
  }
}
