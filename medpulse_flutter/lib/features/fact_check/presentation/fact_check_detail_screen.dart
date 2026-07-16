import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../data/fact_check_model.dart';

class FactCheckDetailScreen extends StatelessWidget {
  final FactCheckModel factCheck;

  const FactCheckDetailScreen({super.key, required this.factCheck});

  /// 依據 verdict 取得對應的主題顏色 (柔和配色)
  Color _getVerdictColor(String verdict) {
    final v = verdict.toLowerCase();
    if (v.contains('false') || v.contains('謠言') || v.contains('不實')) {
      return const Color(0xFFE57373); // 柔和紅
    } else if (v.contains('true') || v.contains('真實') || v.contains('正確')) {
      return const Color(0xFF81C784); // 柔和綠
    } else if (v.contains('mix') || v.contains('partial') || v.contains('部分')) {
      return const Color(0xFFFFB74D); // 柔和橘
    }
    return Colors.blueGrey[400]!;
  }

  /// 依據 verdict 取得對應圖示
  IconData _getVerdictIcon(String verdict) {
    final v = verdict.toLowerCase();
    if (v.contains('false') || v.contains('謠言') || v.contains('不實')) {
      return Icons.cancel_rounded;
    } else if (v.contains('true') || v.contains('真實') || v.contains('正確')) {
      return Icons.check_circle_rounded;
    } else if (v.contains('mix') || v.contains('partial') || v.contains('部分')) {
      return Icons.published_with_changes_rounded;
    }
    return Icons.help_outline_rounded;
  }

  /// 開啟外部網址
  Future<void> _launchUrl(String urlString) async {
    if (urlString.isEmpty) return;
    final Uri url = Uri.parse(urlString);
    if (!await launchUrl(url, mode: LaunchMode.externalApplication)) {
      debugPrint('Could not launch $urlString');
    }
  }

  @override
  Widget build(BuildContext context) {
    final themeColor = _getVerdictColor(factCheck.verdict);
    final verdictIcon = _getVerdictIcon(factCheck.verdict);

    return Scaffold(
      backgroundColor: const Color(0xFFF8F9FA),
      appBar: AppBar(
        title: const Text('Fact-Check Detail', style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: const Color(0xFF00796B),
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(18.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 1. 頂部 Hero Verdict 卡片
            Container(
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
              child: ClipRRect(
                borderRadius: BorderRadius.circular(20),
                child: Column(
                  children: [
                    // 彩色 Header 帶（呈現 VERDICT 結果）
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      color: themeColor.withOpacity(0.15),
                      child: Row(
                        children: [
                          Icon(verdictIcon, color: themeColor == const Color(0xFFFFB74D) ? Colors.orange[900] : themeColor, size: 26),
                          const SizedBox(width: 8),
                          Text(
                            factCheck.verdict.toUpperCase(),
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w900,
                              color: themeColor == const Color(0xFFFFB74D) ? Colors.orange[900] : themeColor,
                              letterSpacing: 0.5,
                            ),
                          ),
                        ],
                      ),
                    ),

                    // 宣稱內容 (Claim)
                    Padding(
                      padding: const EdgeInsets.all(18.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: const [
                              Icon(Icons.format_quote_rounded, size: 20, color: Colors.grey),
                              SizedBox(width: 4),
                              Text(
                                'CLAIM / RUMOR',
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.grey,
                                  letterSpacing: 0.8,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Text(
                            factCheck.claim,
                            style: const TextStyle(
                              fontSize: 17,
                              fontWeight: FontWeight.bold,
                              height: 1.4,
                              color: Colors.black87,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

            // 2. 醫學解析 (Medical Explanation) 標題
            Row(
              children: [
                Container(
                  width: 4,
                  height: 18,
                  decoration: BoxDecoration(
                    color: const Color(0xFF00796B),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const SizedBox(width: 8),
                const Icon(Icons.science_outlined, size: 20, color: Color(0xFF00796B)),
                const SizedBox(width: 6),
                const Text(
                  'Medical Explanation & Evidence',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF004D40),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // 醫學解析內容卡片
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(18.0),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.04),
                    blurRadius: 8,
                    offset: const Offset(0, 3),
                  ),
                ],
              ),
              child: Text(
                factCheck.explanation.isEmpty ? factCheck.summary : factCheck.explanation,
                style: const TextStyle(
                  fontSize: 15,
                  height: 1.6,
                  color: Color(0xFF37474F),
                  letterSpacing: 0.2,
                ),
              ),
            ),
            const SizedBox(height: 24),

            // 3. 參考來源卡片 (Source Card)
            Container(
              padding: const EdgeInsets.all(16.0),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: const Color(0xFF00796B).withOpacity(0.2)),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.02),
                    blurRadius: 6,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(6),
                        decoration: BoxDecoration(
                          color: const Color(0xFF00796B).withOpacity(0.1),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Icon(Icons.verified_outlined, size: 18, color: Color(0xFF00796B)),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'VERIFIED SOURCE',
                              style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.grey),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              factCheck.source,
                              style: const TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.bold,
                                color: Color(0xFF004D40),
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),

                  // 若有原始報導網址，顯示點擊微按鈕
                  if (factCheck.claimUrl.isNotEmpty) ...[
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 12.0),
                      child: Divider(height: 1),
                    ),
                    InkWell(
                      borderRadius: BorderRadius.circular(10),
                      onTap: () => _launchUrl(factCheck.claimUrl),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                        decoration: BoxDecoration(
                          color: const Color(0xFF00796B).withOpacity(0.05),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.open_in_new_rounded, size: 16, color: Color(0xFF00796B)),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                factCheck.claimUrl,
                                style: const TextStyle(
                                  color: Color(0xFF00796B),
                                  fontWeight: FontWeight.w600,
                                  fontSize: 13,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            const Icon(Icons.chevron_right_rounded, size: 18, color: Color(0xFF00796B)),
                          ],
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }
}