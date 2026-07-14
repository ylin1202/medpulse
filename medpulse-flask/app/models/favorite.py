from app.utils.db import Database

class FavoriteModel:
    """使用者收藏夾 (藥品與闢謠) 資料庫操作 Class"""

    @staticmethod
    def create_table():
        """建立 user_favorites 資料表"""
        query = """
        CREATE TABLE IF NOT EXISTS user_favorites (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            item_type VARCHAR(20) NOT NULL, -- 'drug' 或 'fact_check'
            item_id VARCHAR(100) NOT NULL,   -- 藥品 ID (字串) 或闢謠 ID (轉字串)
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_user_item UNIQUE(user_id, item_type, item_id)
        );
        """
        Database.execute_query(query, commit=True)

    @staticmethod
    def add_favorite(user_id, item_type, item_id):
        """新增收藏 (若重複則忽略)"""
        query = """
        INSERT INTO user_favorites (user_id, item_type, item_id)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, item_type, item_id) DO NOTHING
        RETURNING id, user_id, item_type, item_id, created_at;
        """
        return Database.execute_query(query, (user_id, item_type, str(item_id)), fetchone=True, commit=True)

    @staticmethod
    def remove_favorite(user_id, item_type, item_id):
        """取消收藏"""
        query = """
        DELETE FROM user_favorites
        WHERE user_id = %s AND item_type = %s AND item_id = %s;
        """
        Database.execute_query(query, (user_id, item_type, str(item_id)), commit=True)
        return True

    @staticmethod
    def get_user_favorites(user_id, item_type=None):
        """取得使用者的收藏清單 (可按 item_type 過濾)"""
        if item_type == "drug":
            query = """
            SELECT f.id AS favorite_id, f.created_at AS favorited_at, d.id, d.brand_name, d.generic_name, d.purpose
            FROM user_favorites f
            JOIN drugs d ON f.item_id = d.id
            WHERE f.user_id = %s AND f.item_type = 'drug'
            ORDER BY f.created_at DESC;
            """
            return Database.execute_query(query, (user_id,), fetchall=True) or []

        elif item_type == "fact_check":
            query = """
            SELECT f.id AS favorite_id, f.created_at AS favorited_at, fc.id, fc.claim, fc.explanation, fc.label
            FROM user_favorites f
            JOIN factcheck_vectors fc ON f.item_id = fc.id::text
            WHERE f.user_id = %s AND f.item_type = 'fact_check'
            ORDER BY f.created_at DESC;
            """
            return Database.execute_query(query, (user_id,), fetchall=True) or []

        else:
            # 回傳所有收藏紀錄的基本 ID 資訊
            query = """
            SELECT id, item_type, item_id, created_at
            FROM user_favorites
            WHERE user_id = %s
            ORDER BY created_at DESC;
            """
            return Database.execute_query(query, (user_id,), fetchall=True) or []