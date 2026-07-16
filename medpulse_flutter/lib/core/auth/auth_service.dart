import 'package:shared_preferences/shared_preferences.dart';
import '../network/api_client.dart';

class AuthService {
  static final AuthService _instance = AuthService._internal();
  factory AuthService() => _instance;
  AuthService._internal();

  static const String _keyToken = 'jwt_token';
  static const String _keyUserId = 'user_id';
  static const String _keyUsername = 'username';
  static const String _keyEmail = 'email';

  /// 1. 發送 Email 驗證碼 API (POST /api/v1/auth/send-code)
  Future<Map<String, dynamic>> sendVerificationCode(String email) async {
    try {
      final response = await ApiClient().flaskDio.post(
        '/auth/send-code',
        data: {'email': email},
      );

      if (response.statusCode == 200) {
        return {'success': true, 'message': 'Verification code sent to email'};
      }
      return {'success': false, 'message': 'Failed to send verification code'};
    } catch (e) {
      return {'success': false, 'message': 'Network error. Make sure server is running.'};
    }
  }

  /// 2. 註冊 API (POST /api/v1/auth/register) — 新增 code 欄位
  Future<Map<String, dynamic>> register({
    required String username,
    required String email,
    required String password,
    required String code, // 新增 code 驗證碼參數
  }) async {
    try {
      final response = await ApiClient().flaskDio.post(
        '/auth/register',
        data: {
          'username': username,
          'email': email,
          'password': password,
          'code': code, // 帶入驗證碼
        },
      );

      if (response.statusCode == 201) {
        final data = response.data;
        await _saveUserData(
          token: data['access_token'],
          id: data['user']['id'],
          username: data['user']['username'],
          email: data['user']['email'],
        );
        return {'success': true, 'message': 'Registered successfully'};
      }
      return {'success': false, 'message': 'Registration failed'};
    } catch (e) {
      return {'success': false, 'message': 'Invalid verification code or registration failed'};
    }
  }

  /// 登入 API (POST /api/v1/auth/login)
  Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    try {
      final response = await ApiClient().flaskDio.post(
        '/auth/login',
        data: {
          'email': email,
          'password': password,
        },
      );

      if (response.statusCode == 200) {
        final data = response.data;
        await _saveUserData(
          token: data['access_token'],
          id: data['user']['id'],
          username: data['user']['username'],
          email: data['user']['email'],
        );
        return {'success': true, 'message': 'Login successful'};
      }
      return {'success': false, 'message': 'Invalid email or password'};
    } catch (e) {
      return {'success': false, 'message': 'Login failed. Check server or credentials.'};
    }
  }

  /// 寫入 UserData 與 Token 到本機快取
  Future<void> _saveUserData({
    required String token,
    required dynamic id,
    required String username,
    required String email,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyToken, token);
    await prefs.setString(_keyUserId, id.toString());
    await prefs.setString(_keyUsername, username);
    await prefs.setString(_keyEmail, email);

    // 登入後自動把 Bearer Token 加到 Flask Dio Header
    ApiClient().flaskDio.options.headers['Authorization'] = 'Bearer $token';
  }

  /// 檢查是否已登入
  Future<bool> isLoggedIn() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_keyToken);
    if (token != null && token.isNotEmpty) {
      // 復原 Authorization Header
      ApiClient().flaskDio.options.headers['Authorization'] = 'Bearer $token';
      return true;
    }
    return false;
  }

  /// 取得當前用戶資訊
  Future<Map<String, String>> getUserProfile() async {
    final prefs = await SharedPreferences.getInstance();
    return {
      'id': prefs.getString(_keyUserId) ?? '',
      'username': prefs.getString(_keyUsername) ?? 'User',
      'email': prefs.getString(_keyEmail) ?? '',
    };
  }

  /// 登出
  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
    ApiClient().flaskDio.options.headers.remove('Authorization');
  }
}