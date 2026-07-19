from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.favorite import FavoriteModel

favorite_bp = Blueprint("favorite", __name__, url_prefix="/api/v1/favorites")

class FavoriteController:
    """使用者藥品收藏夾 API Controller"""

    @staticmethod
    @jwt_required()
    def add_favorite():
        """新增藥品收藏 (POST /api/v1/favorites)"""
        try:
            current_user_id = int(get_jwt_identity())
            data = request.get_json() or {}
            drug_id = data.get("drug_id")

            if not drug_id:
                return jsonify({"error": "Missing drug_id"}), 400

            res = FavoriteModel.add_favorite(current_user_id, drug_id)
            return jsonify({
                "status": "success",
                "message": "Drug added to favorites",
                "data": res
            }), 201

        except Exception as e:
            return jsonify({"error": f"Failed to add favorite: {str(e)}"}), 500

    @staticmethod
    @jwt_required()
    def remove_favorite(drug_id):
        """取消藥品收藏 (DELETE /api/v1/favorites/<drug_id>)"""
        try:
            current_user_id = int(get_jwt_identity())
            FavoriteModel.remove_favorite(current_user_id, drug_id)
            return jsonify({
                "status": "success",
                "message": f"Successfully removed drug {drug_id} from favorites"
            }), 200

        except Exception as e:
            return jsonify({"error": f"Failed to remove favorite: {str(e)}"}), 500

    @staticmethod
    @jwt_required()
    def check_favorite(drug_id):
        """檢查藥品是否已被收藏 (GET /api/v1/favorites/check/<drug_id>)"""
        try:
            current_user_id = int(get_jwt_identity())
            is_fav = FavoriteModel.is_favorited(current_user_id, drug_id)
            return jsonify({
                "is_favorited": is_fav
            }), 200
        except Exception as e:
            return jsonify({"error": f"Failed to check status: {str(e)}"}), 500

    @staticmethod
    @jwt_required()
    def get_favorites():
        """取得使用者的所有收藏藥品列表 (GET /api/v1/favorites)"""
        try:
            current_user_id = int(get_jwt_identity())
            favorites = FavoriteModel.get_user_favorites(current_user_id)
            return jsonify({
                "status": "success",
                "favorites": favorites
            }), 200

        except Exception as e:
            return jsonify({"error": f"Failed to fetch favorites: {str(e)}"}), 500


# RESTful 路由映射
favorite_bp.route("", methods=["POST"])(FavoriteController.add_favorite)
favorite_bp.route("/<int:drug_id>", methods=["DELETE"])(FavoriteController.remove_favorite)
favorite_bp.route("/check/<int:drug_id>", methods=["GET"])(FavoriteController.check_favorite)
favorite_bp.route("", methods=["GET"])(FavoriteController.get_favorites)