from flask import g
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool


class Database:
    _pool = None

    @classmethod
    def init_pool(cls, app):
        """Initialize the SimpleConnectionPool with application configuration credentials."""
        if cls._pool is None:
            cls._pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                host=app.config["DB_HOST"],
                port=app.config["DB_PORT"],
                dbname=app.config["DB_NAME"],
                user=app.config["DB_USER"],
                password=app.config["DB_PASSWORD"]
            )

    @classmethod
    def get_conn(cls):
        """Acquire a thread-safe connection from the connection pool and bind it to Flask's request context."""
        if "db_conn" not in g:
            g.db_conn = cls._pool.getconn()
        return g.db_conn

    @classmethod
    def release_conn(cls, exception=None):
        """Return the context-bound connection back to the connection pool upon request completion."""
        conn = g.pop("db_conn", None)
        if conn is not None and cls._pool is not None:
            cls._pool.putconn(conn)

    @classmethod
    def execute_query(cls, query, params=None, fetchone=False, fetchall=False, commit=False):
        """
        Execute raw SQL queries with automatic cursor management, dictionary serialization, and rollback safety.
        Returns records as RealDict objects (dict-like key-value structures).
        """
        conn = cls.get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params or ())
                
                result = None
                if fetchone:
                    result = cursor.fetchone()
                elif fetchall:
                    result = cursor.fetchall()

                if commit:
                    conn.commit()

                return result
        except Exception as e:
            if commit:
                conn.rollback()  # Automatically rollback transactions on error to prevent InFailedSqlTransaction states
            raise e