class FactCheckModel {
  final String id;
  final String claim;
  final String verdict;
  final String summary;
  final String explanation; // AI 生成摘要 (Dialog 彈窗用)
  final String originalExplanation; // 資料庫原始文獻 (DetailScreen 內文用)
  final String source; // 上方機構名稱 (如 The Wall Street Journal)
  final String claimUrl; // 下方原始連結 (如 wsj.com 或完整 URL)
  final double? score;

  FactCheckModel({
    required this.id,
    required this.claim,
    required this.verdict,
    required this.summary,
    required this.explanation,
    required this.originalExplanation,
    required this.source,
    required this.claimUrl,
    this.score,
  });

  /// 將 raw sources 字串格式化為機構名稱
  static String _formatPublisherName(String raw) {
    final s = raw.toLowerCase().trim();
    if (s.isEmpty) return 'PUBHEALTH Dataset';

    if (s.contains('wsj')) return 'The Wall Street Journal';
    if (s.contains('snopes')) return 'Snopes';
    if (s.contains('politifact')) return 'PolitiFact';
    if (s.contains('factcheck')) return 'FactCheck.org';
    if (s.contains('healthfeedback') || s.contains('sciencefeedback'))
      return 'Health Feedback';
    if (s.contains('nytimes') || s.contains('new york times'))
      return 'The New York Times';
    if (s.contains('washingtonpost') || s.contains('wapo'))
      return 'The Washington Post';
    if (s.contains('reuters')) return 'Reuters Fact Check';
    if (s.contains('apnews') || s.contains('associated press'))
      return 'Associated Press';
    if (s.contains('who.int') || s.contains('who'))
      return 'World Health Organization (WHO)';
    if (s.contains('cdc.gov') || s.contains('cdc')) return 'CDC';
    if (s.contains('bbc')) return 'BBC News';
    if (s.contains('cnn')) return 'CNN';

    if (s.contains('.')) {
      String clean = s.replaceAll('http://', '').replaceAll('https://', '');
      if (clean.startsWith('www.')) clean = clean.substring(4);
      return clean.split('/').first;
    }

    return raw.length > 1
        ? '${raw[0].toUpperCase()}${raw.substring(1)}'
        : raw.toUpperCase();
  }

  factory FactCheckModel.fromJson(Map<String, dynamic> json) {
    // 取得資料庫中原始的 sources 欄位值
    final String rawSources =
        (json['sources'] ?? json['source'] ?? json['claim_url'] ?? '')
            .toString()
            .trim();

    final String origExp = (json['original_explanation'] ?? '')
        .toString()
        .trim();
    final String mainText = (json['main_text'] ?? '').toString().trim();
    final String exp = (json['explanation'] ?? '').toString().trim();

    final String resolvedOriginalExplanation = origExp.isNotEmpty
        ? origExp
        : (mainText.isNotEmpty ? mainText : exp);

    final String rawSummary = (json['summary'] ?? '').toString().trim();
    final String resolvedSummary = rawSummary.isNotEmpty ? rawSummary : exp;

    return FactCheckModel(
      id: json['id']?.toString() ?? '',
      claim: json['claim'] ?? json['matched_claim'] ?? 'No Claim',
      verdict: json['verdict'] ?? json['label'] ?? 'UNVERIFIED',
      summary: resolvedSummary,
      explanation: exp,
      originalExplanation: resolvedOriginalExplanation,
      source: _formatPublisherName(rawSources), // 上方顯示機構名
      claimUrl: rawSources, // 下方保留原始來源連結
      score: json['score'] != null
          ? (json['score'] as num).toDouble()
          : (json['similarity_score'] != null
                ? (json['similarity_score'] as num).toDouble()
                : null),
    );
  }
}
