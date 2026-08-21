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

# Import route blueprints
from app.routes.auth import auth_bp
from app.routes.fact_check import fact_check_bp
from app.routes.drug import drug_bp
from app.routes.favorite import favorite_bp
from app.routes.pharmacy import pharmacy_bp


def create_app():
    """Application factory for configuring and initializing the Flask application."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Enable JWT blocklist verification
    app.config["JWT_BLACKLIST_ENABLED"] = True
    app.config["JWT_BLACKLIST_TOKEN_CHECKS"] = ["access", "refresh"]

    # Enable Cross-Origin Resource Sharing (CORS)
    CORS(app)

    # Initialize JWT manager
    jwt = JWTManager(app)
    
    # Initialize Flask-Mail for SMTP communication
    mail.init_app(app)

    # Register distributed rate limiter
    limiter.init_app(app)

    # Initialize PostgreSQL connection pool
    Database.init_pool(app)

    # Release database connection back to the pool upon request teardown
    app.teardown_appcontext(Database.release_conn)

    # Register routing blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(fact_check_bp)
    app.register_blueprint(drug_bp)
    app.register_blueprint(favorite_bp)
    app.register_blueprint(pharmacy_bp)
    
    # Health check endpoint
    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "MedPulse Flask Core API",
            "version": "1.0.0"
        }), 200

    # Auto-initialize database tables on application bootstrap
    with app.app_context():
        try:
            UserModel.create_table()
            FavoriteModel.create_table()
            print("Database connection pool initialized & User/Favorite tables checked.")
        except Exception as e:
            print(f"Database initialization skipped or failed: {e}")
    
    # Custom error handler for HTTP 429 Too Many Requests
    @app.errorhandler(RateLimitExceeded)
    def ratelimit_handler(e):
        return jsonify({
            "status": "fail",
            "error": "Too Many Requests",
            "message": f"You have exceeded your request limit. Please try again later. Details: {e.description}"
        }), 429

    # JWT blocklist verification callback
    @jwt.token_in_blocklist_loader
    def check_if_token_is_revoked(jwt_header, jwt_payload: dict):
        """
        Callback invoked by Flask-JWT-Extended on protected endpoints (@jwt_required())
        to verify whether the given JWT has been revoked/blacklisted.
        """
        try:
            # Extract unique JWT identifier (JTI)
            jti = jwt_payload["jti"]
            
            # Obtain shared Redis client instance
            redis_client = CacheService.get_client()
            
            # Check for revoked token presence in Redis
            token_in_redis = redis_client.get(f"blacklist:{jti}")
            
            # Return True to deny access if token exists in blocklist
            return token_in_redis is not None
            
        except Exception:
            # Defensive fallback: allow request if Redis lookup fails to preserve system availability
            return False

    return app