from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
from app.utils.db import Database
from app.models.user import UserModel
from app.routes.auth import auth_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 允許跨域請求 (供 Flutter 前端呼叫)
    CORS(app)

    # 初始化 JWTManager
    JWTManager(app)

    # 初始化 DB 連線池
    Database.init_pool(app)

    # 每個請求結束後自動釋放連線還給連線池
    @app.teardown_appcontext
    def teardown_db(exception):
        Database.release_conn(exception)

    # 註冊 Auth 路由藍圖
    app.register_blueprint(auth_bp)

    # 健康檢查 API
    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "MedPulse Flask Core API",
            "version": "1.0.0"
        }), 200

    # 啟動時建立 User 表 (若尚未存在)
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