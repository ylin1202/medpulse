from app.utils.db import Database

class FavoriteModel:
    """使用者藥品收藏夾 (User-Drug Favorites) 資料庫操作 Class"""

    @staticmethod
    def create_table():
        """建立 user_favorites 資料表 (外鍵關聯 users 與 drugs)"""
        query = """
        CREATE TABLE IF NOT EXISTS user_favorites (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            drug_id INTEGER NOT NULL REFERENCES drugs(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_user_drug UNIQUE(user_id, drug_id)
        );
        """
        Database.execute_query(query, commit=True)

    @staticmethod
    def add_favorite(user_id, drug_id):
        """新增藥品收藏 (若已收藏則回傳現有紀錄)"""
        # 1. 嘗試寫入
        insert_query = """
        INSERT INTO user_favorites (user_id, drug_id)
        VALUES (%s, %s)
        ON CONFLICT (user_id, drug_id) DO NOTHING
        RETURNING id, user_id, drug_id, created_at;
        """
        result = Database.execute_query(insert_query, (user_id, int(drug_id)), fetchone=True, commit=True)
        
        # 2. 若原本已收藏 (result 為 None)，則查詢現有紀錄回傳
        if not result:
            select_query = """
            SELECT id, user_id, drug_id, created_at 
            FROM user_favorites 
            WHERE user_id = %s AND drug_id = %s;
            """
            result = Database.execute_query(select_query, (user_id, int(drug_id)), fetchone=True)

        return result

    @staticmethod
    def remove_favorite(user_id, drug_id):
        """取消藥品收藏"""
        query = """
        DELETE FROM user_favorites
        WHERE user_id = %s AND drug_id = %s;
        """
        Database.execute_query(query, (user_id, int(drug_id)), commit=True)
        return True

    @staticmethod
    def is_favorited(user_id, drug_id):
        """檢查特定藥品是否已被該使用者收藏"""
        query = """
        SELECT 1 FROM user_favorites
        WHERE user_id = %s AND drug_id = %s
        LIMIT 1;
        """
        res = Database.execute_query(query, (user_id, int(drug_id)), fetchone=True)
        return res is not None

    @staticmethod
    def get_user_favorites(user_id):
        """取得使用者收藏的所有藥品詳細資訊 (直接 JOIN drugs 表)"""
        query = """
        SELECT 
            f.id AS favorite_id,
            f.created_at AS favorited_at,
            d.id AS drug_id,
            d.brand_name,
            d.generic_name,
            d.manufacturer_name,
            d.purpose,
            d.indications_and_usage
        FROM user_favorites f
        JOIN drugs d ON f.drug_id = d.id
        WHERE f.user_id = %s
        ORDER BY f.created_at DESC;
        """
        return Database.execute_query(query, (user_id,), fetchall=True) or []