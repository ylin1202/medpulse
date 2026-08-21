import 'package:flutter/material.dart';
import '../../drug/data/drug_model.dart';
import '../../drug/presentation/drug_detail_screen.dart';
import '../data/favorite_service.dart';

class FavoriteScreen extends StatefulWidget {
  const FavoriteScreen({super.key});

  @override
  State<FavoriteScreen> createState() => _FavoriteScreenState();
}

class _FavoriteScreenState extends State<FavoriteScreen> {
  List<dynamic> _favorites = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadFavorites();
  }

  /// Retrieve bookmarked medications from the backend service.
  Future<void> _loadFavorites() async {
    if (!mounted) return;
    setState(() => _isLoading = true);
    final data = await FavoriteService().getFavorites();
    if (mounted) {
      setState(() {
        _favorites = data;
        _isLoading = false;
      });
    }
  }

  /// Remove a medication bookmark and update the local list state.
  Future<void> _removeFavorite(int drugId, int index) async {
    final success = await FavoriteService().removeFavorite(drugId);
    if (success && mounted) {
      setState(() {
        _favorites.removeAt(index);
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Removed medication from saved list.')),
      );
    }
  }

  /// Map dynamic API JSON payloads into a strongly-typed DrugModel.
  DrugModel _mapToDrugModel(Map<String, dynamic> item) {
    return DrugModel.fromJson({
      'id': item['drug_id'] ?? item['id'],
      'brand_name': item['brand_name'],
      'generic_name': item['generic_name'],
      'manufacturer_name': item['manufacturer_name'],
      'purpose': item['purpose'],
      'indications_and_usage': item['indications_and_usage'],
      'warnings': item['warnings'],
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Saved Medications',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: const Color(0xFF00796B),
        foregroundColor: Colors.white,
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: Color(0xFF00796B)),
            )
          : _favorites.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.medication_outlined,
                        size: 64,
                        color: Colors.grey[400],
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'No saved medications yet.',
                        style: TextStyle(
                          fontSize: 16,
                          color: Colors.grey[600],
                        ),
                      ),
                    ],
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _loadFavorites,
                  color: const Color(0xFF00796B),
                  child: ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: _favorites.length,
                    itemBuilder: (context, index) {
                      final item = _favorites[index] as Map<String, dynamic>;

                      // Safe parsing of drug identifier
                      final drugId = item['drug_id'] is int
                          ? item['drug_id'] as int
                          : int.tryParse(item['drug_id'].toString()) ?? 0;

                      final brandName = item['brand_name'] ?? 'Unknown Drug';
                      final genericName = item['generic_name'] ?? '';
                      final purpose =
                          item['purpose'] ?? item['manufacturer_name'] ?? '';

                      return Card(
                        margin: const EdgeInsets.only(bottom: 12),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: ListTile(
                          contentPadding: const EdgeInsets.symmetric(
                            horizontal: 16,
                            vertical: 8,
                          ),
                          leading: const CircleAvatar(
                            backgroundColor: Color(0xFFE0F2F1),
                            child: Icon(
                              Icons.medication_outlined,
                              color: Color(0xFF00796B),
                            ),
                          ),
                          title: Text(
                            brandName,
                            style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 16,
                            ),
                          ),
                          subtitle: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              if (genericName.isNotEmpty) ...[
                                const SizedBox(height: 4),
                                Text(
                                  genericName,
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w500,
                                    color: Color(0xFF004D40),
                                  ),
                                ),
                              ],
                              if (purpose.isNotEmpty) ...[
                                const SizedBox(height: 2),
                                Text(
                                  purpose,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(
                                    color: Colors.grey[600],
                                    fontSize: 12,
                                  ),
                                ),
                              ],
                            ],
                          ),
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              IconButton(
                                icon: const Icon(
                                  Icons.delete_outline,
                                  color: Colors.red,
                                ),
                                onPressed: () => _removeFavorite(drugId, index),
                              ),
                              const Icon(
                                Icons.chevron_right,
                                color: Colors.grey,
                              ),
                            ],
                          ),
                          // Navigate to DrugDetailScreen and refresh on return
                          onTap: () {
                            final drugModel = _mapToDrugModel(item);
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (context) =>
                                    DrugDetailScreen(drug: drugModel),
                              ),
                            ).then((_) {
                              // Resync saved list to reflect changes from detail screen
                              _loadFavorites();
                            });
                          },
                        ),
                      );
                    },
                  ),
                ),
    );
  }
}