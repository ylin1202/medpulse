import json
from unittest.mock import MagicMock, patch
from flask_jwt_extended import create_access_token
import pytest

from app import create_app


class TestAuthAPI:
    """Unit test suite for authentication and user registration API route controllers."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Automatically initialize Flask test client, generate tokens, and set test fixtures."""
        app = create_app()
        app.config['TESTING'] = True
        app.config["RATELIMIT_ENABLED"] = False
        app.config['JWT_SECRET_KEY'] = 'test-jwt-secret-key-for-medpulse-auth-testing'
        app.config['MAIL_USERNAME'] = 'test-sender@medpulse.com'

        self.client = app.test_client()
        self.base_url = "/api/v1/auth"

        # Shared mock credentials and test payload
        self.test_email = "test_email@example.com"
        self.test_username = "test_username"
        self.test_password = "secure_password123"
        self.test_code = "123456"

        # Generate test JWT for profile-authenticated requests
        with app.app_context():
            self.token = create_access_token(identity="42")
        self.headers = {"Authorization": f"Bearer {self.token}"}

    # 1. Send OTP Verification Code (POST /api/v1/auth/send-code)
    @patch('app.routes.auth.mail')
    @patch('app.routes.auth.redis_client')
    def test_send_code_success(self, mock_redis, mock_mail):
        """Test successful storage of OTP in Redis and dispatch via SMTP."""
        mock_redis.setex.return_value = True
        mock_mail.send.return_value = True

        payload = {"email": self.test_email}
        response = self.client.post(f"{self.base_url}/send-code", json=payload)

        assert response.status_code == 200
        res_data = json.loads(response.data)
        assert res_data["message"] == "Verification code sent successfully"

        # Verify Redis setex is invoked with 300s TTL
        called_args, _ = mock_redis.setex.call_args
        assert called_args[0] == f"verify:{self.test_email}"
        assert called_args[1] == 300

    # 2. User Registration (POST /api/v1/auth/register)
    @patch('app.models.user.UserModel.create_user')
    @patch('app.models.user.UserModel.get_by_email')
    @patch('app.routes.auth.redis_client')
    def test_register_success(self, mock_redis, mock_get_email, mock_create_user):
        """Test successful registration and token issuance upon valid OTP verification."""
        # Mock Redis returning matching OTP
        mock_redis.get.return_value = self.test_code
        mock_redis.delete.return_value = True

        # Mock unregistered email
        mock_get_email.return_value = None

        # Mock database insertion returning user dict
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
        """Test registration rejection when an invalid or expired OTP is supplied."""
        # Mock Redis returning non-matching OTP
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

    # 3. User Login (POST /api/v1/auth/login)
    @patch('app.models.user.UserModel.verify_password')
    @patch('app.models.user.UserModel.get_by_email')
    def test_login_success(self, mock_get_email, mock_verify):
        """Test successful authentication and token return with valid credentials."""
        # Mock existing user record
        mock_get_email.return_value = {
            "id": 42,
            "username": self.test_username,
            "email": self.test_email,
            "password_hash": "mocked_hash_value"
        }
        # Mock valid password verification
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
        """Test authentication rejection (HTTP 401) when user email does not exist."""
        mock_get_email.return_value = None

        payload = {"email": "wrong@example.com", "password": self.test_password}
        response = self.client.post(f"{self.base_url}/login", json=payload)

        assert response.status_code == 401
        res_data = json.loads(response.data)
        assert "Invalid email or password" in res_data["error"]

    # 4. User Profile Inspection (GET /api/v1/auth/me)
    def test_get_profile_success(self):
        """Test identity resolution from valid Bearer JWT header."""
        response = self.client.get(f"{self.base_url}/me", headers=self.headers)

        assert response.status_code == 200
        res_data = json.loads(response.data)
        assert res_data["user_id"] == "42"
        assert res_data["status"] == "authenticated"

    # 5. User Logout & Token Revocation (POST /api/v1/auth/logout)
    @patch('app.routes.auth.redis_client')
    def test_logout_success(self, mock_redis):
        """Test token revocation by calculating remaining TTL and storing JTI in Redis blocklist."""
        # Mock successful Redis setex operation
        mock_redis.setex.return_value = True

        # Dispatch logout request using authorized headers
        response = self.client.post(f"{self.base_url}/logout", headers=self.headers)

        # Verify response status code and payload structure
        assert response.status_code == 200
        res_data = json.loads(response.data)
        assert res_data["status"] == "success"
        assert "Successfully logged out" in res_data["message"]

        # Assert Redis blocklist invocation
        assert mock_redis.setex.called
        called_args, _ = mock_redis.setex.call_args

        # Ensure key structure follows blacklist:<jti> format and is marked as revoked
        assert called_args[0].startswith("blacklist:")
        assert called_args[2] == "revoked"