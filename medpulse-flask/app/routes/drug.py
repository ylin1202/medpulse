import math
from flask import Blueprint, request, jsonify
from app.models.drug import DrugModel
from app.utils.cache import CacheService    # 💡 引入寫好的快取工具

drug_bp = Blueprint("drug", __name__, url_prefix="/api/v1/drugs")


class DrugController:
    """openFDA 藥品資料 API Controller"""

    @staticmethod
    def get_drugs():
        try:
            # 1. 取得並清理 Request 參數 (加上 limit 防呆，防止 limit <= 0 造成除以 0 崩潰)
            keyword = request.args.get("q", "").strip() or None
            page = max(1, int(request.args.get("page", 1)))
            limit = max(1, int(request.args.get("limit", 10)))

            # 2. 建立動態快取 Key
            cache_key = f"cache:drugs:q:{keyword}:p:{page}:limit:{limit}"

            # 3. 嘗試命中快取
            cached_data = CacheService.get(cache_key)
            if cached_data:
                return jsonify({
                    "status": "success",
                    "source": "cache",
                    **cached_data
                }), 200

            # 4. 快取未命中，撈取 Model 資料
            result = DrugModel.get_list(keyword=keyword, page=page, limit=limit)

            # 5. 解析數據與總筆數 (相容多元 Model 回傳結構)
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

            # 6. 強固的 total_pages 動態計算！
            # 若原始 total_pages 存在且大於 1 則信任它；否則只要 total_count > 0，一律重新用 math.ceil 計算
            if raw_total_pages is not None and raw_total_pages > 1:
                total_pages = raw_total_pages
            elif total_count > 0:
                total_pages = math.ceil(total_count / limit)
            else:
                total_pages = 1

            # 7. 組裝完全符合測試斷言與前端 Flutter 的標準格式
            response_payload = {
                "pagination": {
                    "total_items": total_count,
                    "total": total_count,          # 補上 total 以相容 Flutter
                    "page": page,
                    "limit": limit,
                    "total_pages": total_pages     # 確保精準的總頁數
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