from app.utils.db import Database

class FactCheckModel:
    """食藥/健康闢謠 PUBHEALTH 資料庫操作 Class"""

    @staticmethod
    def get_list(page=1, limit=10, keyword=None):
        """
        取得闢謠列表 (支援分頁與關鍵字搜尋)
        註：明確列出欄位，特意排除 embedding 欄位以優化 API 傳輸效能
        """
        offset = (page - 1) * limit
        params = []
        
        # 基礎 SQL (排除 embedding)
        base_query = """
            SELECT id, claim, explanation, label, claim_url, main_text, sources
            FROM factcheck_vectors
        """
        count_query = "SELECT COUNT(*) FROM factcheck_vectors"
        
        where_clause = ""
        if keyword:
            where_clause = " WHERE claim ILIKE %s OR explanation ILIKE %s"
            search_pattern = f"%{keyword}%"
            params.extend([search_pattern, search_pattern])

        # 查詢總筆數 (供前端計算總頁數)
        total_count_res = Database.execute_query(count_query + where_clause, params=params if keyword else None, fetchone=True)
        total_items = total_count_res["count"] if total_count_res else 0

        # 分頁查詢資料
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
    def get_by_id(item_id):
        """根據 ID 取得單篇闢謠詳細資訊"""
        query = """
            SELECT id, claim, explanation, label, claim_url, main_text, sources
            FROM factcheck_vectors
            WHERE id = %s;
        """
        return Database.execute_query(query, (item_id,), fetchone=True)