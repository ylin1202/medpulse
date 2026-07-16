import 'package:flutter/material.dart';
import 'features/main_navigation_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MedPulseApp());
}

class MedPulseApp extends StatelessWidget {
  const MedPulseApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MedPulse',
      debugShowCheckedModeBanner: false, // 隱藏 DEBUG 標籤
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF00796B), // 主主題色：深綠色
          primary: const Color(0xFF00796B),
        ),
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFFF5F7FA), // 簡約亮灰底色
      ),
      home: const MainNavigationScreen(),
    );
  }
}