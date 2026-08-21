import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import '../data/fact_check_model.dart';

class FactCheckDetailScreen extends StatelessWidget {
  final FactCheckModel factCheck;
  final String? aiSummary; // 僅從彈窗按鈕點進來時傳入

  const FactCheckDetailScreen({
    super.key,
    required this.factCheck,
    this.aiSummary,
  });

  Color _getVerdictColor(String verdict) {
    final v = verdict.toLowerCase();
    if (v.contains('false') || v.contains('謠言') || v.contains('不實')) {
      return const Color(0xFFE57373);
    } else if (v.contains('true') || v.contains('真實') || v.contains('正確')) {
      return const Color(0xFF81C784);
    } else if (v.contains('mix') || v.contains('partial') || v.contains('部分')) {
      return const Color(0xFFFFB74D);
    }
    return Colors.blueGrey[400]!;
  }

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

  @override
  Widget build(BuildContext context) {
    final themeColor = _getVerdictColor(factCheck.verdict);
    final verdictIcon = _getVerdictIcon(factCheck.verdict);

    final String originalContent =
        factCheck.originalExplanation.trim().isNotEmpty
            ? factCheck.originalExplanation.trim()
            : (factCheck.summary.trim().isNotEmpty
                ? factCheck.summary.trim()
                : 'No original text available.');

    final String sourceText = factCheck.source.trim();
    final bool hasSource =
        sourceText.isNotEmpty &&
        sourceText != 'PUBHEALTH' &&
        sourceText != 'PUBHEALTH Dataset';

    return Scaffold(
      backgroundColor: const Color(0xFFF8F9FA),
      appBar: AppBar(
        title: const Text(
          'Fact-Check Detail',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: const Color(0xFF00796B),
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(18.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 1. 頂部 Verdict 卡片
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
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 12,
                      ),
                      color: themeColor.withOpacity(0.15),
                      child: Row(
                        children: [
                          Icon(
                            verdictIcon,
                            color: themeColor == const Color(0xFFFFB74D)
                                ? Colors.orange[900]
                                : themeColor,
                            size: 26,
                          ),
                          const SizedBox(width: 8),
                          Text(
                            factCheck.verdict.toUpperCase(),
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w900,
                              color: themeColor == const Color(0xFFFFB74D)
                                  ? Colors.orange[900]
                                  : themeColor,
                              letterSpacing: 0.5,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Padding(
                      padding: const EdgeInsets.all(18.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: const [
                              Icon(
                                Icons.format_quote_rounded,
                                size: 20,
                                color: Colors.grey,
                              ),
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

            // 2. 只有從彈窗 Dialog 進入時才顯示的 AI 生成區塊 (支援 Markdown 解析)
            if (aiSummary != null && aiSummary!.trim().isNotEmpty) ...[
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
                  const Icon(
                    Icons.auto_awesome,
                    size: 18,
                    color: Color(0xFF00796B),
                  ),
                  const SizedBox(width: 6),
                  const Text(
                    'AI Synthesis Summary',
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF004D40),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16.0),
                decoration: BoxDecoration(
                  color: const Color(0xFFF0FDF4),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: Colors.teal.shade100),
                ),
                child: MarkdownBody(
                  data: aiSummary!.trim(),
                  selectable: true,
                  styleSheet: MarkdownStyleSheet(
                    p: const TextStyle(
                      fontSize: 14.5,
                      height: 1.6,
                      color: Color(0xFF1B4D3E),
                    ),
                    strong: const TextStyle(
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF004D40),
                    ),
                    listBullet: const TextStyle(
                      color: Color(0xFF00796B),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 24),
            ],

            // 3. 原始醫學文獻卡片 (支援 Markdown 解析)
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
                const Icon(
                  Icons.science_outlined,
                  size: 20,
                  color: Color(0xFF00796B),
                ),
                const SizedBox(width: 6),
                const Text(
                  'Original Medical Evidence & Report',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF004D40),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

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
              child: MarkdownBody(
                data: originalContent,
                selectable: true,
                styleSheet: MarkdownStyleSheet(
                  p: const TextStyle(
                    fontSize: 15,
                    height: 1.6,
                    color: Color(0xFF37474F),
                    letterSpacing: 0.2,
                  ),
                  strong: const TextStyle(
                    fontWeight: FontWeight.bold,
                    color: Colors.black87,
                  ),
                  listBullet: const TextStyle(
                    color: Color(0xFF00796B),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 24),

            // 4. 來源卡片
            Container(
              padding: const EdgeInsets.all(16.0),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: const Color(0xFF00796B).withOpacity(0.2),
                ),
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
                        child: const Icon(
                          Icons.verified_outlined,
                          size: 18,
                          color: Color(0xFF00796B),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'VERIFIED SOURCE',
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                                color: Colors.grey,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              hasSource ? sourceText : 'PUBHEALTH Dataset',
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
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 12.0),
                    child: Divider(height: 1),
                  ),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 10,
                    ),
                    decoration: BoxDecoration(
                      color: const Color(0xFF00796B).withOpacity(0.05),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Row(
                      children: const [
                        Icon(
                          Icons.library_books_outlined,
                          size: 16,
                          color: Color(0xFF00796B),
                        ),
                        SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            'Archived from PUBHEALTH Dataset',
                            style: TextStyle(
                              color: Color(0xFF00796B),
                              fontWeight: FontWeight.w600,
                              fontSize: 13,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  ),
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