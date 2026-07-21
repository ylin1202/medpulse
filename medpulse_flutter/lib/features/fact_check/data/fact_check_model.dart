// fact_check_model.dart
class FactCheckModel {
  final String id;
  final String claim;
  final String verdict;
  final String summary;
  final String explanation;
  final String source;
  final String claimUrl;
  final double? score;

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
      claim: json['claim'] ?? json['matched_claim'] ?? json['title'] ?? 'No Claim',
      verdict: json['verdict'] ?? json['label'] ?? 'UNVERIFIED',
      summary: json['summary'] ?? json['explanation'] ?? '',
      explanation: json['explanation'] ?? json['detail'] ?? '',
      source: json['source'] ?? 'Medical Fact-Check Center',
      claimUrl: json['claim_url'] ?? json['source_url'] ?? '',
      score: json['score'] != null 
          ? (json['score'] as num).toDouble() 
          : (json['similarity_score'] != null ? (json['similarity_score'] as num).toDouble() : null),
    );
  }
}