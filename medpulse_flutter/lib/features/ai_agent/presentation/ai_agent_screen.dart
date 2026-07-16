import 'package:flutter/material.dart';
import '../../../../core/network/api_client.dart';
import '../data/analysis_model.dart';

class AiAgentScreen extends StatefulWidget {
  const AiAgentScreen({super.key});

  @override
  State<AiAgentScreen> createState() => _AiAgentScreenState();
}

class _AiAgentScreenState extends State<AiAgentScreen> {
  final TextEditingController _clinicalTextController = TextEditingController();
  bool _isLoading = false;
  AnalysisResponseModel? _analysisResult;
  String? _errorMessage;

  // 預設快速病歷範例
  final List<String> _sampleNotes = [
    "Patient was brought to the ER with high fever. Urgent lab tests requested for Glucose, White Blood Cells, and Potassium.",
    "Patient with chronic fatigue. Lab test requested for Hemoglobin and Red Blood Cells.",
  ];

  /// 呼叫 FastAPI 臨床病歷分析端點 (POST /api/v1/analyze)
  Future<void> _analyzeClinicalText(String text) async {
    if (text.trim().isEmpty) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      print('[AI Agent] Sending clinical text to FastAPI /api/v1/analyze');

      // 呼叫 FastAPI 端點
      final response = await ApiClient().fastApiDio.post(
        '/analyze',
        data: {'clinical_text': text.trim()},
      );

      print('[AI Agent] Response Status: ${response.statusCode}');

      if (response.statusCode == 200) {
        setState(() {
          _analysisResult = AnalysisResponseModel.fromJson(response.data);
          _isLoading = false;
        });
      }
    } catch (e) {
      print('[AI Agent Error]: $e');
      setState(() {
        _errorMessage = 'Failed to analyze clinical text. Make sure FastAPI is running.';
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8F9FA),
      appBar: AppBar(
        title: Row(
          children: const [
            Icon(Icons.smart_toy_outlined, size: 24),
            SizedBox(width: 8),
            Text('MedPulse AI Agent', style: TextStyle(fontWeight: FontWeight.bold)),
          ],
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
            // 1. 病歷輸入卡片
            Container(
              padding: const EdgeInsets.all(16),
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
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: const [
                      Icon(Icons.assignment_outlined, color: Color(0xFF00796B), size: 20),
                      SizedBox(width: 8),
                      Text(
                        'Clinical Notes Input',
                        style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Color(0xFF004D40)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _clinicalTextController,
                    maxLines: 4,
                    style: const TextStyle(fontSize: 14),
                    decoration: InputDecoration(
                      hintText: 'Enter clinical notes or patient lab requests here...',
                      hintStyle: TextStyle(color: Colors.grey[400], fontSize: 13),
                      filled: true,
                      fillColor: const Color(0xFFF8F9FA),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide.none,
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // 快速範例 Chips
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: _sampleNotes.map((sample) {
                        return Padding(
                          padding: const EdgeInsets.only(right: 8.0),
                          child: ActionChip(
                            avatar: const Icon(Icons.add_rounded, size: 16, color: Color(0xFF00796B)),
                            label: Text(
                              sample.length > 30 ? '${sample.substring(0, 30)}...' : sample,
                              style: const TextStyle(fontSize: 11, color: Color(0xFF00796B)),
                            ),
                            backgroundColor: Colors.teal[50],
                            onPressed: () {
                              _clinicalTextController.text = sample;
                            },
                          ),
                        );
                      }).toList(),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // 分析按鈕
                  SizedBox(
                    width: double.infinity,
                    height: 48,
                    child: ElevatedButton.icon(
                      onPressed: _isLoading
                          ? null
                          : () => _analyzeClinicalText(_clinicalTextController.text),
                      icon: const Icon(Icons.psychology_outlined),
                      label: const Text('Analyze with LangGraph Agent', style: TextStyle(fontWeight: FontWeight.bold)),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF00796B),
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // 2. 載入與錯誤狀態
            if (_isLoading)
              Center(
                child: Padding(
                  padding: const EdgeInsets.all(32.0),
                  child: Column(
                    children: const [
                      CircularProgressIndicator(color: Color(0xFF00796B)),
                      SizedBox(height: 16),
                      Text('Gemma-3 & LangGraph Reasoning...', style: TextStyle(color: Colors.grey, fontWeight: FontWeight.bold)),
                    ],
                  ),
                ),
              ),

            if (_errorMessage != null)
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: Colors.red[50], borderRadius: BorderRadius.circular(12)),
                child: Row(
                  children: [
                    const Icon(Icons.error_outline, color: Colors.red),
                    const SizedBox(width: 8),
                    Expanded(child: Text(_errorMessage!, style: const TextStyle(color: Colors.red, fontSize: 13))),
                  ],
                ),
              ),

            // 3. 分析結果展示面板
            if (_analysisResult != null && !_isLoading) ...[
              // 標頭 Status Badge (Redis 快取 / LangGraph 重試次數)
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.analytics_outlined, color: Color(0xFF00796B), size: 20),
                      const SizedBox(width: 6),
                      Text(
                        'Detected Metrics (${_analysisResult!.detectedMetricsCount})',
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Color(0xFF004D40)),
                      ),
                    ],
                  ),
                  Row(
                    children: [
                      if (_analysisResult!.cached)
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(color: Colors.amber[100], borderRadius: BorderRadius.circular(8)),
                          child: Row(
                            children: const [
                              Icon(Icons.bolt, size: 14, color: Colors.amber),
                              SizedBox(width: 2),
                              Text('Redis HIT (5ms)', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.brown)),
                            ],
                          ),
                        )
                      else
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(color: Colors.teal[50], borderRadius: BorderRadius.circular(8)),
                          child: Text(
                            'Attempts: ${_analysisResult!.totalAttemptsUsed}',
                            style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF00796B)),
                          ),
                        ),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // 指標詳情卡片清單
              if (_analysisResult!.metricsReference.isEmpty)
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
                  child: const Center(
                    child: Text('No MIMIC lab metrics detected in clinical text.', style: TextStyle(color: Colors.grey)),
                  ),
                )
              else
                ListView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: _analysisResult!.metricsReference.length,
                  itemBuilder: (context, index) {
                    final metricName = _analysisResult!.metricsReference.keys.elementAt(index);
                    final metricData = _analysisResult!.metricsReference[metricName]!;

                    return Card(
                      elevation: 2,
                      margin: const EdgeInsets.only(bottom: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(
                                  metricName,
                                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Color(0xFF00796B)),
                                ),
                                if (metricData.unit != null)
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                    decoration: BoxDecoration(color: Colors.grey[100], borderRadius: BorderRadius.circular(6)),
                                    child: Text(
                                      metricData.unit!,
                                      style: TextStyle(fontSize: 11, color: Colors.grey[700], fontWeight: FontWeight.w600),
                                    ),
                                  ),
                              ],
                            ),
                            const SizedBox(height: 8),

                            // 參考值範圍
                            if (metricData.lower != null || metricData.upper != null) ...[
                              Row(
                                children: [
                                  const Icon(Icons.straighten_outlined, size: 16, color: Colors.grey),
                                  const SizedBox(width: 6),
                                  Text(
                                    'Reference Range: ${metricData.lower ?? 'N/A'} ~ ${metricData.upper ?? 'N/A'} ${metricData.unit ?? ''}',
                                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: Colors.black87),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 8),
                            ],

                            // MedlinePlus 醫學定義
                            if (metricData.definition != null) ...[
                              const Divider(),
                              Text(
                                metricData.definition!,
                                style: TextStyle(fontSize: 12, height: 1.4, color: Colors.grey[700]),
                              ),
                            ],
                          ],
                        ),
                      ),
                    );
                  },
                ),
            ],
          ],
        ),
      ),
    );
  }
}