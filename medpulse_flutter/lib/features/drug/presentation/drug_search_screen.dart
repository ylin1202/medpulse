import 'package:flutter/material.dart';
import '../../../../core/auth/auth_service.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/widgets/pagination_bar.dart'; 
import '../../favorite/presentation/favorite_button.dart'; 
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
  
  // Pagination state controllers
  int _currentPage = 1;
  final int _limit = 10;
  int _totalPages = 1;
  int _totalItems = 0;

  @override
  void initState() {
    super.initState();
    _fetchDrugs();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  /// Query Flask API for paginated drug catalog items (GET /api/v1/drugs).
  Future<void> _fetchDrugs({String? query, int page = 1}) async {
    if (!mounted) return;

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

      final response = await ApiClient().dio.get(
        '/drugs',
        queryParameters: queryParams,
      );

      if (response.statusCode == 200 && mounted) {
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
      debugPrint('[Drug Finder Error]: $e');
      if (mounted) {
        setState(() {
          _searchResults = [];
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8F9FA),
      appBar: AppBar(
        title: const Text(
          'Drug Finder',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: const Color(0xFF00796B),
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: Column(
        children: [
          // 1. Integrated top search panel
          Container(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: const BorderRadius.only(
                bottomLeft: Radius.circular(20),
                bottomRight: Radius.circular(20),
              ),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.04),
                  blurRadius: 10,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Column(
              children: [
                // Search input card container
                Container(
                  decoration: BoxDecoration(
                    color: const Color(0xFFF8F9FA),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: Colors.teal.shade100, width: 1),
                  ),
                  child: Row(
                    children: [
                      const SizedBox(width: 12),
                      const Icon(Icons.search, color: Color(0xFF00796B), size: 22),
                      const SizedBox(width: 8),
                      Expanded(
                        child: TextField(
                          controller: _searchController,
                          textInputAction: TextInputAction.search,
                          style: const TextStyle(fontSize: 14),
                          decoration: InputDecoration(
                            hintText: 'Search drug name (e.g. minoxidil)...',
                            hintStyle: TextStyle(
                              color: Colors.grey[400],
                              fontSize: 13,
                            ),
                            border: InputBorder.none,
                            isDense: true,
                            contentPadding: const EdgeInsets.symmetric(vertical: 12),
                            suffixIcon: _searchController.text.isNotEmpty
                                ? IconButton(
                                    icon: const Icon(Icons.clear, color: Colors.grey, size: 18),
                                    onPressed: () {
                                      _searchController.clear();
                                      _fetchDrugs(query: '', page: 1);
                                    },
                                  )
                                : null,
                          ),
                          onSubmitted: (value) => _fetchDrugs(query: value, page: 1),
                        ),
                      ),
                      
                      // Embedded search submit button
                      Padding(
                        padding: const EdgeInsets.all(4.0),
                        child: Material(
                          color: const Color(0xFF00796B),
                          borderRadius: BorderRadius.circular(10),
                          child: InkWell(
                            borderRadius: BorderRadius.circular(10),
                            onTap: () => _fetchDrugs(query: _searchController.text, page: 1),
                            child: const Padding(
                              padding: EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                              child: Text(
                                'Search',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 13,
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // Total metrics count header
          if (!_isLoading && _searchResults.isNotEmpty)
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 14, 20, 8),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: const [
                      Icon(Icons.format_list_bulleted, size: 16, color: Color(0xFF00796B)),
                      SizedBox(width: 6),
                      Text(
                        'Medication Results',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF004D40),
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                  Text(
                    'Total $_totalItems items',
                    style: TextStyle(
                      color: Colors.grey[600],
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),

          // 2. Paginated medication results list view
          Expanded(
            child: ValueListenableBuilder<bool>(
              valueListenable: AuthService.authState,
              builder: (context, isLoggedIn, child) {
                if (_isLoading) {
                  return const Center(
                    child: CircularProgressIndicator(color: Color(0xFF00796B)),
                  );
                }

                if (_searchResults.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.medication_outlined, size: 60, color: Colors.grey[300]),
                        const SizedBox(height: 12),
                        Text(
                          'No drugs matched your query.',
                          style: TextStyle(fontSize: 14, color: Colors.grey[500]),
                        ),
                      ],
                    ),
                  );
                }

                return ListView.builder(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                  itemCount: _searchResults.length,
                  itemBuilder: (context, index) {
                    final drug = _searchResults[index];
                    final int drugId = int.tryParse(drug.id) ?? 0;

                    return Container(
                      margin: const EdgeInsets.only(bottom: 10),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(
                          color: Colors.teal.shade50,
                          width: 1.2,
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.02),
                            blurRadius: 6,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      child: Material(
                        color: Colors.transparent,
                        borderRadius: BorderRadius.circular(14),
                        child: InkWell(
                          borderRadius: BorderRadius.circular(14),
                          onTap: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (context) => DrugDetailScreen(drug: drug),
                              ),
                            ).then((_) {
                              if (mounted) setState(() {});
                            });
                          },
                          child: Padding(
                            padding: const EdgeInsets.all(14.0),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                // Leading medication icon badge
                                Container(
                                  padding: const EdgeInsets.all(10),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFF00796B).withOpacity(0.08),
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: const Icon(
                                    Icons.health_and_safety_outlined,
                                    color: Color(0xFF00796B),
                                    size: 22,
                                  ),
                                ),
                                const SizedBox(width: 12),

                                // Central medication details
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        drug.brandName,
                                        style: const TextStyle(
                                          fontWeight: FontWeight.bold,
                                          fontSize: 15,
                                          color: Colors.black87,
                                          height: 1.25,
                                        ),
                                      ),
                                      const SizedBox(height: 6),

                                      // Generic name chip badge
                                      Container(
                                        padding: const EdgeInsets.symmetric(
                                          horizontal: 8,
                                          vertical: 3,
                                        ),
                                        decoration: BoxDecoration(
                                          color: Colors.teal.shade50,
                                          borderRadius: BorderRadius.circular(6),
                                        ),
                                        child: Text(
                                          'Generic: ${drug.genericName}',
                                          style: const TextStyle(
                                            color: Color(0xFF00695C),
                                            fontSize: 11,
                                            fontWeight: FontWeight.w600,
                                          ),
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                      const SizedBox(height: 4),

                                      // Pharmaceutical manufacturer label
                                      Text(
                                        'Mfr: ${drug.manufacturer}',
                                        style: TextStyle(
                                          color: Colors.grey[500],
                                          fontSize: 11,
                                        ),
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ],
                                  ),
                                ),

                                // Trailing actions: Favorite bookmark button and navigation arrow
                                Column(
                                  children: [
                                    FavoriteButton(
                                      key: ValueKey('fav_${drugId}_$isLoggedIn'),
                                      drugId: drugId,
                                    ),
                                    const SizedBox(height: 8),
                                    const Icon(
                                      Icons.arrow_forward_ios,
                                      size: 12,
                                      color: Colors.grey,
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    );
                  },
                );
              },
            ),
          ),

          // 3. Shared pagination controller bar
          if (!_isLoading && _searchResults.isNotEmpty)
            PaginationBar(
              currentPage: _currentPage,
              totalPages: _totalPages,
              onPageChanged: (newPage) => _fetchDrugs(page: newPage),
            ),
        ],
      ),
    );
  }
}