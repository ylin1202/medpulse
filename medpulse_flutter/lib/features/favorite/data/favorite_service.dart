import 'package:flutter/foundation.dart';
import '../../../core/network/api_client.dart';

class FavoriteService {
  static final FavoriteService _instance = FavoriteService._internal();
  factory FavoriteService() => _instance;
  FavoriteService._internal();

  /// 1. 取得收藏的藥品清單 (GET /api/v1/favorites)
  Future<List<dynamic>> getFavorites() async {
    try {
      final response = await ApiClient().flaskDio.get('/favorites');
      if (response.statusCode == 200) {
        return response.data['favorites'] ?? [];
      }
      return [];
    } catch (e) {
      debugPrint('Failed to fetch favorites: $e');
      return [];
    }
  }

  /// 2. 新增藥品收藏 (POST /api/v1/favorites)
  Future<bool> addFavorite(int drugId) async {
    try {
      final response = await ApiClient().flaskDio.post(
        '/favorites',
        data: {'drug_id': drugId},
      );
      return response.statusCode == 201 || response.statusCode == 200;
    } catch (e) {
      debugPrint('Failed to add favorite: $e');
      return false;
    }
  }

  /// 3. 取消藥品收藏 (DELETE /api/v1/favorites/:drugId)
  Future<bool> removeFavorite(int drugId) async {
    try {
      final response = await ApiClient().flaskDio.delete('/favorites/$drugId');
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('Failed to remove favorite: $e');
      return false;
    }
  }

  /// 4. 檢查藥品是否已被收藏 (GET /api/v1/favorites/check/:drugId)
  Future<bool> isFavorited(int drugId) async {
    try {
      final response = await ApiClient().flaskDio.get('/favorites/check/$drugId');
      if (response.statusCode == 200) {
        return response.data['is_favorited'] ?? false;
      }
      return false;
    } catch (e) {
      return false;
    }
  }
}