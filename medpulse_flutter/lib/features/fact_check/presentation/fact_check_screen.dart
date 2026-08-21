import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
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

  // Suggested prompt query chips for quick evaluation
  final List<String> _suggestedPrompts = [
    'Vitamin D prevents cold?',
    'Mammogram false positives',
    'Can lemons cure cancer?',
  ];

  // Pagination state controllers
  int _currentPage = 1;
  final int _limit = 10;
  int _totalPages = 1;
  int _totalItems = 0;

  @override
  void initState() {
    super.initState();
    _fetchFactChecks();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  /// 1. Default mode: Standard relational keyword search (GET /api/v1/fact-checks).
  Future<void> _fetchFactChecks({String? query, int page = 1}) async {
    setState(() => _isLoading = true);

    final String keyword = (query ?? _searchController.text).trim();

    try {
      debugPrint(
        '[Fact-Check Search] Querying page $page with keyword: "$keyword"',
      );

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
          _isLoading = false;
        });
      }
    } catch (e) {
      debugPrint('[Fact-Check Search Error]: $e');
      if (mounted) {
        setState(() {
          _claims = [];
          _isLoading = false;
        });
      }
    }
  }

  /// 2. Semantic RAG mode: Dense vector retrieval + Gemini synthesis via FastAPI.
  Future<void> _triggerRagSearch({String? query}) async {
    final String keyword = (query ?? _searchController.text).trim();

    if (keyword.isEmpty) {
      _fetchFactChecks(page: 1);
      return;
    }

    // Present non-dismissible loading modal during inference
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (BuildContext dialogContext) {
        return PopScope(
          canPop: false,
          child: Dialog(
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(20),
            ),
            backgroundColor: Colors.white,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 32, horizontal: 24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const SizedBox(
                    width: 48,
                    height: 48,
                    child: CircularProgressIndicator(
                      strokeWidth: 3.5,
                      valueColor: AlwaysStoppedAnimation<Color>(
                        Color(0xFF00796B),
                      ),
                    ),
                  ),
                  const SizedBox(height: 22),
                  const Text(
                    'Analyzing with AI...',
                    style: TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF004D40),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Retrieving PUBHEALTH evidence & synthesizing verdict...',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 13,
                      color: Colors.grey[600],
                      height: 1.4,
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );

    try {
      debugPrint('[RAG Vector Search] Sending query to AI service: "$keyword"');

      final response = await ApiClient().fastApiDio.post(
        '/api/v1/factcheck',
        data: {'query': keyword},
      );

      // Dismiss inference dialog
      if (mounted) {
        Navigator.of(context, rootNavigator: true).pop();
      }

      if (response.statusCode == 200 && mounted) {
        final List rawData = response.data['data'] ?? [];

        if (rawData.isNotEmpty) {
          final factItem = FactCheckModel.fromJson(rawData.first);
          _showRagResultDialog(factItem);
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('No authoritative fact-check found for "$keyword".'),
              backgroundColor: Colors.blueGrey,
            ),
          );
        }
      }
    } catch (e) {
      debugPrint('[RAG Vector Search Error]: $e');
      if (mounted) {
        Navigator.of(context, rootNavigator: true).pop();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('AI verification failed: $e'),
            backgroundColor: Colors.redAccent,
          ),
        );
      }
    }
  }

  /// Present synthesized RAG verification results in a modal dialog.
  void _showRagResultDialog(FactCheckModel item) {
    final themeColor = _getVerdictColor(item.verdict);
    final scorePercent = item.score != null
        ? (item.score! * 100).toStringAsFixed(1)
        : null;

    final String explanationText = item.explanation.isNotEmpty
        ? item.explanation
        : item.summary;

    showDialog(
      context: context,
      builder: (ctx) => Dialog(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
        child: Container(
          constraints: const BoxConstraints(maxWidth: 480),
          padding: const EdgeInsets.all(20),
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header row: Verdict badge, similarity score, and close action
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 10,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color: themeColor.withOpacity(0.15),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text(
                            item.verdict.toUpperCase(),
                            style: TextStyle(
                              color: themeColor == const Color(0xFFFFB74D)
                                  ? Colors.orange[900]
                                  : themeColor,
                              fontWeight: FontWeight.w800,
                              fontSize: 12,
                            ),
                          ),
                        ),
                        if (scorePercent != null) ...[
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: Colors.teal[50],
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Text(
                              '$scorePercent% Match',
                              style: const TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                                color: Color(0xFF00796B),
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                    IconButton(
                      icon: const Icon(Icons.close, color: Colors.grey),
                      onPressed: () => Navigator.of(ctx).pop(),
                    ),
                  ],
                ),
                const SizedBox(height: 12),

                // Claim title (Markdown formatted)
                MarkdownBody(
                  data: item.claim,
                  selectable: true,
                  styleSheet: MarkdownStyleSheet(
                    p: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      height: 1.35,
                      color: Colors.black87,
                    ),
                    strong: const TextStyle(
                      fontWeight: FontWeight.w900,
                      color: Colors.black,
                    ),
                  ),
                ),
                const Divider(height: 24),

                // AI synthesis title
                Row(
                  children: const [
                    Icon(
                      Icons.auto_awesome,
                      color: Color(0xFF00796B),
                      size: 16,
                    ),
                    SizedBox(width: 6),
                    Text(
                      'AI Fact-Check Synthesis',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF004D40),
                        fontSize: 13,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),

                // Synthesized explanation body (Markdown formatted)
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF4F9F8),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Colors.teal.shade100),
                  ),
                  child: MarkdownBody(
                    data: explanationText,
                    selectable: true,
                    styleSheet: MarkdownStyleSheet(
                      p: const TextStyle(
                        fontSize: 14,
                        height: 1.55,
                        color: Colors.black87,
                      ),
                      strong: const TextStyle(
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF004D40),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 20),

                // Action buttons
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        style: OutlinedButton.styleFrom(
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10),
                          ),
                          padding: const EdgeInsets.symmetric(vertical: 12),
                        ),
                        onPressed: () => Navigator.of(ctx).pop(),
                        child: const Text('Close'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF00796B),
                          foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10),
                          ),
                          padding: const EdgeInsets.symmetric(vertical: 12),
                        ),
                        onPressed: () {
                          Navigator.of(ctx).pop();
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => FactCheckDetailScreen(
                                factCheck: item,
                                aiSummary: item.explanation,
                              ),
                            ),
                          );
                        },
                        child: const Text('View Source'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Color _getVerdictColor(String verdict) {
    final v = verdict.toLowerCase();
    if (v.contains('false') || v.contains('untrue') || v.contains('misleading')) {
      return const Color(0xFFE57373);
    } else if (v.contains('true') || v.contains('correct') || v.contains('verified')) {
      return const Color(0xFF81C784);
    } else if (v.contains('mix') || v.contains('partial') || v.contains('unproven')) {
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
          // 1. RAG Search & Prompt Panel
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
                              Icons.search,
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

                    // AI Fact-Check Action Button
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
                          Icons.auto_awesome,
                          size: 16,
                          color: Colors.amberAccent,
                        ),
                        label: const Text(
                          'AI Fact-Check',
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

                // Quick Prompt Chips
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
                                  Icons.lightbulb_outline,
                                  size: 11,
                                  color: Colors.amberAccent,
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

          // 2. Archived claims list view
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
                          'No fact-checks available.',
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
                                          // Verdict badge and source label
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
                                              const SizedBox(width: 12),
                                              Expanded(
                                                child: Text(
                                                  item.source,
                                                  textAlign: TextAlign.end,
                                                  maxLines: 1,
                                                  overflow:
                                                      TextOverflow.ellipsis,
                                                  style: TextStyle(
                                                    fontSize: 11,
                                                    color: Colors.grey[500],
                                                  ),
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

          // 3. Bottom pagination controls
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