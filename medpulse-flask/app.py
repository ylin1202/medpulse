from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from app.utils.db import Database
from app.models.user import UserModel

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 允許跨域請求
    CORS(app)

    # 初始化連線池
    Database.init_pool(app)

    # 每個請求結束後自動釋放連線
    @app.teardown_appcontext
    def teardown_db(exception):
        Database.release_conn(exception)

    # 健康檢查 API
    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "MedPulse Flask Core API",
            "version": "1.0.0"
        }), 200

    # 啟動時自動建立 User 表 (開發用，確保 DB 有表)
    with app.app_context():
        try:
            UserModel.create_table()
            print("Database connection pool initialized & User table checked.")
        except Exception as e:
            print(f"Database initialization skipped or failed: {e}")

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)