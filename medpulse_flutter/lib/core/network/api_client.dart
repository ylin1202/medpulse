import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Singleton API network client dynamically loading endpoint configurations
/// from environment variables (.env) with robust local fallbacks.
class ApiClient {
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;

  late final Dio flaskDio;
  late final Dio fastApiDio;

  ApiClient._internal() {
    // Read URLs from .env with production/local fallback defaults
    final flaskUrl = dotenv.env['FLASK_BASE_URL'] ?? 'http://localhost:5001/api/v1';
    final fastApiUrl = dotenv.env['FASTAPI_BASE_URL'] ?? 'http://localhost:8000';

    // 1. Initialize Flask Dio instance
    flaskDio = Dio(
      BaseOptions(
        baseUrl: flaskUrl,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
        headers: {'Content-Type': 'application/json'},
      ),
    );

    flaskDio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final prefs = await SharedPreferences.getInstance();
          final token = prefs.getString('jwt_token');

          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          return handler.next(options);
        },
        onError: (DioException e, handler) {
          if (e.response?.statusCode == 401) {
            debugPrint('[ApiClient] Unauthorized access (401). Session may have expired.');
          }
          return handler.next(e);
        },
      ),
    );

    // 2. Initialize FastAPI Dio instance
    fastApiDio = Dio(
      BaseOptions(
        baseUrl: fastApiUrl,
        connectTimeout: const Duration(seconds: 30),
        receiveTimeout: const Duration(seconds: 60),
        sendTimeout: const Duration(seconds: 30),
        headers: {'Content-Type': 'application/json'},
      ),
    );
  }

  Dio get dio => flaskDio;
}