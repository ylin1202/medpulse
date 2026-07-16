import 'package:dio/dio.dart';

class ApiClient {
  // 單例模式 (Singleton)
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;

  late final Dio flaskDio;   // 給 Flask 用的 Dio (例如 5000 Port)
  late final Dio fastApiDio; // 給 FastAPI 用的 Dio (例如 8000 Port)

  ApiClient._internal() {
    // 1. 初始化 Flask Dio (預設 baseUrl)
    flaskDio = Dio(
      BaseOptions(
        baseUrl: 'http://127.0.0.1:5001/api/v1', // 請確認你的 Flask Port
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 10),
        headers: {'Content-Type': 'application/json'},
      ),
    );

    // 2. 初始化 FastAPI Dio (FastAPI 連線 Port)
    fastApiDio = Dio(
      BaseOptions(
        baseUrl: 'http://127.0.0.1:8000/api/v1', // 請確認你的 FastAPI Port (例如 8000)
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 15), // AI 推論可給稍長的 Timeout
        headers: {'Content-Type': 'application/json'},
      ),
    );
  }

  // 相容舊程式碼：如果原本有呼叫 ApiClient().dio，指向 flaskDio 即可
  Dio get dio => flaskDio;
}