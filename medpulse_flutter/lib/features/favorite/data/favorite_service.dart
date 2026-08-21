import 'package:flutter/foundation.dart';
import '../../../core/network/api_client.dart';

class FavoriteService {
  static final FavoriteService _instance = FavoriteService._internal();
  factory FavoriteService() => _instance;
  FavoriteService._internal();

  /// 1. Retrieve bookmarked drug catalog items (GET /api/v1/favorites).
  Future<List<dynamic>> getFavorites() async {
    try {
      final response = await ApiClient().flaskDio.get('/favorites');
      if (response.statusCode == 200) {
        return response.data['favorites'] ?? [];
      }
      return [];
    } catch (e) {
      debugPrint('[FavoriteService] Failed to fetch favorites: $e');
      return [];
    }
  }

  /// 2. Add drug to user bookmarks (POST /api/v1/favorites).
  Future<bool> addFavorite(int drugId) async {
    try {
      final response = await ApiClient().flaskDio.post(
        '/favorites',
        data: {'drug_id': drugId},
      );
      return response.statusCode == 201 || response.statusCode == 200;
    } catch (e) {
      debugPrint('[FavoriteService] Failed to add favorite: $e');
      return false;
    }
  }

  /// 3. Remove drug from user bookmarks (DELETE /api/v1/favorites/:drugId).
  Future<bool> removeFavorite(int drugId) async {
    try {
      final response = await ApiClient().flaskDio.delete('/favorites/$drugId');
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('[FavoriteService] Failed to remove favorite: $e');
      return false;
    }
  }

  /// 4. Verify whether a drug is bookmarked by the authenticated user (GET /api/v1/favorites/check/:drugId).
  Future<bool> isFavorited(int drugId) async {
    try {
      final response = await ApiClient().flaskDio.get('/favorites/check/$drugId');
      if (response.statusCode == 200) {
        return response.data['is_favorited'] ?? false;
      }
      return false;
    } catch (e) {
      debugPrint('[FavoriteService] Failed to check favorite status: $e');
      return false;
    }
  }
}