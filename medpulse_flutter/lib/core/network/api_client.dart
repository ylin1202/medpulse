import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// 專門負責管理 HTTP 請求與 JWT 自動附加的單例 (Singleton) 類別
class ApiClient {
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;

  late final Dio dio;
  final FlutterSecureStorage storage = const FlutterSecureStorage();

  // 預設連線至本機 Flask API (模擬器連線 localhost 需使用 10.0.2.2 或 127.0.0.1)
  // iOS 模擬器可直接用 http://127.0.0.1:5001
  static const String baseUrl = 'http://localhost:5001/api/v1';

  ApiClient._internal() {
    dio = Dio(
      BaseOptions(
        baseUrl: baseUrl,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 30),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    // 設定 Dio 攔截器 (Interceptor)：每次發送請求前，自動從安全儲存區抓取 JWT Token 帶入
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await storage.read(key: 'jwt_token');
          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          return handler.next(options);
        },
        onError: (DioException e, handler) {
          // 統一記錄 HTTP 錯誤日誌
          print('[API Error] ${e.response?.statusCode} => ${e.message}');
          return handler.next(e);
        },
      ),
    );
  }

  /// 儲存 JWT Token 至手機安全儲存區 (Keystore / Keychain)
  Future<void> saveToken(String token) async {
    await storage.write(key: 'jwt_token', value: token);
  }

  /// 清除 JWT Token (使用者登出時使用)
  Future<void> clearToken() async {
    await storage.delete(key: 'jwt_token');
  }

  /// 檢查是否已經有 Token (判斷是否登入)
  Future<bool> hasToken() async {
    final token = await storage.read(key: 'jwt_token');
    return token != null && token.isNotEmpty;
  }
}