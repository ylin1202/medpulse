from flask import Blueprint, request, jsonify
from app.models.fact_check import FactCheckModel
from app.utils.cache import CacheService 

fact_check_bp = Blueprint("fact_check", __name__, url_prefix="/api/v1/fact-checks")

class FactCheckController:
    """封裝闢謠專區 API 邏輯的 Class (整合 Redis 快取防禦)"""

    @staticmethod
    def get_fact_checks():
        """取得闢謠列表 (GET /api/v1/fact-checks?page=1&limit=10&q=keyword)"""
        try:
            page = int(request.args.get("page", 1))
            limit = int(request.args.get("limit", 10))
            keyword = request.args.get("q", "").strip() or None

            # 邊界值保護
            page = max(1, page)
            limit = min(max(1, limit), 50)  # 限制單頁最多 50 筆

            # 1. 建立動態分頁快取 Key
            cache_key = f"cache:fact_checks:q:{keyword or 'all'}:p:{page}:limit:{limit}"

            # 2. 嘗試從 Redis 命中有狀態快取
            cached_data = CacheService.get(cache_key)
            if cached_data:
                return jsonify({
                    "status": "success",
                    "source": "cache",  # 標記來源自快取
                    **cached_data
                }), 200

            # 3. 快取未命中 (Cache Miss)，走原本的資料庫查詢
            result = FactCheckModel.get_list(page=page, limit=limit, keyword=keyword)
            
            # 4. 組裝完全對齊原架構與斷言的 Payload
            response_payload = {
                "data": result.get("items") or [],
                "pagination": result.get("pagination") or {
                    "total_items": 0,
                    "page": page,
                    "limit": limit,
                    "total_pages": 1
                }
            }

            # 5. 寫入 Redis 快取，預設存活 10 分鐘 (600秒)
            CacheService.set(cache_key, response_payload, expire=600)

            return jsonify({
                "status": "success",
                "source": "database",  # 標記來源自資料庫
                **response_payload
            }), 200

        except Exception as e:
            return jsonify({"error": f"Failed to fetch fact checks: {str(e)}"}), 500

    @staticmethod
    def get_fact_check_detail(item_id):
        """取得單篇闢謠詳情 (GET /api/v1/fact-checks/<id>)"""
        try:
            # 1. 定義單篇詳情的專屬 Redis Key
            cache_key = f"cache:fact_checks:detail:{item_id}"

            # 2. 嘗試命中快取
            cached_item = CacheService.get(cache_key)
            if cached_item:
                return jsonify({
                    "status": "success",
                    "source": "cache",
                    "data": cached_item
                }), 200

            # 3. 快取未命中，查詢資料庫
            item = FactCheckModel.get_by_id(item_id)
            if not item:
                return jsonify({"error": "Fact check item not found"}), 404

            # 4. 查有實據，寫入 Redis 記憶體快取 10 分鐘
            CacheService.set(cache_key, item, expire=600)

            return jsonify({
                "status": "success",
                "source": "database",
                "data": item
            }), 200

        except Exception as e:
            return jsonify({"error": f"Failed to fetch fact check detail: {str(e)}"}), 500


# 綁定路由點
fact_check_bp.route("", methods=["GET"])(FactCheckController.get_fact_checks)
fact_check_bp.route("/<int:item_id>", methods=["GET"])(FactCheckController.get_fact_check_detail)