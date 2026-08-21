class MetricReferenceModel {
  final double? lower;
  final double? upper;
  final String? unit;
  final String? definition;

  MetricReferenceModel({
    this.lower,
    this.upper,
    this.unit,
    this.definition,
  });

  factory MetricReferenceModel.fromJson(Map<String, dynamic> json) {
    return MetricReferenceModel(
      lower: json['lower'] != null ? (json['lower'] as num).toDouble() : null,
      upper: json['upper'] != null ? (json['upper'] as num).toDouble() : null,
      unit: json['unit'],
      definition: json['definition'],
    );
  }
}

/// Data model representing clinical lab analysis responses returned by FastAPI (/api/v1/analyze)
class AnalysisResponseModel {
  final String status;
  final int detectedMetricsCount;
  final String? clinicalSynthesis; // LLM-generated synthesis and RAG narrative
  final Map<String, MetricReferenceModel> metricsReference;
  final int totalAttemptsUsed;
  final bool cached;

  AnalysisResponseModel({
    required this.status,
    required this.detectedMetricsCount,
    this.clinicalSynthesis,
    required this.metricsReference,
    required this.totalAttemptsUsed,
    required this.cached,
  });

  factory AnalysisResponseModel.fromJson(Map<String, dynamic> json) {
    final rawMetrics = json['metrics_reference'] as Map<String, dynamic>? ?? {};
    final Map<String, MetricReferenceModel> parsedMetrics = {};

    rawMetrics.forEach((key, value) {
      if (value is Map<String, dynamic>) {
        parsedMetrics[key] = MetricReferenceModel.fromJson(value);
      }
    });

    return AnalysisResponseModel(
      status: json['status'] ?? 'unknown',
      detectedMetricsCount: json['detected_metrics_count'] ?? 0,
      clinicalSynthesis: json['clinical_synthesis']?.toString(),
      metricsReference: parsedMetrics,
      totalAttemptsUsed: json['total_attempts_used'] ?? 1,
      cached: json['cached'] ?? false,
    );
  }
}