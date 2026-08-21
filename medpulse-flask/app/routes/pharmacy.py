from flask import Blueprint, jsonify, request

from app.models.pharmacy import PharmacyModel
from app.utils.cache import CacheService

pharmacy_bp = Blueprint("pharmacy", __name__, url_prefix="/api/v1/pharmacies")


class PharmacyController:
    """Controller handling pharmacy geolocation lookups, filtering, and Redis caching."""

    @staticmethod
    def get_pharmacies():
        """
        Retrieve pharmacy listings with optional keyword and regional filtering.
        Route: GET /api/v1/pharmacies?q=name&city=city_name
        """
        try:
            keyword = request.args.get("q", "").strip() or None
            city = request.args.get("city", "").strip() or None

            # Build deterministic cache key (normalize None values to 'all')
            cache_key = f"cache:pharmacies:q:{keyword or 'all'}:city:{city or 'all'}"

            # Check cache hit
            cached_data = CacheService.get(cache_key)
            if cached_data:
                return jsonify({
                    "status": "success",
                    "source": "cache",
                    "count": len(cached_data),
                    "data": cached_data
                }), 200

            # Cache miss: query PostgreSQL via Data Access Object
            pharmacies = PharmacyModel.get_all(keyword=keyword, city=city)

            # Populate Redis cache with a 10-minute TTL (600 seconds)
            CacheService.set(cache_key, pharmacies, expire=600)

            return jsonify({
                "status": "success",
                "source": "database",
                "count": len(pharmacies),
                "data": pharmacies
            }), 200

        except Exception as e:
            return jsonify({"error": f"Failed to fetch pharmacies: {str(e)}"}), 500


# Endpoint Route Bindings
pharmacy_bp.route("", methods=["GET"])(PharmacyController.get_pharmacies)