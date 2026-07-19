from flask import Blueprint, request, jsonify
from app.models.pharmacy import PharmacyModel
from app.utils.cache import CacheService  # 引入快取服務

pharmacy_bp = Blueprint("pharmacy", __name__, url_prefix="/api/v1/pharmacies")

class PharmacyController:
    """藥局資料 API Controller (整合 Redis 快取防禦)"""

    @staticmethod
    def get_pharmacies():
        """
        取得所有藥局清單 (GET /api/v1/pharmacies?q=祥全&city=臺北市)
        """
        try:
            keyword = request.args.get("q", "").strip() or None
            city = request.args.get("city", "").strip() or None

            # 1. 建立動態快取 Key (將 None 轉為 'all' 字串以維持 Key 結構整齊)
            cache_key = f"cache:pharmacies:q:{keyword or 'all'}:city:{city or 'all'}"

            # 2. 嘗試從 Redis 快取命中全量或篩選資料
            cached_data = CacheService.get(cache_key)
            if cached_data:
                return jsonify({
                    "status": "success",
                    "source": "cache", 
                    "count": len(cached_data),
                    "data": cached_data
                }), 200

            # 3. 快取未命中 (Cache Miss)，呼叫原本的資料庫全量查詢
            pharmacies = PharmacyModel.get_all(keyword=keyword, city=city)

            # 4. 將查詢結果寫入 Redis，全量藥局資料較大，建議設定 10 分鐘 (600秒)
            CacheService.set(cache_key, pharmacies, expire=600)

            return jsonify({
                "status": "success",
                "source": "database", 
                "count": len(pharmacies),
                "data": pharmacies
            }), 200

        except Exception as e:
            return jsonify({"error": f"Failed to fetch pharmacies: {str(e)}"}), 500


# 綁定路由點
pharmacy_bp.route("", methods=["GET"])(PharmacyController.get_pharmacies)