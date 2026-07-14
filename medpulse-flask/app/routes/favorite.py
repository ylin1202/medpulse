from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.favorite import FavoriteModel

favorite_bp = Blueprint("favorite", __name__, url_prefix="/api/v1/favorites")

class FavoriteController:
    """封裝使用者收藏夾 API 邏輯的 Class"""

    @staticmethod
    @jwt_required()
    def add_favorite():
        """新增收藏 (POST /api/v1/favorites)"""
        try:
            current_user_id = int(get_jwt_identity())
            data = request.get_json() or {}
            item_type = data.get("item_type")  # 'drug' 或 'fact_check'
            item_id = data.get("item_id")

            if not item_type or not item_id:
                return jsonify({"error": "Missing item_type or item_id"}), 400

            if item_type not in ["drug", "fact_check"]:
                return jsonify({"error": "Invalid item_type. Must be 'drug' or 'fact_check'"}), 400

            res = FavoriteModel.add_favorite(current_user_id, item_type, item_id)
            return jsonify({
                "status": "success",
                "message": f"Successfully added {item_type} to favorites",
                "data": res
            }), 201

        except Exception as e:
            return jsonify({"error": f"Failed to add favorite: {str(e)}"}), 500

    @staticmethod
    @jwt_required()
    def remove_favorite():
        """取消收藏 (DELETE /api/v1/favorites)"""
        try:
            current_user_id = int(get_jwt_identity())
            data = request.get_json() or {}
            item_type = data.get("item_type")
            item_id = data.get("item_id")

            if not item_type or not item_id:
                return jsonify({"error": "Missing item_type or item_id"}), 400

            FavoriteModel.remove_favorite(current_user_id, item_type, item_id)
            return jsonify({
                "status": "success",
                "message": f"Successfully removed {item_type} from favorites"
            }), 200

        except Exception as e:
            return jsonify({"error": f"Failed to remove favorite: {str(e)}"}), 500

    @staticmethod
    @jwt_required()
    def get_favorites():
        """取得個人收藏清單 (GET /api/v1/favorites?type=drug)"""
        try:
            current_user_id = int(get_jwt_identity())
            item_type = request.args.get("type", "").strip() or None

            favorites = FavoriteModel.get_user_favorites(current_user_id, item_type=item_type)
            return jsonify({
                "status": "success",
                "data": favorites
            }), 200

        except Exception as e:
            return jsonify({"error": f"Failed to fetch favorites: {str(e)}"}), 500


# 綁定路由點
favorite_bp.route("", methods=["POST"])(FavoriteController.add_favorite)
favorite_bp.route("", methods=["DELETE"])(FavoriteController.remove_favorite)
favorite_bp.route("", methods=["GET"])(FavoriteController.get_favorites)