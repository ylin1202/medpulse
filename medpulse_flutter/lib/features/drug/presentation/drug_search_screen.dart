import 'package:flutter/material.dart';
import '../../../../core/network/api_client.dart';
import '../data/drug_model.dart';
import 'drug_detail_screen.dart';

class DrugSearchScreen extends StatefulWidget {
  const DrugSearchScreen({super.key});

  @override
  State<DrugSearchScreen> createState() => _DrugSearchScreenState();
}

class _DrugSearchScreenState extends State<DrugSearchScreen> {
  final TextEditingController _searchController = TextEditingController();
  List<DrugModel> _searchResults = [];
  bool _isLoading = false;
  
  // 分頁控制
  int _currentPage = 1;
  final int _limit = 10;
  int _totalPages = 1;
  int _totalItems = 0;

  @override
  void initState() {
    super.initState();
    // 畫面一載入，立即發送請求獲取第一頁藥品清單
    _fetchDrugs();
  }

  /// 呼叫 Flask 後端取得藥品清單與搜尋 API (GET /api/v1/drugs)
  Future<void> _fetchDrugs({String? query, int page = 1}) async {
    setState(() {
      _isLoading = true;
    });

    try {
      final String keyword = (query ?? _searchController.text).trim();
      final Map<String, dynamic> queryParams = {
        'page': page,
        'limit': _limit,
      };

      if (keyword.isNotEmpty) {
        queryParams['q'] = keyword;
      }

      print('[Drug Finder] Fetching page $page with query: "$keyword"');

      final response = await ApiClient().dio.get(
        '/drugs',
        queryParameters: queryParams,
      );

      print('[Drug Finder] Response Status: ${response.statusCode}');

      if (response.statusCode == 200) {
        final List rawData = response.data['data'] ?? [];
        final items = rawData.map((e) => DrugModel.fromJson(e)).toList();
        final pagination = response.data['pagination'] ?? {};

        setState(() {
          _searchResults = items;
          _currentPage = pagination['page'] ?? page;
          _totalPages = pagination['total_pages'] ?? 1;
          _totalItems = pagination['total'] ?? items.length;
          _isLoading = false;
        });
      }
    } catch (e) {
      print('[Drug Finder Error]: $e');
      setState(() {
        _searchResults = [];
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Drug Finder', style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: const Color(0xFF00796B),
        foregroundColor: Colors.white,
      ),
      body: Column(
        children: [
          // 1. 頂部搜尋列
          Container(
            padding: const EdgeInsets.all(16.0),
            color: const Color(0xFF00796B).withOpacity(0.05),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _searchController,
                    textInputAction: TextInputAction.search,
                    decoration: InputDecoration(
                      hintText: 'Search drug name (e.g. minoxidil, aspirin)...',
                      prefixIcon: const Icon(Icons.search, color: Color(0xFF00796B)),
                      suffixIcon: _searchController.text.isNotEmpty
                          ? IconButton(
                              icon: const Icon(Icons.clear),
                              onPressed: () {
                                _searchController.clear();
                                _fetchDrugs(query: '', page: 1);
                              },
                            )
                          : null,
                      filled: true,
                      fillColor: Colors.white,
                      contentPadding: const EdgeInsets.symmetric(vertical: 12),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide.none,
                      ),
                    ),
                    onSubmitted: (value) => _fetchDrugs(query: value, page: 1),
                  ),
                ),
                const SizedBox(width: 8),
                ElevatedButton(
                  onPressed: () => _fetchDrugs(query: _searchController.text, page: 1),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF00796B),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: const Text('Search'),
                ),
              ],
            ),
          ),

          // 2. 藥品清單與狀態展示
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator(color: Color(0xFF00796B)))
                : _searchResults.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.medication_outlined, size: 64, color: Colors.grey[400]),
                            const SizedBox(height: 12),
                            Text(
                              'No drugs found.',
                              style: TextStyle(fontSize: 16, color: Colors.grey[600]),
                            ),
                          ],
                        ),
                      )
                    : Column(
                        children: [
                          // 筆數統計資訊
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(
                                  'Total: $_totalItems drugs',
                                  style: TextStyle(color: Colors.grey[600], fontSize: 13, fontWeight: FontWeight.w500),
                                ),
                                Text(
                                  'Page $_currentPage / $_totalPages',
                                  style: TextStyle(color: Colors.grey[600], fontSize: 13, fontWeight: FontWeight.w500),
                                ),
                              ],
                            ),
                          ),

                          // 列表內容
                          Expanded(
                            child: ListView.builder(
                              padding: const EdgeInsets.symmetric(horizontal: 16),
                              itemCount: _searchResults.length,
                              itemBuilder: (context, index) {
                                final drug = _searchResults[index];
                                return Card(
                                  elevation: 2,
                                  margin: const EdgeInsets.only(bottom: 12),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: ListTile(
                                    contentPadding: const EdgeInsets.all(16),
                                    leading: CircleAvatar(
                                      backgroundColor: const Color(0xFF00796B).withOpacity(0.1),
                                      child: const Icon(Icons.medication, color: Color(0xFF00796B)),
                                    ),
                                    title: Text(
                                      drug.brandName,
                                      style: const TextStyle(
                                        fontWeight: FontWeight.bold,
                                        fontSize: 16,
                                      ),
                                    ),
                                    subtitle: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        const SizedBox(height: 4),
                                        Text(
                                          'Generic: ${drug.genericName}',
                                          style: TextStyle(color: Colors.grey[700]),
                                        ),
                                        const SizedBox(height: 2),
                                        Text(
                                          'Mfr: ${drug.manufacturer}',
                                          style: TextStyle(color: Colors.grey[500], fontSize: 12),
                                        ),
                                      ],
                                    ),
                                    trailing: const Icon(Icons.chevron_right, color: Colors.grey),
                                    onTap: () {
                                      Navigator.push(
                                        context,
                                        MaterialPageRoute(
                                          builder: (context) => DrugDetailScreen(drug: drug),
                                        ),
                                      );
                                    },
                                  ),
                                );
                              },
                            ),
                          ),

                          // 3. 底部簡易分頁切換控制 (Pagination)
                          if (_totalPages > 1)
                            Container(
                              padding: const EdgeInsets.symmetric(vertical: 8),
                              decoration: BoxDecoration(
                                color: Colors.white,
                                boxShadow: [
                                  BoxShadow(
                                    color: Colors.black.withOpacity(0.05),
                                    blurRadius: 4,
                                    offset: const Offset(0, -2),
                                  ),
                                ],
                              ),
                              child: Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  IconButton(
                                    icon: const Icon(Icons.arrow_back_ios, size: 18),
                                    onPressed: _currentPage > 1
                                        ? () => _fetchDrugs(page: _currentPage - 1)
                                        : null,
                                  ),
                                  Text(
                                    '$_currentPage / $_totalPages',
                                    style: const TextStyle(fontWeight: FontWeight.bold),
                                  ),
                                  IconButton(
                                    icon: const Icon(Icons.arrow_forward_ios, size: 18),
                                    onPressed: _currentPage < _totalPages
                                        ? () => _fetchDrugs(page: _currentPage + 1)
                                        : null,
                                  ),
                                ],
                              ),
                            ),
                        ],
                      ),
          ),
        ],
      ),
    );
  }
}