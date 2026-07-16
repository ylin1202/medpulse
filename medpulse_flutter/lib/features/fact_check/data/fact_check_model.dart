class FactCheckModel {
  final String id;
  final String claim;
  final String verdict;
  final String summary;
  final String explanation;
  final String source;
  final String claimUrl;
  final double? score; // RAG 語意相似度分數 (例如 0.85)

  FactCheckModel({
    required this.id,
    required this.claim,
    required this.verdict,
    required this.summary,
    required this.explanation,
    required this.source,
    required this.claimUrl,
    this.score,
  });

  factory FactCheckModel.fromJson(Map<String, dynamic> json) {
    return FactCheckModel(
      id: json['id']?.toString() ?? '',
      claim: json['claim'] ?? json['title'] ?? '',
      verdict: json['label'] ?? json['verdict'] ?? 'Unverified',
      summary: json['main_text'] ?? json['summary'] ?? '',
      explanation: json['explanation'] ?? json['detail'] ?? '',
      source: json['sources'] ?? json['source'] ?? 'Medical Fact-Check Center',
      claimUrl: json['claim_url'] ?? '',
      score: json['score'] != null ? (json['score'] as num).toDouble() : null,
    );
  }
}