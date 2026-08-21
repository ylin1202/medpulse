import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ApiClient {
  // 單例模式 (Singleton)
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;

  late final Dio flaskDio;   // 給 Flask 用的 Dio (例如 5001 Port)
  late final Dio fastApiDio; // 給 FastAPI 用的 Dio (例如 8000 Port)

  ApiClient._internal() {
    // 1. 初始化 Flask Dio
    flaskDio = Dio(
      BaseOptions(
        baseUrl: '',
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
        headers: {'Content-Type': 'application/json'},
      ),
    );

    // 加入 Interceptor：每一次發 Request 前，自動檢查並附加 Bearer Token
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
          // 如果收到 401 代表 Token 過期或未登入
          if (e.response?.statusCode == 401) {
            print('[ApiClient] Unauthorized access (401). User may need to sign in again.');
          }
          return handler.next(e);
        },
      ),
    );

    // 2. 初始化 FastAPI Dio (給予 AI 生成足夠的逾時時間)
    fastApiDio = Dio(
      BaseOptions(
        baseUrl: '',
        connectTimeout: const Duration(seconds: 30),
        receiveTimeout: const Duration(seconds: 60), // 從 15 秒調整至 60 秒
        sendTimeout: const Duration(seconds: 30),
        headers: {'Content-Type': 'application/json'},
      ),
    );
  }

  // 相容舊程式碼
  Dio get dio => flaskDio;
}