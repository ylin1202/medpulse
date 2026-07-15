from app.utils.db import Database

class PharmacyModel:
    """健保藥局資料庫操作 Class"""

    @staticmethod
    def get_all(keyword=None, city=None):
        """
        取得所有藥局清單 (不分頁，支援關鍵字搜尋與縣市篩選)
        """
        params = []
        conditions = []

        query = """
            SELECT id, name, status, city, district, address, phone, is_nhi_contracted, latitude, longitude
            FROM pharmacies
        """

        # 關鍵字搜尋 (藥局名稱或地址)
        if keyword:
            conditions.append("(name ILIKE %s OR address ILIKE %s)")
            pattern = f"%{keyword}%"
            params.extend([pattern, pattern])

        # 按縣市篩選 (例如：臺北市)
        if city:
            conditions.append("city = %s")
            params.append(city)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY id ASC;"

        return Database.execute_query(query, params=params if conditions else None, fetchall=True) or []