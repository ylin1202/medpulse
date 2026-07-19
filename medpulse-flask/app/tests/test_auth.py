import json
import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from flask_jwt_extended import create_access_token

class TestAuthAPI:
    """使用者認證與註冊功能 (Auth) API 路由控制器的單元測試類別"""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """在每個測試方法執行前，自動初始化 Flask 測試客戶端、生成 Token 與共用變數"""
        app = create_app()
        app.config['TESTING'] = True
        app.config["RATELIMIT_ENABLED"] = False
        app.config['JWT_SECRET_KEY'] = 'test-jwt-secret-key-for-medpulse-auth-testing'
        app.config['MAIL_USERNAME'] = 'test-sender@medpulse.com'
        
        self.client = app.test_client()
        self.base_url = "/api/v1/auth"
        
        # 準備共用的測試假資料 (配合全英文 data 環境)
        self.test_email = "test_email@example.com"
        self.test_username = "test_username"
        self.test_password = "secure_password123"
        self.test_code = "123456"

        # 生成測試 Profile 專用的 Token
        with app.app_context():
            self.token = create_access_token(identity="42")
        self.headers = {"Authorization": f"Bearer {self.token}"}

    # ====================================================================
    # 1. 測試：發送驗證碼 (POST /api/v1/auth/send-code)
    # ====================================================================
    @patch('app.routes.auth.mail')
    @patch('app.routes.auth.redis_client')
    def test_send_code_success(self, mock_redis, mock_mail):
        """測試：成功將驗證碼存入 Redis 並透過 SMTP 發送 Email"""
        mock_redis.setex.return_value = True
        mock_mail.send.return_value = True

        payload = {"email": self.test_email}
        response = self.client.post(f"{self.base_url}/send-code", json=payload)

        assert response.status_code == 200
        res_data = json.loads(response.data)
        assert res_data["message"] == "Verification code sent successfully"
        
        # 驗證 Redis 有確實呼叫 setex 且過期時間設為 300 秒
        called_args, _ = mock_redis.setex.call_args
        assert called_args[0] == f"verify:{self.test_email}"
        assert called_args[1] == 300

    # ====================================================================
    # 2. 測試：使用者註冊 (POST /api/v1/auth/register)
    # ====================================================================
    @patch('app.models.user.UserModel.create_user')
    @patch('app.models.user.UserModel.get_by_email')
    @patch('app.routes.auth.redis_client')
    def test_register_success(self, mock_redis, mock_get_email, mock_create_user):
        """測試：驗證碼正確且無重複 Email 時，成功註冊並簽發 JWT"""
        # 模擬 Redis 裡面有正確的驗證碼
        mock_redis.get.return_value = self.test_code
        mock_redis.delete.return_value = True
        
        # 模擬 Email 尚未被註冊過
        mock_get_email.return_value = None
        
        # 模擬資料庫寫入成功後的回傳用戶字典
        mock_create_user.return_value = {
            "id": 42,
            "username": self.test_username,
            "email": self.test_email
        }

        payload = {
            "username": self.test_username,
            "email": self.test_email,
            "password": self.test_password,
            "code": self.test_code
        }
        response = self.client.post(f"{self.base_url}/register", json=payload)

        assert response.status_code == 201
        res_data = json.loads(response.data)
        assert res_data["message"] == "User registered successfully"
        assert "access_token" in res_data
        assert res_data["user"]["id"] == 42

    @patch('app.routes.auth.redis_client')
    def test_register_invalid_code(self, mock_redis):
        """測試：當輸入錯誤或過期的驗證碼時，註冊應被攔截"""
        # 模擬 Redis 內部的驗證碼與使用者輸入的不符
        mock_redis.get.return_value = "999999"

        payload = {
            "username": self.test_username,
            "email": self.test_email,
            "password": self.test_password,
            "code": self.test_code  # 123456 != 999999
        }
        response = self.client.post(f"{self.base_url}/register", json=payload)

        assert response.status_code == 400
        res_data = json.loads(response.data)
        assert res_data["error"] == "Invalid or expired verification code"

    # ====================================================================
    # 3. 測試：使用者登入 (POST /api/v1/auth/login)
    # ====================================================================
    @patch('app.models.user.UserModel.verify_password')
    @patch('app.models.user.UserModel.get_by_email')
    def test_login_success(self, mock_get_email, mock_verify):
        """測試：輸入正確的帳密時，成功登入並取得 JWT"""
        # 模擬資料庫查到該用戶
        mock_get_email.return_value = {
            "id": 42,
            "username": self.test_username,
            "email": self.test_email,
            "password_hash": "mocked_hash_value"
        }
        # 模擬密碼密鑰比對成功
        mock_verify.return_value = True

        payload = {"email": self.test_email, "password": self.test_password}
        response = self.client.post(f"{self.base_url}/login", json=payload)

        assert response.status_code == 200
        res_data = json.loads(response.data)
        assert res_data["message"] == "Login successful"
        assert res_data["user"]["email"] == self.test_email
        assert "access_token" in res_data

    @patch('app.models.user.UserModel.get_by_email')
    def test_login_failed_user_not_found(self, mock_get_email):
        """測試：當 Email 不存在於系統中時，返回 401 登入失敗"""
        mock_get_email.return_value = None

        payload = {"email": "wrong@example.com", "password": self.test_password}
        response = self.client.post(f"{self.base_url}/login", json=payload)

        assert response.status_code == 401
        res_data = json.loads(response.data)
        assert "Invalid email or password" in res_data["error"]

    # ====================================================================
    # 4. 測試：個人 Profile 查詢 (GET /api/v1/auth/me)
    # ====================================================================
    def test_get_profile_success(self):
        """測試：帶上合法 Token 請求個人資訊時，應能成功解析身份識別"""
        response = self.client.get(f"{self.base_url}/me", headers=self.headers)
        
        assert response.status_code == 200
        res_data = json.loads(response.data)
        assert res_data["user_id"] == "42"
        assert res_data["status"] == "authenticated"

    # ====================================================================
    # 5. 測試：使用者登出與黑名單廢棄 (POST /api/v1/auth/logout)
    # ====================================================================
    @patch('app.routes.auth.redis_client')
    def test_logout_success(self, mock_redis):
        """測試：帶上合法 Token 請求登出時，系統應計算 Token 剩餘壽命並成功將 JTI 寫入 Redis 黑名單"""
        # 模擬 Redis 的 setex 操作成功
        mock_redis.setex.return_value = True

        # 發送登出請求（使用 setup_method 中生成的 self.headers）
        response = self.client.post(f"{self.base_url}/logout", headers=self.headers)

        # 1. 驗證回應狀態碼與內容
        assert response.status_code == 200
        res_data = json.loads(response.data)
        assert res_data["status"] == "success"
        assert "Successfully logged out" in res_data["message"]

        # 2. 驗證 Controller 內部是否有正確呼叫 redis_client.setex
        assert mock_redis.setex.called
        called_args, _ = mock_redis.setex.call_args
        
        # 檢查寫入 Redis 的 Key 格式是否為 blacklist:<jti>
        assert called_args[0].startswith("blacklist:")
        # 檢查存入的值是否為被廢棄的標記值 "revoked"
        assert called_args[2] == "revoked"