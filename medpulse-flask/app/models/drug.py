from app.utils.db import Database

class DrugModel:
    """openFDA 藥品資料庫操作 Class"""

    @staticmethod
    def get_list(page=1, limit=10, keyword=None, product_type=None):
        """
        取得藥品清單 (支援關鍵字搜尋、藥品類型篩選與分頁)
        註：排除 raw_openfda 大欄位以提升傳輸效能
        """
        offset = (page - 1) * limit
        params = []
        conditions = []

        base_query = """
            SELECT id, brand_name, generic_name, manufacturer_name, product_type, route, active_ingredient, purpose, boxed_warning
            FROM drugs
        """
        count_query = "SELECT COUNT(*) FROM drugs"

        # 關鍵字搜尋 (品名、學名或主要用途)
        if keyword:
            conditions.append("(brand_name ILIKE %s OR generic_name ILIKE %s OR purpose ILIKE %s)")
            pattern = f"%{keyword}%"
            params.extend([pattern, pattern, pattern])

        # 按藥品類型過濾 (例如 HUMAN OTC DRUG 或 PRESCRIPTION)
        if product_type:
            conditions.append("product_type = %s")
            params.append(product_type)

        where_clause = ""
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)

        # 查詢總筆數
        total_res = Database.execute_query(count_query + where_clause, params=params if conditions else None, fetchone=True)
        total_items = total_res["count"] if total_res else 0

        # 查詢分頁資料
        query = f"{base_query}{where_clause} ORDER BY id ASC LIMIT %s OFFSET %s;"
        query_params = params + [limit, offset]

        items = Database.execute_query(query, params=query_params, fetchall=True) or []

        return {
            "items": items,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_items": total_items,
                "total_pages": (total_items + limit - 1) // limit if limit > 0 else 0
            }
        }

    @staticmethod
    def get_by_id(drug_id):
        """根據 ID 取得完整藥品說明書資訊"""
        query = "SELECT * FROM drugs WHERE id = %s;"
        return Database.execute_query(query, (drug_id,), fetchone=True)