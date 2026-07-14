import psycopg2
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import RealDictCursor
from flask import current_app, g

class Database:
    """封裝 psycopg2 連線池管理 Class"""
    _pool = None

    @classmethod
    def init_pool(cls, app):
        """初始化連線池"""
        if cls._pool is None:
            cls._pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10, # 連線池大小
                host=app.config["DB_HOST"],
                port=app.config["DB_PORT"],
                dbname=app.config["DB_NAME"],
                user=app.config["DB_USER"],
                password=app.config["DB_PASSWORD"]
            )

    @classmethod
    def get_conn(cls):
        """從連線池取得連線"""
        if "db_conn" not in g:
            g.db_conn = cls._pool.getconn()
        return g.db_conn

    @classmethod
    def release_conn(cls, exception=None):
        """請求結束時釋放連線還給連線池"""
        conn = g.pop("db_conn", None)
        if conn is not None and cls._pool is not None:
            cls._pool.putconn(conn)

    @classmethod
    def execute_query(cls, query, params=None, fetchone=False, fetchall=False, commit=False):
        """通用 SQL 執行函式，回傳 RealDict 格式 (類似 Dict/JSON)"""
        conn = cls.get_conn()
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