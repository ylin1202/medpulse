from app.utils.db import Database


class FavoriteModel:
    """Data Access Object (DAO) for managing user medication bookmarks/favorites."""

    @staticmethod
    def create_table():
        """Create the `user_favorites` table with foreign key cascades and unique constraints."""
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
        """
        Add a drug to the user's favorites list.

        Performs an idempotent insert; returns existing bookmark record if already favorited.
        """
        # 1. Attempt insert with conflict avoidance
        insert_query = """
        INSERT INTO user_favorites (user_id, drug_id)
        VALUES (%s, %s)
        ON CONFLICT (user_id, drug_id) DO NOTHING
        RETURNING id, user_id, drug_id, created_at;
        """
        result = Database.execute_query(insert_query, (user_id, int(drug_id)), fetchone=True, commit=True)
        
        # 2. Fetch existing bookmark record if conflict occurred (result is None)
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
        """Remove a drug from the user's favorites list."""
        query = """
        DELETE FROM user_favorites
        WHERE user_id = %s AND drug_id = %s;
        """
        Database.execute_query(query, (user_id, int(drug_id)), commit=True)
        return True

    @staticmethod
    def is_favorited(user_id, drug_id):
        """Check if a specific medication is favorited by the user."""
        query = """
        SELECT 1 FROM user_favorites
        WHERE user_id = %s AND drug_id = %s
        LIMIT 1;
        """
        res = Database.execute_query(query, (user_id, int(drug_id)), fetchone=True)
        return res is not None

    @staticmethod
    def get_user_favorites(user_id):
        """Retrieve all favorited medications for a user with joined drug metadata."""
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