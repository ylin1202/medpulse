import 'package:flutter/material.dart';
import 'features/main_navigation_screen.dart';

import 'package:flutter_dotenv/flutter_dotenv.dart';

import 'package:flutter/services.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // 1. 載入 .env 檔案
  await dotenv.load(fileName: ".env");

  // 2. 將 .env 裡的 API Key 傳給 iOS Native 層
  final apiKey = dotenv.env['GOOGLE_MAPS_API_KEY'];
  if (apiKey != null && apiKey.isNotEmpty) {
    const platform = MethodChannel('com.medpulse.app/config');
    try {
      await platform.invokeMethod('setGoogleMapsKey', {'key': apiKey});
    } on PlatformException catch (e) {
      print("Failed to set Google Maps API Key: '${e.message}'.");
    }
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