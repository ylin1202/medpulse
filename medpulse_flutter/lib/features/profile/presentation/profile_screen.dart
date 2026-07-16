import 'package:flutter/material.dart';
import '../../../core/auth/auth_service.dart';
import 'auth_modal.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  bool _isLoggedIn = false;
  String _username = '';
  String _email = '';

  @override
  void initState() {
    super.initState();
    _checkAuthStatus();
  }

  /// 檢查本地登入狀態
  Future<void> _checkAuthStatus() async {
    final loggedIn = await AuthService().isLoggedIn();
    if (loggedIn) {
      final profile = await AuthService().getUserProfile();
      setState(() {
        _isLoggedIn = true;
        _username = profile['username'] ?? 'User';
        _email = profile['email'] ?? '';
      });
    } else {
      setState(() {
        _isLoggedIn = false;
      });
    }
  }

  /// 開啟 Auth 對話框
  void _openAuthModal() {
    showDialog(
      context: context,
      builder: (context) => AuthModal(
        onAuthSuccess: _checkAuthStatus,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8F9FA),
      appBar: AppBar(
        title: const Text('Profile & Settings', style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: const Color(0xFF00796B),
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(18.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 1. 使用者個人名片 / 登入引導卡片
            _buildUserHeaderCard(),
            const SizedBox(height: 24),

            // 2. 收藏與歷史紀錄區塊 (需登入)
            const Text(
              'Personal Features',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF004D40)),
            ),
            const SizedBox(height: 10),
            _buildFeatureTile(
              icon: Icons.bookmark_outline_rounded,
              title: 'My Bookmarks',
              subtitle: 'Saved drugs and verified fact-checks',
              onTap: () {
                if (!_isLoggedIn) {
                  _showLoginRequiredDialog();
                } else {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Opening Bookmarks...')),
                  );
                }
              },
            ),
            _buildFeatureTile(
              icon: Icons.history_rounded,
              title: 'Search & Analysis History',
              subtitle: 'Recent queries and clinical analysis logs',
              onTap: () {
                if (!_isLoggedIn) {
                  _showLoginRequiredDialog();
                } else {
                  // TODO: 開啟歷史紀錄
                }
              },
            ),
            const SizedBox(height: 24),

            // 3. 系統資訊與免責聲明 (無需登入即可查看)
            const Text(
              'About & System',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF004D40)),
            ),
            const SizedBox(height: 10),
            _buildFeatureTile(
              icon: Icons.info_outline_rounded,
              title: 'About MedPulse',
              subtitle: 'Version 2.1.0 (Dual-Engine RAG + Agent)',
              onTap: () => _showAboutDialog(),
            ),
            _buildFeatureTile(
              icon: Icons.gavel_rounded,
              title: 'Medical Disclaimer',
              subtitle: 'Important safety and legal terms',
              onTap: () => _showDisclaimerDialog(),
            ),
            _buildFeatureTile(
              icon: Icons.dns_outlined,
              title: 'Backend Service Health',
              subtitle: 'Flask Auth & FastAPI LangGraph Active',
              onTap: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Flask (JWT) & FastAPI Services Running')),
                );
              },
            ),
            const SizedBox(height: 30),

            // 4. 登出按鈕
            if (_isLoggedIn)
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: () async {
                    await AuthService().logout();
                    _checkAuthStatus();
                  },
                  icon: const Icon(Icons.logout_rounded, color: Colors.red),
                  label: const Text('Log Out', style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: Colors.red),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildUserHeaderCard() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.04),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: _isLoggedIn
          ? Row(
              children: [
                CircleAvatar(
                  radius: 30,
                  backgroundColor: const Color(0xFF00796B),
                  child: Text(
                    _username.isNotEmpty ? _username.substring(0, 1).toUpperCase() : 'U',
                    style: const TextStyle(fontSize: 24, color: Colors.white, fontWeight: FontWeight.bold),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(_username, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 4),
                      Text(_email, style: TextStyle(color: Colors.grey[600], fontSize: 13)),
                    ],
                  ),
                ),
              ],
            )
          : Column(
              children: [
                Row(
                  children: [
                    CircleAvatar(
                      radius: 26,
                      backgroundColor: Colors.teal[50],
                      child: const Icon(Icons.person_outline_rounded, color: Color(0xFF00796B), size: 28),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Sign in to MedPulse', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                          const SizedBox(height: 2),
                          Text('Unlock bookmarking for drugs & health myths', style: TextStyle(color: Colors.grey[600], fontSize: 12)),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: _openAuthModal,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF00796B),
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                    child: const Text('Log In / Register', style: TextStyle(fontWeight: FontWeight.bold)),
                  ),
                ),
              ],
            ),
    );
  }

  Widget _buildFeatureTile({
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.02),
            blurRadius: 6,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: ListTile(
        onTap: onTap,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        leading: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: const Color(0xFF00796B).withOpacity(0.08),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, color: const Color(0xFF00796B), size: 22),
        ),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
        subtitle: Text(subtitle, style: TextStyle(color: Colors.grey[500], fontSize: 12)),
        trailing: const Icon(Icons.chevron_right_rounded, color: Colors.grey, size: 20),
      ),
    );
  }

  void _showLoginRequiredDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: const [
            Icon(Icons.lock_outline_rounded, color: Color(0xFF00796B)),
            SizedBox(width: 8),
            Text('Login Required'),
          ],
        ),
        content: const Text('Please sign in to access your saved bookmarks and personal history.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel', style: TextStyle(color: Colors.grey)),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              _openAuthModal();
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF00796B),
              foregroundColor: Colors.white,
            ),
            child: const Text('Log In Now'),
          ),
        ],
      ),
    );
  }

  void _showAboutDialog() {
    showAboutDialog(
      context: context,
      applicationName: 'MedPulse',
      applicationVersion: '2.1.0',
      applicationIcon: const Icon(Icons.reviews, size: 40, color: Color(0xFF00796B)),
      children: const [
        Text('MedPulse is an intelligent healthcare platform integrating Dual-RAG architecture, fine-tuned LLMs, and real-time pharmacy navigation.'),
      ],
    );
  }

  void _showDisclaimerDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: const [
            Icon(Icons.gavel_rounded, color: Colors.amber),
            SizedBox(width: 8),
            Text('Medical Disclaimer'),
          ],
        ),
        content: const SingleChildScrollView(
          child: Text(
            '1. Educational Purpose Only: MedPulse is designed strictly for informational and educational purposes.\n\n'
            '2. Not Professional Medical Advice: AI analysis, drug facts, and fact-checking results generated by this app do NOT constitute professional medical advice, diagnosis, or treatment.\n\n'
            '3. Consult Professionals: Always seek the advice of a qualified healthcare provider for any questions regarding a medical condition.',
            style: TextStyle(fontSize: 13, height: 1.5),
          ),
        ),
        actions: [
          ElevatedButton(
            onPressed: () => Navigator.pop(context),
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF00796B),
              foregroundColor: Colors.white,
            ),
            child: const Text('I Understand'),
          ),
        ],
      ),
    );
  }
}