from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.models.user import UserModel

# 建立 JWT Auth 的 Blueprint 模組
auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

class AuthController:
    """封裝 Auth 相關 API 邏輯的 Class"""

    @staticmethod
    def register():
        """使用者註冊 API"""
        data = request.get_json() or {}
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")

        # 1. 欄位驗證 (Edge Case 防護)
        if not username or not email or not password:
            return jsonify({"error": "Missing required fields: username, email, password"}), 400

        # 2. 檢查 Email 是否已被註冊
        existing_user = UserModel.get_by_email(email)
        if existing_user:
            return jsonify({"error": "Email is already registered"}), 409

        try:
            # 3. 建立新用戶 (UserModel 內部會對 password 進行 Hash)
            new_user = UserModel.create_user(username, email, password)
            
            # 4. 簽發 JWT Token (期限預設為 1 天)
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

        # 1. 欄位驗證
        if not email or not password:
            return jsonify({"error": "Missing email or password"}), 400

        # 2. 尋找用戶
        user = UserModel.get_by_email(email)
        if not user:
            return jsonify({"error": "Invalid email or password"}), 401

        # 3. 驗證密碼 Hash
        if not UserModel.verify_password(user["password_hash"], password):
            return jsonify({"error": "Invalid email or password"}), 401

        # 4. 簽發 JWT Token
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
auth_bp.route("/register", methods=["POST"])(AuthController.register)
auth_bp.route("/login", methods=["POST"])(AuthController.login)
auth_bp.route("/me", methods=["GET"])(AuthController.get_profile)