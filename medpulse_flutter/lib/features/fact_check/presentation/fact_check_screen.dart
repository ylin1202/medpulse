import 'package:flutter/material.dart';
import '../../../../core/network/api_client.dart';
import '../data/fact_check_model.dart';
import 'fact_check_detail_screen.dart';

class FactCheckScreen extends StatefulWidget {
  const FactCheckScreen({super.key});

  @override
  State<FactCheckScreen> createState() => _FactCheckScreenState();
}

class _FactCheckScreenState extends State<FactCheckScreen> {
  final TextEditingController _searchController = TextEditingController();
  List<FactCheckModel> _claims = [];
  bool _isLoading = false;

  // RAG 搜尋狀態
  bool _isRagSearchResult = false;
  String? _aiSummary;

  // 快捷 Prompt 建議標籤
  final List<String> _suggestedPrompts = [
    'Celery juice for blood pressure?',
    'Mammogram false positives',
    'Vaccine side effects',
  ];

  // 分頁控制
  int _currentPage = 1;
  final int _limit = 10;
  int _totalPages = 1;
  int _totalItems = 0;

  @override
  void initState() {
    super.initState();
    _fetchFactChecks();
  }

  /// 執行搜尋 (預設列表 或 RAG 語意搜尋)
  Future<void> _fetchFactChecks({String? query, int page = 1}) async {
    setState(() => _isLoading = true);

    final String keyword = (query ?? _searchController.text).trim();

    try {
      if (keyword.isNotEmpty) {
        // RAG 語意搜尋模式
        print('[RAG Vector Search] Query: "$keyword"');

        final response = await ApiClient().dio.get(
          '/fact-checks',
          queryParameters: {'q': keyword, 'page': page, 'limit': _limit},
        );

        if (response.statusCode == 200) {
          final List rawData = response.data['data'] ?? [];
          final pagination = response.data['pagination'] ?? {};

          setState(() {
            _claims = rawData.map((e) => FactCheckModel.fromJson(e)).toList();
            _currentPage = pagination['page'] ?? page;
            _totalPages = pagination['total_pages'] ?? 1;
            _totalItems = pagination['total'] ?? _claims.length;
            _isRagSearchResult = true;
            _aiSummary =
                'Retrieved ${_claims.length} verified evidence sources for "$keyword".';
            _isLoading = false;
          });
        }
      } else {
        // 💡 預設列表模式
        print('[Fact-Check] Fetching page $page');

        final response = await ApiClient().dio.get(
          '/fact-checks',
          queryParameters: {'page': page, 'limit': _limit},
        );

        if (response.statusCode == 200) {
          final List rawData = response.data['data'] ?? [];
          final pagination = response.data['pagination'] ?? {};

          setState(() {
            _claims = rawData.map((e) => FactCheckModel.fromJson(e)).toList();
            _currentPage = pagination['page'] ?? page;
            _totalPages = pagination['total_pages'] ?? 1;
            _totalItems = pagination['total'] ?? _claims.length;
            _isRagSearchResult = false;
            _aiSummary = null;
            _isLoading = false;
          });
        }
      }
    } catch (e) {
      print('[Fact-Check Error]: $e');
      setState(() {
        _claims = [];
        _isLoading = false;
      });
    }
  }

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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8F9FA),
      appBar: AppBar(
        title: Row(
          children: const [
            Icon(Icons.psychology, size: 24),
            SizedBox(width: 8),
            Text(
              'Fact-Check Hub',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
          ],
        ),
        backgroundColor: const Color(0xFF00796B),
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: Column(
        children: [
          // 1. RAG 專屬搜尋頂欄面板
          Container(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            decoration: const BoxDecoration(
              color: Color(0xFF00796B),
              borderRadius: BorderRadius.only(
                bottomLeft: Radius.circular(24),
                bottomRight: Radius.circular(24),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 搜尋列與 RAG 按鈕
                Row(
                  children: [
                    Expanded(
                      child: Container(
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(14),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.1),
                              blurRadius: 10,
                              offset: const Offset(0, 4),
                            ),
                          ],
                        ),
                        child: TextField(
                          controller: _searchController,
                          textInputAction: TextInputAction.search,
                          style: const TextStyle(fontSize: 14),
                          decoration: InputDecoration(
                            hintText: 'Ask any medical question or myth...',
                            hintStyle: TextStyle(
                              color: Colors.grey[400],
                              fontSize: 13,
                            ),
                            prefixIcon: const Icon(
                              Icons.auto_awesome,
                              color: Color(0xFF00796B),
                              size: 20,
                            ),
                            suffixIcon: _searchController.text.isNotEmpty
                                ? IconButton(
                                    icon: const Icon(
                                      Icons.clear,
                                      color: Colors.grey,
                                      size: 18,
                                    ),
                                    onPressed: () {
                                      _searchController.clear();
                                      _fetchFactChecks(page: 1);
                                    },
                                  )
                                : null,
                            border: InputBorder.none,
                            contentPadding: const EdgeInsets.symmetric(
                              vertical: 14,
                            ),
                          ),
                          onSubmitted: (value) =>
                              _fetchFactChecks(query: value, page: 1),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),

                    // AI RAG 按鈕
                    Container(
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [Color(0xFF004D40), Color(0xFF00796B)],
                        ),
                        borderRadius: BorderRadius.circular(14),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.15),
                            blurRadius: 8,
                            offset: const Offset(0, 3),
                          ),
                        ],
                      ),
                      child: ElevatedButton.icon(
                        onPressed: () => _fetchFactChecks(
                          query: _searchController.text,
                          page: 1,
                        ),
                        icon: const Icon(
                          Icons.light,
                          size: 16,
                          color: Colors.amberAccent,
                        ),
                        label: const Text(
                          'Press',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 13,
                          ),
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.transparent,
                          shadowColor: Colors.transparent,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(
                            horizontal: 14,
                            vertical: 14,
                          ),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(14),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),

                // 快捷 Prompts Chips
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: _suggestedPrompts.map((prompt) {
                      return Padding(
                        padding: const EdgeInsets.only(right: 8.0),
                        child: InkWell(
                          onTap: () {
                            _searchController.text = prompt;
                            _fetchFactChecks(query: prompt, page: 1);
                          },
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 10,
                              vertical: 5,
                            ),
                            decoration: BoxDecoration(
                              color: Colors.white.withOpacity(0.15),
                              borderRadius: BorderRadius.circular(20),
                              border: Border.all(
                                color: Colors.white.withOpacity(0.3),
                                width: 0.8,
                              ),
                            ),
                            child: Row(
                              children: [
                                const Icon(
                                  Icons.north_west,
                                  size: 10,
                                  color: Colors.white70,
                                ),
                                const SizedBox(width: 4),
                                Text(
                                  prompt,
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontSize: 11,
                                    fontWeight: FontWeight.w500,
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
              ],
            ),
          ),

          // 2. RAG AI 語意檢索結果提醒面板
          if (_isRagSearchResult && _aiSummary != null && !_isLoading) ...[
            Container(
              margin: const EdgeInsets.fromLTRB(16, 12, 16, 4),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    Colors.teal[50]!,
                    Colors.teal[100]!.withOpacity(0.5),
                  ],
                ),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                  color: const Color(0xFF00796B).withOpacity(0.3),
                ),
              ),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: const Color(0xFF00796B),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(
                      Icons.psychology,
                      color: Colors.white,
                      size: 20,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'RAG Semantic Retrieval',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF004D40),
                            fontSize: 12,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          _aiSummary!,
                          style: TextStyle(
                            color: Colors.teal[900],
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],

          // 筆數資訊
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 6),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  _isRagSearchResult
                      ? 'Vector Matched Evidence'
                      : 'Latest Fact-Checks',
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF00796B),
                    fontSize: 14,
                  ),
                ),
                Text(
                  'Total: $_totalItems',
                  style: TextStyle(
                    color: Colors.grey[600],
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),

          // 3. 乾淨純粹的卡片列表（無來源 URL）
          Expanded(
            child: _isLoading
                ? const Center(
                    child: CircularProgressIndicator(color: Color(0xFF00796B)),
                  )
                : _claims.isEmpty
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.saved_search_rounded,
                          size: 64,
                          color: Colors.grey[300],
                        ),
                        const SizedBox(height: 12),
                        Text(
                          'No semantic matches found.',
                          style: TextStyle(
                            color: Colors.grey[500],
                            fontSize: 14,
                          ),
                        ),
                      ],
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 6,
                    ),
                    itemCount: _claims.length,
                    itemBuilder: (context, index) {
                      final item = _claims[index];
                      final themeColor = _getVerdictColor(item.verdict);

                      return Container(
                        margin: const EdgeInsets.only(bottom: 12),
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
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(16),
                          child: IntrinsicHeight(
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                // 左側彩條
                                Container(width: 5, color: themeColor),

                                // 卡片主體
                                Expanded(
                                  child: InkWell(
                                    onTap: () {
                                      Navigator.push(
                                        context,
                                        MaterialPageRoute(
                                          builder: (context) =>
                                              FactCheckDetailScreen(
                                                factCheck: item,
                                              ),
                                        ),
                                      );
                                    },
                                    child: Padding(
                                      padding: const EdgeInsets.all(14.0),
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          // 頂部列：僅保留判定標籤 (與 RAG 向量標籤)
                                          Row(
                                            mainAxisAlignment:
                                                MainAxisAlignment.spaceBetween,
                                            children: [
                                              Container(
                                                padding:
                                                    const EdgeInsets.symmetric(
                                                      horizontal: 8,
                                                      vertical: 3,
                                                    ),
                                                decoration: BoxDecoration(
                                                  color: themeColor.withOpacity(
                                                    0.15,
                                                  ),
                                                  borderRadius:
                                                      BorderRadius.circular(6),
                                                ),
                                                child: Text(
                                                  item.verdict.toUpperCase(),
                                                  style: TextStyle(
                                                    color:
                                                        themeColor ==
                                                            const Color(
                                                              0xFFFFB74D,
                                                            )
                                                        ? Colors.orange[900]
                                                        : themeColor,
                                                    fontWeight: FontWeight.w800,
                                                    fontSize: 10,
                                                  ),
                                                ),
                                              ),

                                              if (_isRagSearchResult)
                                                Container(
                                                  padding:
                                                      const EdgeInsets.symmetric(
                                                        horizontal: 8,
                                                        vertical: 3,
                                                      ),
                                                  decoration: BoxDecoration(
                                                    color: Colors.teal[50],
                                                    borderRadius:
                                                        BorderRadius.circular(
                                                          10,
                                                        ),
                                                    border: Border.all(
                                                      color: const Color(
                                                        0xFF00796B,
                                                      ).withOpacity(0.3),
                                                    ),
                                                  ),
                                                  child: Row(
                                                    children: const [
                                                      Icon(
                                                        Icons.bolt,
                                                        size: 12,
                                                        color: Color(
                                                          0xFF00796B,
                                                        ),
                                                      ),
                                                      SizedBox(width: 2),
                                                      Text(
                                                        'Semantic Match',
                                                        style: TextStyle(
                                                          fontSize: 10,
                                                          fontWeight:
                                                              FontWeight.bold,
                                                          color: Color(
                                                            0xFF004D40,
                                                          ),
                                                        ),
                                                      ),
                                                    ],
                                                  ),
                                                ),
                                            ],
                                          ),
                                          const SizedBox(height: 10),

                                          // 宣稱內容 (Claim)
                                          Text(
                                            item.claim,
                                            style: const TextStyle(
                                              fontWeight: FontWeight.bold,
                                              fontSize: 15,
                                              height: 1.3,
                                              color: Colors.black87,
                                            ),
                                          ),

                                          // 摘要內文 (Summary)
                                          if (item.summary.isNotEmpty) ...[
                                            const SizedBox(height: 6),
                                            Text(
                                              item.summary,
                                              maxLines: 2,
                                              overflow: TextOverflow.ellipsis,
                                              style: TextStyle(
                                                color: Colors.grey[600],
                                                fontSize: 12,
                                                height: 1.4,
                                              ),
                                            ),
                                          ],
                                        ],
                                      ),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      );
                    },
                  ),
          ),

          // 4. 底部分頁控制
          if (_totalPages > 1)
            Container(
              padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
              decoration: BoxDecoration(
                color: Colors.white,
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.05),
                    blurRadius: 6,
                    offset: const Offset(0, -2),
                  ),
                ],
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  IconButton(
                    icon: const Icon(Icons.arrow_back_ios, size: 15),
                    onPressed: _currentPage > 1
                        ? () => _fetchFactChecks(page: _currentPage - 1)
                        : null,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'Page $_currentPage of $_totalPages',
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 12,
                      color: Colors.black87,
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    icon: const Icon(Icons.arrow_forward_ios, size: 15),
                    onPressed: _currentPage < _totalPages
                        ? () => _fetchFactChecks(page: _currentPage + 1)
                        : null,
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}
