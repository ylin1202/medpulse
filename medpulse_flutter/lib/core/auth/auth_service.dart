import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../network/api_client.dart';


class AuthService {
  static final AuthService _instance = AuthService._internal();
  factory AuthService() => _instance;
  AuthService._internal();

  /// Global reactive notifier broadcasting real-time authentication status (true/false).
  static final ValueNotifier<bool> authState = ValueNotifier<bool>(false);

  static const String _keyToken = 'jwt_token';
  static const String _keyUserId = 'user_id';
  static const String _keyUsername = 'username';
  static const String _keyEmail = 'email';

  /// Request email verification code (POST /api/v1/auth/send-code).
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
      return {
        'success': false,
        'message': 'Network error. Ensure the backend server is reachable.',
      };
    }
  }

  /// Register a new account with email verification (POST /api/v1/auth/register).
  Future<Map<String, dynamic>> register({
    required String username,
    required String email,
    required String password,
    required String code,
  }) async {
    try {
      final response = await ApiClient().flaskDio.post(
        '/auth/register',
        data: {
          'username': username,
          'email': email,
          'password': password,
          'code': code,
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
      return {
        'success': false,
        'message': 'Invalid verification code or registration request failed.',
      };
    }
  }

  /// Authenticate user credentials and retrieve access token (POST /api/v1/auth/login).
  Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    try {
      final response = await ApiClient().flaskDio.post(
        '/auth/login',
        data: {'email': email, 'password': password},
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
      return {
        'success': false,
        'message': 'Login failed. Please verify credentials or connection.',
      };
    }
  }

  /// Persist session metadata and JWT access token to local device storage.
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

    // Broadcast authenticated state across the application
    authState.value = true;
  }

  /// Check active user authentication state from persistent storage.
  Future<bool> isLoggedIn() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_keyToken);
    final loggedIn = token != null && token.isNotEmpty;

    // Sync reactive state if divergence is detected
    if (authState.value != loggedIn) {
      authState.value = loggedIn;
    }
    return loggedIn;
  }

  /// Terminate session, purge persistent credentials, and clear network headers.
  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();

    // Strip authorization header from HTTP client options
    ApiClient().flaskDio.options.headers.remove('Authorization');

    // Trigger global reactive logout broadcast
    authState.value = false;
  }

  /// Retrieve current authenticated user profile attributes.
  Future<Map<String, String>> getUserProfile() async {
    final prefs = await SharedPreferences.getInstance();
    return {
      'id': prefs.getString(_keyUserId) ?? '',
      'username': prefs.getString(_keyUsername) ?? 'User',
      'email': prefs.getString(_keyEmail) ?? '',
    };
  }
}