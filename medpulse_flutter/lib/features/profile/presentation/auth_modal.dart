import 'dart:async';
import 'package:flutter/material.dart';
import '../../../core/auth/auth_service.dart';

class AuthModal extends StatefulWidget {
  final VoidCallback onAuthSuccess;

  const AuthModal({super.key, required this.onAuthSuccess});

  @override
  State<AuthModal> createState() => _AuthModalState();
}

class _AuthModalState extends State<AuthModal> {
  bool _isLoginMode = true;
  bool _isLoading = false;

  // 倒數計時器相關變數
  int _countdownSeconds = 0;
  Timer? _timer;

  final _formKey = GlobalKey<FormState>();
  final TextEditingController _usernameController = TextEditingController();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _codeController = TextEditingController(); // 👈 驗證碼 Controller

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  /// 開始 60 秒倒數
  void _startCountdown() {
    setState(() => _countdownSeconds = 60);
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (_countdownSeconds == 0) {
        timer.cancel();
      } else {
        setState(() => _countdownSeconds--);
      }
    });
  }

  /// 發送驗證碼事件
  Future<void> _sendCode() async {
    final email = _emailController.text.trim();
    if (email.isEmpty || !email.contains('@')) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a valid email address first')),
      );
      return;
    }

    _startCountdown();

    final result = await AuthService().sendVerificationCode(email);

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(result['message'] ?? 'Sending code...'),
          backgroundColor: result['success'] ? const Color(0xFF00796B) : Colors.red,
        ),
      );
    }
  }

  /// 提交註冊 / 登入
  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    Map<String, dynamic> result;

    if (_isLoginMode) {
      result = await AuthService().login(
        email: _emailController.text.trim(),
        password: _passwordController.text,
      );
    } else {
      result = await AuthService().register(
        username: _usernameController.text.trim(),
        email: _emailController.text.trim(),
        password: _passwordController.text,
        code: _codeController.text.trim(), // 👈 傳送驗證碼
      );
    }

    setState(() => _isLoading = false);

    if (mounted) {
      if (result['success'] == true) {
        Navigator.pop(context);
        widget.onAuthSuccess();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(_isLoginMode ? 'Welcome back!' : 'Registered successfully!'),
            backgroundColor: const Color(0xFF00796B),
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result['message'] ?? 'Authentication failed'),
            backgroundColor: Colors.red[600],
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: SingleChildScrollView(
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 標題
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      _isLoginMode ? 'Sign In' : 'Create Account',
                      style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Color(0xFF004D40)),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: () => Navigator.pop(context),
                    ),
                  ],
                ),
                const SizedBox(height: 16),

                // 註冊時顯示 Username
                if (!_isLoginMode) ...[
                  TextFormField(
                    controller: _usernameController,
                    decoration: InputDecoration(
                      labelText: 'Username',
                      prefixIcon: const Icon(Icons.person_outline),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    validator: (v) => v == null || v.isEmpty ? 'Username is required' : null,
                  ),
                  const SizedBox(height: 12),
                ],

                // Email 輸入框
                TextFormField(
                  controller: _emailController,
                  keyboardType: TextInputType.emailAddress,
                  decoration: InputDecoration(
                    labelText: 'Email',
                    prefixIcon: const Icon(Icons.email_outlined),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  validator: (v) => v == null || !v.contains('@') ? 'Enter a valid email' : null,
                ),
                const SizedBox(height: 12),

                // 註冊模式時顯示：驗證碼欄位 + 發送按鈕
                if (!_isLoginMode) ...[
                  Row(
                    children: [
                      Expanded(
                        child: TextFormField(
                          controller: _codeController,
                          keyboardType: TextInputType.number,
                          decoration: InputDecoration(
                            labelText: 'Code',
                            prefixIcon: const Icon(Icons.shield_outlined),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                          ),
                          validator: (v) => v == null || v.length != 6 ? '6-digit code' : null,
                        ),
                      ),
                      const SizedBox(width: 8),
                      SizedBox(
                        height: 56,
                        child: OutlinedButton(
                          onPressed: _countdownSeconds > 0 ? null : _sendCode,
                          style: OutlinedButton.styleFrom(
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                            side: const BorderSide(color: Color(0xFF00796B)),
                          ),
                          child: Text(
                            _countdownSeconds > 0 ? '${_countdownSeconds}s' : 'Send Code',
                            style: const TextStyle(color: Color(0xFF00796B), fontWeight: FontWeight.bold),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                ],

                // 密碼輸入框
                TextFormField(
                  controller: _passwordController,
                  obscureText: true,
                  decoration: InputDecoration(
                    labelText: 'Password',
                    prefixIcon: const Icon(Icons.lock_outline),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  validator: (v) => v == null || v.length < 6 ? 'At least 6 characters' : null,
                ),
                const SizedBox(height: 20),

                // 提交按鈕
                SizedBox(
                  width: double.infinity,
                  height: 48,
                  child: ElevatedButton(
                    onPressed: _isLoading ? null : _submit,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF00796B),
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    child: _isLoading
                        ? const CircularProgressIndicator(color: Colors.white)
                        : Text(_isLoginMode ? 'Log In' : 'Register', style: const TextStyle(fontWeight: FontWeight.bold)),
                  ),
                ),
                const SizedBox(height: 12),

                // 切換 登入 / 註冊 模式
                Center(
                  child: TextButton(
                    onPressed: () {
                      setState(() {
                        _isLoginMode = !_isLoginMode;
                      });
                    },
                    child: Text(
                      _isLoginMode ? "Don't have an account? Sign Up" : "Already have an account? Log In",
                      style: const TextStyle(color: Color(0xFF00796B), fontWeight: FontWeight.bold),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}