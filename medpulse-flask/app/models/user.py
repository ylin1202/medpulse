from werkzeug.security import generate_password_hash, check_password_hash
from app.utils.db import Database


class UserModel:
    """Data Access Object (DAO) for managing user accounts and authentication using raw SQL."""

    @staticmethod
    def create_table():
        """Create the `users` table schema if it does not exist."""
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
        """Create a new user record with a securely hashed password."""
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
        """Retrieve user credentials and account details by email address."""
        query = "SELECT * FROM users WHERE email = %s;"
        return Database.execute_query(query, (email,), fetchone=True)

    @staticmethod
    def verify_password(stored_password_hash, provided_password):
        """Verify candidate plaintext password against stored cryptographic hash."""
        return check_password_hash(stored_password_hash, provided_password)
    
    @staticmethod
    def verify_user_email(user_id):
        """Mark user account as verified upon email confirmation."""
        query = "UPDATE users SET is_verified = TRUE WHERE id = %s RETURNING id, is_verified;"
        return Database.execute_query(query, (user_id,), fetchone=True, commit=True)