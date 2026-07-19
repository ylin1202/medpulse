import random
import redis
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from flask_mail import Message
from app.extensions import mail
from app.models.user import UserModel

# 建立 JWT Auth 的 Blueprint 模組
auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

# ⚡ 連接 Redis (用來存 5 分鐘快取驗證碼)
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)


class AuthController:
    """封裝 Auth 相關 API 邏輯的 Class"""

    @staticmethod
    def send_code():
        """發送 6 位數 Email 驗證碼 API"""
        data = request.get_json() or {}
        email = data.get("email")

        if not email:
            return jsonify({"error": "Email is required"}), 400

        # 1. 產生 6 位數隨機數字
        code = f"{random.randint(100000, 999999)}"

        try:
            # 2. 將驗證碼存入 Redis (Key: verify:user@example.com，有效時間 300 秒/5分鐘)
            redis_client.setex(f"verify:{email}", 300, code)

            # 3. 透過 SMTP 寄出信件
            msg = Message(
                subject="[MedPulse] Your Registration Verification Code",
                sender=current_app.config.get("MAIL_USERNAME"),
                recipients=[email],
                body=f"Hello!\n\nYour verification code for MedPulse is: {code}\n\nThis code will expire in 5 minutes."
            )
            mail.send(msg)

            return jsonify({"message": "Verification code sent successfully"}), 200

        except Exception as e:
            return jsonify({"error": f"Failed to send email: {str(e)}"}), 500

    @staticmethod
    def register():
        """使用者註冊 API (含驗證碼比對)"""
        data = request.get_json() or {}
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")
        code = data.get("code") 

        # 1. 欄位驗證 (Edge Case 防護)
        if not username or not email or not password or not code:
            return jsonify({"error": "Missing required fields: username, email, password, code"}), 400

        # 2. 比對 Redis 中的驗證碼
        saved_code = redis_client.get(f"verify:{email}")
        if not saved_code or saved_code != str(code):
            return jsonify({"error": "Invalid or expired verification code"}), 400

        # 3. 檢查 Email 是否已被註冊
        existing_user = UserModel.get_by_email(email)
        if existing_user:
            return jsonify({"error": "Email is already registered"}), 409

        try:
            # 4. 驗證成功！刪除 Redis 驗證碼防重複使用
            redis_client.delete(f"verify:{email}")

            # 5. 建立新用戶 (UserModel 內部會對 password 進行 Hash)
            new_user = UserModel.create_user(username, email, password)
            
            # 6. 簽發 JWT Token
            access_token = create_access_token(identity=str(new_user["id"]))

            return jsonify({
                "message": "User registered successfully",
                "user": {
                    "id": new_user["id"],
                    "username": new_user["username"],
                    "email": new_user["email"]
                },
                "access_token": access_token
            }), 201

        except Exception as e:
            return jsonify({"error": f"Failed to register user: {str(e)}"}), 500

    @staticmethod
    def login():
        """使用者登入 API"""
        data = request.get_json() or {}
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "Missing email or password"}), 400

        user = UserModel.get_by_email(email)
        if not user or not UserModel.verify_password(user["password_hash"], password):
            return jsonify({"error": "Invalid email or password"}), 401

        access_token = create_access_token(identity=str(user["id"]))

        return jsonify({
            "message": "Login successful",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"]
            },
            "access_token": access_token
        }), 200

    @staticmethod
    @jwt_required()
    def get_profile():
        """取得個人 Profile (需帶 Bearer JWT Token)"""
        current_user_id = get_jwt_identity()
        return jsonify({
            "user_id": current_user_id,
            "status": "authenticated"
        }), 200


# 綁定路由點 (Routes Mapping)
auth_bp.route("/send-code", methods=["POST"])(AuthController.send_code) 
auth_bp.route("/register", methods=["POST"])(AuthController.register)
auth_bp.route("/login", methods=["POST"])(AuthController.login)
auth_bp.route("/me", methods=["GET"])(AuthController.get_profile)