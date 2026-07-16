import 'package:flutter/material.dart';
import 'features/main_navigation_screen.dart';

import 'package:flutter_dotenv/flutter_dotenv.dart';


Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    await dotenv.load(fileName: ".env");
  } catch (e) {
    debugPrint("Failed to load .env: $e");
  }
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