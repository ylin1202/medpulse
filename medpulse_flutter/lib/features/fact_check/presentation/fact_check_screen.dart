import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/widgets/pagination_bar.dart';
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
    'Vitamin D prevents cold?',
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
    _fetchFactChecks(); // 預設進來撈取一般清單
  }

  /// 1. 預設模式：一般 SQL / API 搜尋 (GET /fact-checks)
  Future<void> _fetchFactChecks({String? query, int page = 1}) async {
    setState(() => _isLoading = true);

    final String keyword = (query ?? _searchController.text).trim();

    try {
      debugPrint('[Fact-Check Normal Search] Fetching page $page, keyword: "$keyword"');

      final response = await ApiClient().dio.get(
        '/fact-checks',
        queryParameters: {
          if (keyword.isNotEmpty) 'q': keyword,
          'page': page,
          'limit': _limit,
        },
      );

      if (response.statusCode == 200 && mounted) {
        final List rawData = response.data['data'] ?? [];
        final pagination = response.data['pagination'] ?? {};

        setState(() {
          _claims = rawData.map((e) => FactCheckModel.fromJson(e)).toList();
          _currentPage = pagination['page'] ?? page;
          _totalPages = pagination['total_pages'] ?? 1;
          _totalItems = pagination['total'] ?? _claims.length;
          _isRagSearchResult = false; // 標示為一般結果
          _aiSummary = null;
          _isLoading = false;
        });
      }
    } catch (e) {
      debugPrint('[Fact-Check Normal Error]: $e');
      if (mounted) {
        setState(() {
          _claims = [];
          _isLoading = false;
        });
      }
    }
  }

  /// 2. RAG 專屬模式：觸發 AI 語意向量檢索 (POST /api/v1/factcheck)
  Future<void> _triggerRagSearch({String? query}) async {
    final String keyword = (query ?? _searchController.text).trim();

    if (keyword.isEmpty) {
      _fetchFactChecks(page: 1); // 空字串切回預設列表
      return;
    }

    setState(() => _isLoading = true);

    try {
      debugPrint('[RAG Vector Search] Querying FastAPI for: "$keyword"');

      final fastapiDio = Dio(
        BaseOptions(
          baseUrl: '',
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 10),
          headers: {'Content-Type': 'application/json'},
        ),
      );

      final response = await fastapiDio.post(
        '/api/v1/factcheck',
        data: {'query': keyword},
      );

      if (response.statusCode == 200 && mounted) {
        final List rawData = response.data['data'] ?? [];

        setState(() {
          _claims = rawData.map((e) => FactCheckModel.fromJson(e)).toList();
          _currentPage = 1;
          _totalPages = 1;
          _totalItems = _claims.length;
          _isRagSearchResult = true;

          if (_claims.isNotEmpty && _claims.first.score != null) {
            final scorePercent =
                (_claims.first.score! * 100).toStringAsFixed(1);
            _aiSummary =
                'Matched verified evidence with $scorePercent% confidence.';
          } else if (_claims.isNotEmpty) {
            _aiSummary =
                'Retrieved ${_claims.length} vector-matched evidence sources.';
          } else {
            _aiSummary =
                'No relevant medical fact-check found for "$keyword".';
          }

          _isLoading = false;
        });
      }
    } catch (e) {
      debugPrint('[RAG Vector Search Error]: $e');
      if (mounted) {
        setState(() {
          _claims = [];
          _isLoading = false;
        });
      }
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

                    // AI RAG 按鈕 (改為 AI Search，專業度更高)
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
                        onPressed: () => _triggerRagSearch(),
                        icon: const Icon(
                          Icons.lightbulb_outline,
                          size: 16,
                          color: Colors.amberAccent,
                        ),
                        label: const Text(
                          'AI Search',
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
                            _triggerRagSearch(query: prompt);
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
                                  Icons.search,
                                  size: 11,
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
              ],
            ),
          ),

          // 3. 卡片列表
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
                          'No matched evidence found.',
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
                                Container(width: 5, color: themeColor),
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
                                          Text(
                                            item.claim,
                                            style: const TextStyle(
                                              fontWeight: FontWeight.bold,
                                              fontSize: 15,
                                              height: 1.3,
                                              color: Colors.black87,
                                            ),
                                          ),
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

          // 4. 底部分頁控制 (通用元件)
          if (!_isRagSearchResult)
            PaginationBar(
              currentPage: _currentPage,
              totalPages: _totalPages,
              onPageChanged: (newPage) => _fetchFactChecks(page: newPage),
            ),
        ],
      ),
    );
  }
}