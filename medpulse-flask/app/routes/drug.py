import math
from flask import Blueprint, jsonify, request

from app.models.drug import DrugModel
from app.utils.cache import CacheService

drug_bp = Blueprint("drug", __name__, url_prefix="/api/v1/drugs")


class DrugController:
    """Controller handling OpenFDA medication queries, pagination, and multi-tier caching."""

    @staticmethod
    def get_drugs():
        """
        Retrieve a paginated list of drugs with keyword search and Redis caching.
        Route: GET /api/v1/drugs
        """
        try:
            # Parse and sanitize query parameters (enforce min bounds to prevent ZeroDivisionError)
            keyword = request.args.get("q", "").strip() or None
            page = max(1, int(request.args.get("page", 1)))
            limit = max(1, int(request.args.get("limit", 10)))

            # Build deterministic cache key
            cache_key = f"cache:drugs:q:{keyword}:p:{page}:limit:{limit}"

            # Check cache hit
            cached_data = CacheService.get(cache_key)
            if cached_data:
                return jsonify({
                    "status": "success",
                    "source": "cache",
                    **cached_data
                }), 200

            # Cache miss: query PostgreSQL via Data Access Object
            result = DrugModel.get_list(keyword=keyword, page=page, limit=limit)

            # Normalize payload and extract total count across possible DAO return shapes
            if isinstance(result, dict) and "pagination" in result:
                pagination_data = result.get("pagination", {})
                total_count = (
                    pagination_data.get("total_items")
                    or pagination_data.get("total")
                    or 0
                )
                items_data = result.get("items") or result.get("data") or []
                raw_total_pages = pagination_data.get("total_pages")
            elif isinstance(result, dict):
                total_count = (
                    result.get("total_items")
                    or result.get("total")
                    or result.get("count")
                    or 0
                )
                items_data = result.get("items") or result.get("data") or []
                raw_total_pages = result.get("total_pages")
            else:
                total_count = 0
                items_data = []
                raw_total_pages = None

            # Calculate total pages dynamically
            if raw_total_pages is not None and raw_total_pages > 1:
                total_pages = raw_total_pages
            elif total_count > 0:
                total_pages = math.ceil(total_count / limit)
            else:
                total_pages = 1

            response_payload = {
                "pagination": {
                    "total_items": total_count,
                    "total": total_count,
                    "page": page,
                    "limit": limit,
                    "total_pages": total_pages
                },
                "data": items_data
            }

            # Populate Redis cache with a 10-minute TTL (600 seconds)
            CacheService.set(cache_key, response_payload, expire=600)

            return jsonify({
                "status": "success",
                "source": "database",
                **response_payload
            }), 200

        except Exception as e:
            return jsonify({"error": f"Failed to fetch drugs: {str(e)}"}), 500

    @staticmethod
    def get_drug_detail(drug_id):
        """
        Retrieve complete package insert details for a single medication.
        Route: GET /api/v1/drugs/<drug_id>
        """
        try:
            # Generate entity-specific cache key
            cache_key = f"cache:drugs:detail:{drug_id}"

            # Check cache hit
            cached_drug = CacheService.get(cache_key)
            if cached_drug:
                return jsonify({
                    "status": "success",
                    "source": "cache",
                    "data": cached_drug
                }), 200

            # Cache miss: query PostgreSQL
            drug = DrugModel.get_by_id(drug_id)
            if not drug:
                return jsonify({"error": "Drug not found"}), 404

            # Write-through to Redis with 10-minute TTL
            CacheService.set(cache_key, drug, expire=600)

            return jsonify({
                "status": "success",
                "source": "database",
                "data": drug
            }), 200

        except Exception as e:
            return jsonify({"error": f"Failed to fetch drug detail: {str(e)}"}), 500


# Endpoint Route Bindings
drug_bp.route("", methods=["GET"])(DrugController.get_drugs)
drug_bp.route("/<string:drug_id>", methods=["GET"])(DrugController.get_drug_detail)