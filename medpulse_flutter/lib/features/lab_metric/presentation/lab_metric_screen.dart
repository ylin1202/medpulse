import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:dio/dio.dart';
import '../../../../core/network/api_client.dart';
import '../data/analysis_model.dart';

class AiAgentScreen extends StatefulWidget {
  const AiAgentScreen({super.key});

  @override
  State<AiAgentScreen> createState() => _AiAgentScreenState();
}

class _AiAgentScreenState extends State<AiAgentScreen> {
  final TextEditingController _clinicalTextController =
      TextEditingController();
  bool _isLoading = false;
  AnalysisResponseModel? _analysisResult;
  String? _errorMessage;

  // Pre-configured clinical note samples for prompt evaluation
  final List<String> _sampleNotes = [
    "Patient was brought to the ER with high fever. Urgent lab tests requested for Glucose, White Blood Cells, and Potassium.",
    "Patient with chronic fatigue. Lab test requested for Hemoglobin and Red Blood Cells.",
  ];

  /// Dispatches unstructured clinical text to FastAPI reasoning endpoint (POST /api/v1/analyze).
  Future<void> _analyzeClinicalText(String text) async {
    if (text.trim().isEmpty) return;

    FocusScope.of(context).unfocus(); // Dismiss active soft keyboard

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      debugPrint('[AI Agent] Dispatching clinical payload to FastAPI /api/v1/analyze');

      final response = await ApiClient().fastApiDio.post(
        '/api/v1/analyze',
        data: {'clinical_text': text.trim()},
        options: Options(
          receiveTimeout: const Duration(seconds: 90),
          sendTimeout: const Duration(seconds: 30),
        ),
      );

      debugPrint('[AI Agent] Response Status: ${response.statusCode}');

      if (response.statusCode == 200 && mounted) {
        setState(() {
          _analysisResult = AnalysisResponseModel.fromJson(response.data);
          _isLoading = false;
        });
      }
    } on DioException catch (dioErr) {
      debugPrint('[AI Agent DioError]: ${dioErr.type} - ${dioErr.message}');
      if (mounted) {
        String message = 'Failed to analyze clinical text.';
        if (dioErr.type == DioExceptionType.receiveTimeout) {
          message = 'The AI Agent analysis timed out. Multi-stage clinical reasoning took longer than expected. Please try again.';
        } else if (dioErr.type == DioExceptionType.connectionError ||
                   dioErr.type == DioExceptionType.connectionTimeout) {
          message = 'Unable to connect to AI Agent service at localhost:8000. Please ensure the backend container is running.';
        }
        setState(() {
          _errorMessage = message;
          _isLoading = false;
        });
      }
    } catch (e) {
      debugPrint('[AI Agent Error]: $e');
      if (mounted) {
        setState(() {
          _errorMessage = 'An unexpected error occurred during medical analysis: $e';
          _isLoading = false;
        });
      }
    }
  }

  @override
  void dispose() {
    _clinicalTextController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final hasSynthesis = _analysisResult?.clinicalSynthesis != null &&
        _analysisResult!.clinicalSynthesis!.trim().isNotEmpty;

    return Scaffold(
      backgroundColor: const Color(0xFFF8F9FA),
      appBar: AppBar(
        title: const Text(
          'Lab Metric Explorer',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: const Color(0xFF00796B),
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 1. Clinical Analysis Hero Card
            Container(
              padding: const EdgeInsets.all(16.0),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.teal.shade100, width: 1.2),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.03),
                    blurRadius: 10,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Themed Icon Badge
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: const Color(0xFF00796B).withOpacity(0.1),
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: const Icon(
                          Icons.psychology_outlined,
                          color: Color(0xFF00796B),
                          size: 30,
                        ),
                      ),
                      const SizedBox(width: 14),

                      // Title and Model Capability Tag
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Lab Metric Search',
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                                color: Color(0xFF004D40),
                                height: 1.25,
                              ),
                            ),
                            const SizedBox(height: 6),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 8,
                                vertical: 3,
                              ),
                              decoration: BoxDecoration(
                                color: Colors.teal.shade50,
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: const Text(
                                'Explore Lab Metrics',
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.bold,
                                  color: Color(0xFF00695C),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),

                  // Clinical text input field
                  TextField(
                    controller: _clinicalTextController,
                    maxLines: 3,
                    style: const TextStyle(fontSize: 13.5),
                    decoration: InputDecoration(
                      hintText:
                          'Enter clinical note (e.g., patient condition, requested lab tests)...',
                      hintStyle: TextStyle(
                        color: Colors.grey[400],
                        fontSize: 13,
                      ),
                      filled: true,
                      fillColor: const Color(0xFFF8F9FA),
                      contentPadding: const EdgeInsets.all(12),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide(color: Colors.grey.shade200),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide(color: Colors.grey.shade200),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: const BorderSide(
                          color: Color(0xFF00796B),
                          width: 1.5,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // Quick Sample Prompt Chips
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: _sampleNotes.map((sample) {
                        return Padding(
                          padding: const EdgeInsets.only(right: 8.0),
                          child: InkWell(
                            onTap: () {
                              _clinicalTextController.text = sample;
                            },
                            borderRadius: BorderRadius.circular(8),
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 10,
                                vertical: 5,
                              ),
                              decoration: BoxDecoration(
                                color:
                                    const Color(0xFF00796B).withOpacity(0.06),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Row(
                                children: [
                                  const Icon(
                                    Icons.add,
                                    size: 13,
                                    color: Color(0xFF00796B),
                                  ),
                                  const SizedBox(width: 4),
                                  Text(
                                    sample.length > 26
                                        ? '${sample.substring(0, 26)}...'
                                        : sample,
                                    style: const TextStyle(
                                      fontSize: 11,
                                      fontWeight: FontWeight.w500,
                                      color: Color(0xFF004D40),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                  ),
                  const SizedBox(height: 14),

                  // Execute Analysis Button
                  SizedBox(
                    width: double.infinity,
                    height: 44,
                    child: ElevatedButton.icon(
                      onPressed: _isLoading
                          ? null
                          : () => _analyzeClinicalText(
                                _clinicalTextController.text,
                              ),
                      icon: const Icon(Icons.auto_awesome, size: 18),
                      label: const Text(
                        'Execute Medical RAG Analysis',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF00796B),
                        foregroundColor: Colors.white,
                        elevation: 0,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),

            // 2. Loading State Card
            if (_isLoading)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: Colors.teal.shade100),
                ),
                child: Center(
                  child: Column(
                    children: const [
                      CircularProgressIndicator(
                        color: Color(0xFF00796B),
                        strokeWidth: 3,
                      ),
                      SizedBox(height: 16),
                      Text(
                        'Synthesizing with LangGraph & Gemini...',
                        style: TextStyle(
                          color: Color(0xFF004D40),
                          fontWeight: FontWeight.bold,
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ),
                ),
              ),

            // 3. Error Alert Banner
            if (_errorMessage != null)
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.red.shade200),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.error_outline, color: Colors.red),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        _errorMessage!,
                        style: const TextStyle(color: Colors.red, fontSize: 13),
                      ),
                    ),
                  ],
                ),
              ),

            // 4. Clinical Results Panel
            if (_analysisResult != null && !_isLoading) ...[
              // AI Clinical Synthesis Section (Markdown formatted)
              if (hasSynthesis) ...[
                Container(
                  width: double.infinity,
                  margin: const EdgeInsets.only(bottom: 20),
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF0FDF4),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: Colors.teal.shade200, width: 1.2),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.teal.withOpacity(0.04),
                        blurRadius: 8,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: const [
                          Icon(
                            Icons.auto_awesome,
                            color: Color(0xFF00796B),
                            size: 18,
                          ),
                          SizedBox(width: 8),
                          Text(
                            'AI Clinical Interpretation & Synthesis',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 15,
                              color: Color(0xFF004D40),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      MarkdownBody(
                        data: _analysisResult!.clinicalSynthesis!.trim(),
                        styleSheet: MarkdownStyleSheet(
                          p: const TextStyle(
                            fontSize: 13.5,
                            height: 1.55,
                            color: Color(0xFF1B4D3E),
                            letterSpacing: 0.15,
                          ),
                          strong: const TextStyle(
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF004D40),
                          ),
                          listBullet: const TextStyle(
                            color: Color(0xFF00796B),
                            fontSize: 13.5,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],

              // Metrics Header & Cache/Extraction Status
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Detected Metrics (${_analysisResult!.detectedMetricsCount})',
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                      color: Color(0xFF004D40),
                    ),
                  ),
                  if (_analysisResult!.cached)
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 3,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.amber.shade100,
                        borderRadius: BorderRadius.circular(6),
                      ),
                    )
                  else
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 3,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.teal.shade50,
                        borderRadius: BorderRadius.circular(6),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 12),

              // Lab Reference Interval Card List
              if (_analysisResult!.metricsReference.isEmpty)
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: Colors.grey.shade200),
                  ),
                  child: const Center(
                    child: Text(
                      'No MIMIC lab metrics detected in clinical text.',
                      style: TextStyle(color: Colors.grey, fontSize: 13),
                    ),
                  ),
                )
              else
                ListView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: _analysisResult!.metricsReference.length,
                  itemBuilder: (context, index) {
                    final metricName = _analysisResult!.metricsReference.keys
                        .elementAt(index);
                    final metricData =
                        _analysisResult!.metricsReference[metricName]!;

                    return Container(
                      margin: const EdgeInsets.only(bottom: 12),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: Colors.grey.shade200),
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
                          // Card header with metric name and unit badge
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 14,
                              vertical: 10,
                            ),
                            decoration: BoxDecoration(
                              color: const Color(0xFF00796B).withOpacity(0.06),
                              borderRadius: const BorderRadius.only(
                                topLeft: Radius.circular(14),
                                topRight: Radius.circular(14),
                              ),
                            ),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Row(
                                  children: [
                                    const Icon(
                                      Icons.science_outlined,
                                      color: Color(0xFF00796B),
                                      size: 18,
                                    ),
                                    const SizedBox(width: 8),
                                    Text(
                                      metricName,
                                      style: const TextStyle(
                                        fontSize: 15,
                                        fontWeight: FontWeight.bold,
                                        color: Color(0xFF00796B),
                                      ),
                                    ),
                                  ],
                                ),
                                if (metricData.unit != null)
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 8,
                                      vertical: 2,
                                    ),
                                    decoration: BoxDecoration(
                                      color: Colors.white,
                                      borderRadius: BorderRadius.circular(6),
                                    ),
                                    child: Text(
                                      metricData.unit!,
                                      style: const TextStyle(
                                        fontSize: 11,
                                        color: Color(0xFF004D40),
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ),
                              ],
                            ),
                          ),

                          // Card content: reference range and definitions
                          Padding(
                            padding: const EdgeInsets.all(14.0),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                if (metricData.lower != null ||
                                    metricData.upper != null) ...[
                                  Row(
                                    children: [
                                      const Icon(
                                        Icons.straighten,
                                        size: 15,
                                        color: Colors.grey,
                                      ),
                                      const SizedBox(width: 6),
                                      Text(
                                        'Reference Range: ${metricData.lower ?? 'N/A'} ~ ${metricData.upper ?? 'N/A'} ${metricData.unit ?? ''}',
                                        style: const TextStyle(
                                          fontSize: 13,
                                          fontWeight: FontWeight.bold,
                                          color: Colors.black87,
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 8),
                                ],
                                Text(
                                  metricData.definition?.isNotEmpty == true
                                      ? metricData.definition!
                                      : 'No specific medical definition found for this metric.',
                                  style: TextStyle(
                                    fontSize: 13,
                                    height: 1.5,
                                    color: metricData.definition?.isNotEmpty == true
                                        ? Colors.black54
                                        : Colors.grey[400],
                                    fontStyle: metricData.definition?.isNotEmpty == true
                                        ? FontStyle.normal
                                        : FontStyle.italic,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
            ],
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}