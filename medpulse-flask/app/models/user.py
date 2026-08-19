from werkzeug.security import generate_password_hash, check_password_hash
from app.utils.db import Database

class UserModel:
    """使用者資料庫操作 Class (原生 SQL 封裝)"""

    @staticmethod
    def create_table():
        query = """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            is_verified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        Database.execute_query(query, commit=True)

    @staticmethod
    def create_user(username, email, password):
        """新增使用者 (密碼自動哈希加密)"""
        hashed_password = generate_password_hash(password)
        query = """
        INSERT INTO users (username, email, password_hash)
        VALUES (%s, %s, %s)
        RETURNING id, username, email, created_at;
        """
        return Database.execute_query(
            query, (username, email, hashed_password), fetchone=True, commit=True
        )

    @staticmethod
    def get_by_email(email):
        """根據 Email 尋找使用者"""
        query = "SELECT * FROM users WHERE email = %s;"
        return Database.execute_query(query, (email,), fetchone=True)

    @staticmethod
    def verify_password(stored_password_hash, provided_password):
        """驗證密碼是否正確"""
        return check_password_hash(stored_password_hash, provided_password)
    
    @staticmethod
    def verify_user_email(user_id):
        query = "UPDATE users SET is_verified = TRUE WHERE id = %s RETURNING id, is_verified;"
        return Database.execute_query(query, (user_id,), fetchone=True, commit=True)
    