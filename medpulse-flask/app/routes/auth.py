from datetime import datetime, timezone
import random
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity, jwt_required
from flask_mail import Message

from app.extensions import mail
from app.models.user import UserModel
from app.utils.cache import CacheService
from app.utils.limiter import limiter

# Initialize JWT Authentication Blueprint
auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

# Shared Redis client instance and connection pool from CacheService
redis_client = CacheService.get_client()


class AuthController:
    """Controller handling user authentication, verification codes, and session lifecycles."""

    # Rate limit: 3 requests per minute per IP to prevent spamming the SMTP server
    @limiter.limit("3 per minute")
    @staticmethod
    def send_code():
        """Send a 6-digit email verification code via SMTP."""
        data = request.get_json() or {}
        email = data.get("email")

        if not email:
            return jsonify({"error": "Email is required"}), 400

        # Generate a 6-digit one-time password (OTP)
        code = f"{random.randint(100000, 999999)}"

        try:
            # Store OTP in Redis with a 5-minute TTL (300 seconds)
            redis_client.setex(f"verify:{email}", 300, code)

            # Dispatch verification email via SMTP
            msg = Message(
                subject="[MedPulse] Your Registration Verification Code",
                sender=current_app.config.get("MAIL_USERNAME"),
                recipients=[email],
                body=(
                    f"Hello!\n\n"
                    f"Your verification code for MedPulse is: {code}\n\n"
                    f"This code will expire in 5 minutes."
                ),
            )
            mail.send(msg)

            return jsonify({"message": "Verification code sent successfully"}), 200

        except Exception as e:
            return jsonify({"error": f"Failed to send email: {str(e)}"}), 500

    # Rate limit: 5 registration attempts per minute per IP to prevent brute-force attacks
    @limiter.limit("5 per minute")
    @staticmethod
    def register():
        """Register a new user account upon valid OTP code verification."""
        data = request.get_json() or {}
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")
        code = data.get("code")

        # Payload validation
        if not username or not email or not password or not code:
            return jsonify({"error": "Missing required fields: username, email, password, code"}), 400

        # Verify OTP code against cached Redis entry
        saved_code = redis_client.get(f"verify:{email}")
        if not saved_code or saved_code != str(code):
            return jsonify({"error": "Invalid or expired verification code"}), 400

        # Ensure email uniqueness
        existing_user = UserModel.get_by_email(email)
        if existing_user:
            return jsonify({"error": "Email is already registered"}), 409

        try:
            # Delete cached OTP immediately to prevent replay attacks
            redis_client.delete(f"verify:{email}")

            # Persist user (UserModel handles cryptographic password hashing)
            new_user = UserModel.create_user(username, email, password)

            # Issue JWT access token
            access_token = create_access_token(identity=str(new_user["id"]))

            return jsonify({
                "message": "User registered successfully",
                "user": {
                    "id": new_user["id"],
                    "username": new_user["username"],
                    "email": new_user["email"],
                },
                "access_token": access_token,
            }), 201

        except Exception as e:
            return jsonify({"error": f"Failed to register user: {str(e)}"}), 500

    # Rate limit: 5 login attempts per minute per IP
    @limiter.limit("5 per minute")
    @staticmethod
    def login():
        """Authenticate user credentials and issue an access token."""
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
                "email": user["email"],
            },
            "access_token": access_token,
        }), 200

    @staticmethod
    @jwt_required()
    def logout():
        """Revoke current JWT by adding its unique token ID (JTI) to Redis blocklist."""
        try:
            # Extract JWT claims from request header
            jwt_data = get_jwt()
            jti = jwt_data["jti"]

            # Calculate remaining token lifespan (TTL) in seconds
            now = datetime.now(timezone.utc).timestamp()
            remains = max(int(jwt_data["exp"] - now), 1)

            # Store revoked token ID in Redis with matching TTL
            redis_client.setex(f"blacklist:{jti}", remains, "revoked")

            return jsonify({
                "status": "success",
                "message": "Successfully logged out. Token has been revoked.",
            }), 200

        except Exception as e:
            return jsonify({"error": f"Logout failed: {str(e)}"}), 500

    @staticmethod
    @jwt_required()
    def get_profile():
        """Retrieve authenticated user identity from Bearer token."""
        current_user_id = get_jwt_identity()
        return jsonify({
            "user_id": current_user_id,
            "status": "authenticated",
        }), 200


# Endpoint Route Bindings
auth_bp.route("/send-code", methods=["POST"])(AuthController.send_code)
auth_bp.route("/register", methods=["POST"])(AuthController.register)
auth_bp.route("/login", methods=["POST"])(AuthController.login)
auth_bp.route("/logout", methods=["POST"])(AuthController.logout)
auth_bp.route("/me", methods=["GET"])(AuthController.get_profile)