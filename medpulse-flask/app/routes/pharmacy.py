from flask import Blueprint, request, jsonify
from app.models.pharmacy import PharmacyModel

pharmacy_bp = Blueprint("pharmacy", __name__, url_prefix="/api/v1/pharmacies")

class PharmacyController:
    """藥局資料 API Controller"""

    @staticmethod
    def get_pharmacies():
        """
        取得所有藥局清單 (GET /api/v1/pharmacies?q=祥全&city=臺北市)
        """
        try:
            keyword = request.args.get("q", "").strip() or None
            city = request.args.get("city", "").strip() or None

            # 呼叫全量查詢
            pharmacies = PharmacyModel.get_all(keyword=keyword, city=city)

            return jsonify({
                "status": "success",
                "count": len(pharmacies),
                "data": pharmacies
            }), 200

        except Exception as e:
            return jsonify({"error": f"Failed to fetch pharmacies: {str(e)}"}), 500


# 綁定路由點
pharmacy_bp.route("", methods=["GET"])(PharmacyController.get_pharmacies)