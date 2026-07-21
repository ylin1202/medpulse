import 'package:flutter/material.dart';
import '../../../../core/network/api_client.dart';
import '../data/drug_model.dart';

class DrugDetailScreen extends StatefulWidget {
  final DrugModel drug;

  const DrugDetailScreen({super.key, required this.drug});

  @override
  State<DrugDetailScreen> createState() => _DrugDetailScreenState();
}

class _DrugDetailScreenState extends State<DrugDetailScreen> {
  late DrugModel _drugDetail;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _drugDetail = widget.drug;
    _fetchDrugDetail();
  }

  /// 呼叫 Flask 取得單一藥品詳細說明書 (GET /api/v1/drugs/<drug_id>)
  Future<void> _fetchDrugDetail() async {
    if (_drugDetail.id.isEmpty) {
      if (mounted) setState(() => _isLoading = false);
      return;
    }

    try {
      debugPrint('[Drug Detail] Fetching detail for ID: ${_drugDetail.id}');
      final response = await ApiClient().dio.get('/drugs/${_drugDetail.id}');

      if (response.statusCode == 200 && mounted) {
        final rawData = response.data['data'] ?? response.data;
        setState(() {
          _drugDetail = DrugModel.fromJson(rawData);
          _isLoading = false;
        });
      }
    } catch (e) {
      debugPrint('[Drug Detail Error]: $e (Showing preliminary data)');
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8F9FA), // 柔和灰底
      appBar: AppBar(
        title: const Text(
          'Drug Information',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
        ),
        backgroundColor: const Color(0xFF00796B),
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: Color(0xFF00796B)),
            )
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // 1. 藥品頂部英雄卡片 (Hero Header Banner)
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
                            // 主題膠囊 Icon
                            Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: const Color(0xFF00796B).withOpacity(0.1),
                                borderRadius: BorderRadius.circular(14),
                              ),
                              child: const Icon(
                                Icons.medication,
                                color: Color(0xFF00796B),
                                size: 30,
                              ),
                            ),
                            const SizedBox(width: 14),

                            // 藥名與通用名
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    _drugDetail.brandName,
                                    style: const TextStyle(
                                      fontSize: 18,
                                      fontWeight: FontWeight.bold,
                                      color: Color(0xFF004D40),
                                      height: 1.25,
                                    ),
                                  ),
                                  const SizedBox(height: 6),
                                  Text(
                                    'Generic: ${_drugDetail.genericName}',
                                    style: TextStyle(
                                      fontSize: 13,
                                      fontWeight: FontWeight.w600,
                                      color: Colors.teal[800],
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const Padding(
                          padding: EdgeInsets.symmetric(vertical: 12),
                          child: Divider(height: 1, color: Color(0xFFE0E0E0)),
                        ),

                        // 底部詳細資訊與標籤
                        Row(
                          children: [
                            const Icon(
                              Icons.business_outlined,
                              size: 16,
                              color: Colors.grey,
                            ),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                'Mfr: ${_drugDetail.manufacturer.isNotEmpty ? _drugDetail.manufacturer : 'Unknown'}',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Colors.grey[700],
                                  fontWeight: FontWeight.w500,
                                ),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),

                  // 2. 詳細內容區塊列表
                  _buildSectionCard(
                    title: 'Indications & Usage',
                    content: _drugDetail.indications,
                    icon: Icons.assignment_turned_in_outlined,
                    accentColor: const Color(0xFF00796B),
                  ),
                  const SizedBox(height: 12),

                  _buildSectionCard(
                    title: 'Dosage & Administration',
                    content: _drugDetail.dosage,
                    icon: Icons.access_time_filled_rounded,
                    accentColor: const Color(0xFF0288D1),
                  ),
                  const SizedBox(height: 12),

                  _buildSectionCard(
                    title: 'Warnings & Precautions',
                    content: _drugDetail.warnings,
                    icon: Icons.warning_rounded,
                    accentColor: const Color(0xFFF57C00),
                  ),
                  const SizedBox(height: 12),

                  _buildSectionCard(
                    title: 'Adverse Reactions',
                    content: _drugDetail.adverseReactions,
                    icon: Icons.report_problem_rounded,
                    accentColor: const Color(0xFFD32F2F),
                  ),
                  const SizedBox(height: 24),
                ],
              ),
            ),
    );
  }

  Widget _buildSectionCard({
    required String title,
    required String content,
    required IconData icon,
    required Color accentColor,
  }) {
    final bool hasContent = content.trim().isNotEmpty;

    return Container(
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
          // 標題列 (帶淡色彩標區塊)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: accentColor.withOpacity(0.06),
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(14),
                topRight: Radius.circular(14),
              ),
            ),
            child: Row(
              children: [
                Icon(icon, color: accentColor, size: 20),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    color: accentColor,
                  ),
                ),
              ],
            ),
          ),

          // 內文區域
          Padding(
            padding: const EdgeInsets.all(14.0),
            child: Text(
              hasContent ? content : 'No specific information provided for this section.',
              style: TextStyle(
                fontSize: 13.5,
                height: 1.5,
                color: hasContent ? Colors.black87 : Colors.grey[400],
                fontStyle: hasContent ? FontStyle.normal : FontStyle.italic,
              ),
            ),
          ),
        ],
      ),
    );
  }
}