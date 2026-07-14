from flask import Blueprint, request, jsonify
from app.models.fact_check import FactCheckModel

fact_check_bp = Blueprint("fact_check", __name__, url_prefix="/api/v1/fact-checks")

class FactCheckController:
    """封裝闢謠專區 API 邏輯的 Class"""

    @staticmethod
    def get_fact_checks():
        """取得闢謠列表 (GET /api/v1/fact-checks?page=1&limit=10&q=keyword)"""
        try:
            page = int(request.args.get("page", 1))
            limit = int(request.args.get("limit", 10))
            keyword = request.args.get("q", "").strip() or None

            # 邊界值保護
            page = max(1, page)
            limit = min(max(1, limit), 50) # 限制單頁最多 50 筆

            result = FactCheckModel.get_list(page=page, limit=limit, keyword=keyword)
            return jsonify({
                "status": "success",
                "data": result["items"],
                "pagination": result["pagination"]
            }), 200

        except Exception as e:
            return jsonify({"error": f"Failed to fetch fact checks: {str(e)}"}), 500

    @staticmethod
    def get_fact_check_detail(item_id):
        """取得單篇闢謠詳情 (GET /api/v1/fact-checks/<id>)"""
        try:
            item = FactCheckModel.get_by_id(item_id)
            if not item:
                return jsonify({"error": "Fact check item not found"}), 404

            return jsonify({
                "status": "success",
                "data": item
            }), 200

        except Exception as e:
            return jsonify({"error": f"Failed to fetch fact check detail: {str(e)}"}), 500


# 綁定路由點
fact_check_bp.route("", methods=["GET"])(FactCheckController.get_fact_checks)
fact_check_bp.route("/<int:item_id>", methods=["GET"])(FactCheckController.get_fact_check_detail)