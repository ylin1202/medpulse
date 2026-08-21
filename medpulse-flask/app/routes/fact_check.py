from flask import Blueprint, jsonify, request

from app.models.fact_check import FactCheckModel
from app.utils.cache import CacheService

fact_check_bp = Blueprint("fact_check", __name__, url_prefix="/api/v1/fact-checks")


class FactCheckController:
    """Controller handling public health fact-checking queries, pagination, and multi-tier caching."""

    @staticmethod
    def get_fact_checks():
        """
        Retrieve a paginated list of fact checks with keyword search and Redis caching.
        Route: GET /api/v1/fact-checks?page=1&limit=10&q=keyword
        """
        try:
            page = int(request.args.get("page", 1))
            limit = int(request.args.get("limit", 10))
            keyword = request.args.get("q", "").strip() or None

            # Enforce boundary limits (clamp max limit to 50 to prevent payload exhaustion)
            page = max(1, page)
            limit = min(max(1, limit), 50)

            # Build deterministic cache key
            cache_key = f"cache:fact_checks:q:{keyword or 'all'}:p:{page}:limit:{limit}"

            # Check cache hit
            cached_data = CacheService.get(cache_key)
            if cached_data:
                return jsonify({
                    "status": "success",
                    "source": "cache",
                    **cached_data
                }), 200

            # Cache miss: query PostgreSQL via Data Access Object
            result = FactCheckModel.get_list(page=page, limit=limit, keyword=keyword)

            response_payload = {
                "data": result.get("items") or [],
                "pagination": result.get("pagination") or {
                    "total_items": 0,
                    "page": page,
                    "limit": limit,
                    "total_pages": 1
                }
            }

            # Populate Redis cache with 10-minute TTL (600 seconds)
            CacheService.set(cache_key, response_payload, expire=600)

            return jsonify({
                "status": "success",
                "source": "database",
                **response_payload
            }), 200

        except Exception as e:
            return jsonify({"error": f"Failed to fetch fact checks: {str(e)}"}), 500

    @staticmethod
    def get_fact_check_detail(item_id):
        """
        Retrieve complete details for a single fact-check record.
        Route: GET /api/v1/fact-checks/<id>
        """
        try:
            # Generate entity-specific cache key
            cache_key = f"cache:fact_checks:detail:{item_id}"

            # Check cache hit
            cached_item = CacheService.get(cache_key)
            if cached_item:
                return jsonify({
                    "status": "success",
                    "source": "cache",
                    "data": cached_item
                }), 200

            # Cache miss: query PostgreSQL
            item = FactCheckModel.get_by_id(item_id)
            if not item:
                return jsonify({"error": "Fact check item not found"}), 404

            # Write-through to Redis with 10-minute TTL
            CacheService.set(cache_key, item, expire=600)

            return jsonify({
                "status": "success",
                "source": "database",
                "data": item
            }), 200

        except Exception as e:
            return jsonify({"error": f"Failed to fetch fact check detail: {str(e)}"}), 500


# Endpoint Route Bindings
fact_check_bp.route("", methods=["GET"])(FactCheckController.get_fact_checks)
fact_check_bp.route("/<int:item_id>", methods=["GET"])(FactCheckController.get_fact_check_detail)