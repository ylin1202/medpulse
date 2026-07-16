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
      setState(() => _isLoading = false);
      return;
    }

    try {
      print('[Drug Detail] Fetching detail for ID: ${_drugDetail.id}');
      final response = await ApiClient().dio.get('/drugs/${_drugDetail.id}'); // 💡 依 baseUrl 調整路徑

      if (response.statusCode == 200) {
        final rawData = response.data['data'] ?? response.data;
        setState(() {
          _drugDetail = DrugModel.fromJson(rawData);
          _isLoading = false;
        });
      }
    } catch (e) {
      print('[Drug Detail Error]: $e (Showing preliminary data)');
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_drugDetail.brandName, style: const TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: const Color(0xFF00796B),
        foregroundColor: Colors.white,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: Color(0xFF00796B)))
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // 1. 藥品頂部基本資訊卡片
                  Card(
                    elevation: 3,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                    color: Colors.teal[50],
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Row(
                        children: [
                          const CircleAvatar(
                            radius: 28,
                            backgroundColor: Color(0xFF00796B),
                            child: Icon(Icons.medication, color: Colors.white, size: 32),
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  _drugDetail.brandName,
                                  style: const TextStyle(
                                    fontSize: 20,
                                    fontWeight: FontWeight.bold,
                                    color: Color(0xFF004D40),
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  'Generic: ${_drugDetail.genericName}',
                                  style: TextStyle(
                                    fontSize: 14,
                                    fontWeight: FontWeight.w600,
                                    color: Colors.teal[800],
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  'Manufacturer: ${_drugDetail.manufacturer}',
                                  style: TextStyle(fontSize: 12, color: Colors.grey[700]),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 20),

                  // 2. 詳細資訊卡片區塊
                  _buildSectionCard(
                    title: 'Indications & Usage',
                    content: _drugDetail.indications,
                    icon: Icons.assignment_turned_in_outlined,
                    iconColor: const Color(0xFF00796B),
                  ),
                  const SizedBox(height: 12),

                  _buildSectionCard(
                    title: 'Dosage & Administration',
                    content: _drugDetail.dosage,
                    icon: Icons.access_time,
                    iconColor: Colors.blue[700]!,
                  ),
                  const SizedBox(height: 12),

                  _buildSectionCard(
                    title: 'Warnings & Precautions',
                    content: _drugDetail.warnings,
                    icon: Icons.warning_amber_rounded,
                    iconColor: Colors.orange[800]!,
                  ),
                  const SizedBox(height: 12),

                  _buildSectionCard(
                    title: 'Adverse Reactions',
                    content: _drugDetail.adverseReactions,
                    icon: Icons.report_problem_outlined,
                    iconColor: Colors.red[700]!,
                  ),
                ],
              ),
            ),
    );
  }

  Widget _buildSectionCard({
    required String title,
    required String content,
    required IconData icon,
    required Color iconColor,
  }) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: iconColor, size: 22),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    title,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: Colors.black87,
                    ),
                  ),
                ),
              ],
            ),
            const Divider(height: 20),
            Text(
              content,
              style: const TextStyle(
                fontSize: 14,
                height: 1.5,
                color: Colors.black54,
              ),
            ),
          ],
        ),
      ),
    );
  }
}