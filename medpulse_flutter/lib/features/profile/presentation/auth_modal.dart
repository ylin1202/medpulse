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

  // Rate-limiting countdown timer variables
  int _countdownSeconds = 0;
  Timer? _timer;

  final _formKey = GlobalKey<FormState>();
  final TextEditingController _usernameController = TextEditingController();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _codeController = TextEditingController();

  @override
  void dispose() {
    _timer?.cancel();
    _usernameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _codeController.dispose();
    super.dispose();
  }

  /// Initialize 60-second rate-limiting countdown for OTP dispatch
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

  /// Request email verification code dispatch
  Future<void> _sendCode() async {
    final email = _emailController.text.trim();
    if (email.isEmpty || !email.contains('@')) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a valid email address first.')),
      );
      return;
    }

    _startCountdown();

    final result = await AuthService().sendVerificationCode(email);

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(result['message'] ?? 'Sending verification code...'),
          backgroundColor: result['success'] ? const Color(0xFF00796B) : Colors.red,
        ),
      );
    }
  }

  /// Submit authentication form payload (Sign In or Registration)
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
        code: _codeController.text.trim(),
      );
    }

    setState(() => _isLoading = false);

    if (mounted) {
      if (result['success'] == true) {
        Navigator.pop(context);
        widget.onAuthSuccess();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(_isLoginMode ? 'Welcome back!' : 'Account registered successfully!'),
            backgroundColor: const Color(0xFF00796B),
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result['message'] ?? 'Authentication failed.'),
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
                // Header row with title and dismiss action
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      _isLoginMode ? 'Sign In' : 'Create Account',
                      style: const TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF004D40),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: () => Navigator.pop(context),
                    ),
                  ],
                ),
                const SizedBox(height: 16),

                // Username input field (Registration mode only)
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

                // Email address input field
                TextFormField(
                  controller: _emailController,
                  keyboardType: TextInputType.emailAddress,
                  decoration: InputDecoration(
                    labelText: 'Email Address',
                    prefixIcon: const Icon(Icons.email_outlined),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  validator: (v) => v == null || !v.contains('@') ? 'Enter a valid email' : null,
                ),
                const SizedBox(height: 12),

                // OTP verification code input & trigger button (Registration mode only)
                if (!_isLoginMode) ...[
                  Row(
                    children: [
                      Expanded(
                        child: TextFormField(
                          controller: _codeController,
                          keyboardType: TextInputType.number,
                          decoration: InputDecoration(
                            labelText: 'Verification Code',
                            prefixIcon: const Icon(Icons.shield_outlined),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                          ),
                          validator: (v) => v == null || v.length != 6 ? 'Enter 6-digit code' : null,
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
                            style: const TextStyle(
                              color: Color(0xFF00796B),
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                ],

                // Password input field
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

                // Submit action button
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
                        : Text(
                            _isLoginMode ? 'Log In' : 'Register',
                            style: const TextStyle(fontWeight: FontWeight.bold),
                          ),
                  ),
                ),
                const SizedBox(height: 12),

                // Mode toggle button (Sign In <-> Sign Up)
                Center(
                  child: TextButton(
                    onPressed: () {
                      setState(() {
                        _isLoginMode = !_isLoginMode;
                      });
                    },
                    child: Text(
                      _isLoginMode ? "Don't have an account? Sign Up" : "Already have an account? Log In",
                      style: const TextStyle(
                        color: Color(0xFF00796B),
                        fontWeight: FontWeight.bold,
                      ),
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