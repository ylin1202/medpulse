import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'features/main_navigation_screen.dart';

Future<void> main() async {
  // Ensure Flutter engine bindings are initialized before async bootstrapping
  WidgetsFlutterBinding.ensureInitialized();

  // Load environment variables from .env asset bundle
  try {
    await dotenv.load(fileName: ".env");
  } catch (e) {
    debugPrint("[Config] Failed to load .env file: $e");
  }

  runApp(const MedPulseApp());
}

class MedPulseApp extends StatelessWidget {
  const MedPulseApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MedPulse',
      debugShowCheckedModeBanner: false, 
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF00796B), 
          primary: const Color(0xFF00796B),
        ),
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFFF5F7FA), 
      ),
      home: const MainNavigationScreen(),
    );
  }
}