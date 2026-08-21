from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.models.favorite import FavoriteModel

favorite_bp = Blueprint("favorite", __name__, url_prefix="/api/v1/favorites")


class FavoriteController:
    """Controller handling user medication bookmarks, favorites management, and status checks."""

    @staticmethod
    @jwt_required()
    def add_favorite():
        """
        Add a medication to the authenticated user's favorites.
        Route: POST /api/v1/favorites
        """
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
        """
        Remove a medication from the authenticated user's favorites.
        Route: DELETE /api/v1/favorites/<drug_id>
        """
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
        """
        Check if a specific medication is favorited by the authenticated user.
        Route: GET /api/v1/favorites/check/<drug_id>
        """
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
        """
        Retrieve all favorited medications for the authenticated user.
        Route: GET /api/v1/favorites
        """
        try:
            current_user_id = int(get_jwt_identity())
            favorites = FavoriteModel.get_user_favorites(current_user_id)
            return jsonify({
                "status": "success",
                "favorites": favorites
            }), 200

        except Exception as e:
            return jsonify({"error": f"Failed to fetch favorites: {str(e)}"}), 500


# RESTful Route Bindings
favorite_bp.route("", methods=["POST"])(FavoriteController.add_favorite)
favorite_bp.route("/<int:drug_id>", methods=["DELETE"])(FavoriteController.remove_favorite)
favorite_bp.route("/check/<int:drug_id>", methods=["GET"])(FavoriteController.check_favorite)
favorite_bp.route("", methods=["GET"])(FavoriteController.get_favorites)