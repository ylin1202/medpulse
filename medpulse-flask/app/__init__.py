from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter.errors import RateLimitExceeded

from config import Config
from app.extensions import mail
from app.utils.db import Database
from app.utils.limiter import limiter
from app.utils.cache import CacheService
from app.models.user import UserModel
from app.models.favorite import FavoriteModel

# 引入路由藍圖
from app.routes.auth import auth_bp
from app.routes.fact_check import fact_check_bp
from app.routes.drug import drug_bp
from app.routes.favorite import favorite_bp
from app.routes.pharmacy import pharmacy_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 開啟 JWT 黑名單檢查功能
    app.config["JWT_BLACKLIST_ENABLED"] = True
    app.config["JWT_BLACKLIST_TOKEN_CHECKS"] = ["access", "refresh"]

    # 允許跨域請求
    CORS(app)

    # 初始化 JWTManager
    jwt = JWTManager(app)
    
    # 初始化 Flask-Mail (會去讀 app.config['MAIL_SERVER'] 等設定)
    mail.init_app(app)

    # 註冊流量限制器
    limiter.init_app(app)

    # 初始化 DB 連線池
    Database.init_pool(app)

    # 每個請求結束後自動釋放連線還給連線池
    app.teardown_appcontext(Database.release_conn)

    # 註冊路由藍圖
    app.register_blueprint(auth_bp)
    app.register_blueprint(fact_check_bp)
    app.register_blueprint(drug_bp)
    app.register_blueprint(favorite_bp)
    app.register_blueprint(pharmacy_bp)
    
    # 健康檢查 API
    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "MedPulse Flask Core API",
            "version": "1.0.0"
        }), 200

    # 啟動時自動檢查並建立關聯資料表
    with app.app_context():
        try:
            UserModel.create_table()
            FavoriteModel.create_table()
            print("Database connection pool initialized & User/Favorite tables checked.")
        except Exception as e:
            print(f"Database initialization skipped or failed: {e}")
    
    # 自訂 429 流量超限錯誤回應
    @app.errorhandler(RateLimitExceeded)
    def ratelimit_handler(e):
        return jsonify({
            "status": "fail",
            "error": "Too Many Requests",
            "message": f"You have exceeded your request limit. Please try again later. Details: {e.description}"
        }), 429

    # 註冊 JWT 黑名單（Blocklist）檢查回呼函式
    @jwt.token_in_blocklist_loader
    def check_if_token_is_revoked(jwt_header, jwt_payload: dict):
        """
        每當有需要驗證的請求（帶有 @jwt_required()）進來時，
        Flask-JWT-Extended 會自動呼叫此處，檢查這把鑰匙是否已被黑名單廢棄。
        """
        try:
            # 取得該 JWT 的唯一識別碼 (JWT ID)
            jti = jwt_payload["jti"]
            
            # 取得共用的 Redis 連線實例
            redis_client = CacheService.get_client()
            
            # 查詢 Redis 中是否存在此 jti 的黑名單紀錄
            token_in_redis = redis_client.get(f"blacklist:{jti}")
            
            # 若存在代表使用者已主動登出，回傳 True 阻斷連線
            return token_in_redis is not None
            
        except Exception:
            # 防禦性降級：若 Redis 連線異常，預設回傳 False 放行以避免影響正常業務（亦可依資安策略改為 True 嚴格攔截）
            return False

    return app