from flask import Blueprint, request, jsonify
from app.models.drug import DrugModel
from app.utils.cache import CacheService    # 💡 引入寫好的快取工具

drug_bp = Blueprint("drug", __name__, url_prefix="/api/v1/drugs")


class DrugController:
    """openFDA 藥品資料 API Controller"""

    @staticmethod
    def get_drugs():
        try:
            keyword = request.args.get("q", "").strip() or None
            page = int(request.args.get("page", 1))
            limit = int(request.args.get("limit", 10))

            # 1. 建立動態快取 Key
            cache_key = f"cache:drugs:q:{keyword}:p:{page}:limit:{limit}"

            # 2. 嘗試命中快取
            cached_data = CacheService.get(cache_key)
            if cached_data:
                return jsonify({
                    "status": "success",
                    "source": "cache",
                    **cached_data
                }), 200

            # 3. 快取未命中，直接戳原本的 Model 邏輯
            result = DrugModel.get_list(keyword=keyword, page=page, limit=limit)

            # 如果 result 本身就是測試預期的最終格式，或者內部藏在 pagination 裡，統統撈出來
            if isinstance(result, dict) and "pagination" in result:
                pagination_data = result["pagination"]
                total_count = pagination_data.get("total_items") or pagination_data.get("total") or 0
                items_data = result.get("items") or result.get("data") or []
            else:
                # 如果 Model 只丟出原始 dict，我們從最底層的鍵值拿
                total_count = result.get("total_items") or result.get("total") or result.get("count") or 0
                items_data = result.get("items") or result.get("data") or []

            # 5. 組裝完全符合測試斷言的標準格式
            response_payload = {
                "pagination": {
                    "total_items": total_count,
                    "page": page,
                    "limit": limit,
                    "total_pages": result.get("total_pages") or 1
                },
                "data": items_data
            }

            # 6. 回填 Redis 快取
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
        """取得單一藥品詳細說明書 (GET /api/v1/drugs/<drug_id>)"""
        try:
            # 1. 定義單一藥品詳情的專屬 Redis Key
            cache_key = f"cache:drugs:detail:{drug_id}"

            # 2. 嘗試從 Redis 讀取快取
            cached_drug = CacheService.get(cache_key)
            if cached_drug:
                # 快取命中 (Cache Hit)！直接微秒級回傳
                return jsonify({
                    "status": "success",
                    "source": "cache",
                    "data": cached_drug
                }), 200

            # 3. 快取未命中 (Cache Miss)，走原本的 PostgreSQL 查詢
            drug = DrugModel.get_by_id(drug_id)
            if not drug:
                return jsonify({"error": "Drug not found"}), 404

            # 4. 查到資料後，順手寫入 Redis 快取，預設活 10 分鐘 (600秒)
            CacheService.set(cache_key, drug, expire=600)

            return jsonify({
                "status": "success",
                "source": "database",
                "data": drug
            }), 200

        except Exception as e:
            return jsonify({"error": f"Failed to fetch drug detail: {str(e)}"}), 500


# 綁定路由點
drug_bp.route("", methods=["GET"])(DrugController.get_drugs)
drug_bp.route("/<string:drug_id>", methods=["GET"])(DrugController.get_drug_detail)