from flask import Blueprint, request, jsonify
from app.models.drug import DrugModel

drug_bp = Blueprint("drug", __name__, url_prefix="/api/v1/drugs")

class DrugController:
    """封裝藥品查詢 API 邏輯的 Class"""

    @staticmethod
    def get_drugs():
        """取得藥品清單與搜尋 (GET /api/v1/drugs?page=1&limit=10&q=minoxidil&type=HUMAN OTC DRUG)"""
        try:
            page = int(request.args.get("page", 1))
            limit = int(request.args.get("limit", 10))
            keyword = request.args.get("q", "").strip() or None
            product_type = request.args.get("type", "").strip() or None

            page = max(1, page)
            limit = min(max(1, limit), 50)

            result = DrugModel.get_list(page=page, limit=limit, keyword=keyword, product_type=product_type)
            return jsonify({
                "status": "success",
                "data": result["items"],
                "pagination": result["pagination"]
            }), 200

        except Exception as e:
            return jsonify({"error": f"Failed to fetch drugs: {str(e)}"}), 500

    @staticmethod
    def get_drug_detail(drug_id):
        """取得單一藥品詳細說明書 (GET /api/v1/drugs/<drug_id>)"""
        try:
            drug = DrugModel.get_by_id(drug_id)
            if not drug:
                return jsonify({"error": "Drug not found"}), 404

            return jsonify({
                "status": "success",
                "data": drug
            }), 200

        except Exception as e:
            return jsonify({"error": f"Failed to fetch drug detail: {str(e)}"}), 500


# 綁定路由點
drug_bp.route("", methods=["GET"])(DrugController.get_drugs)
drug_bp.route("/<string:drug_id>", methods=["GET"])(DrugController.get_drug_detail)