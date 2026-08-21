import json
from unittest.mock import patch
from flask_jwt_extended import create_access_token
import pytest

from app import create_app


class TestFavoriteAPI:
    """Unit test suite for medication bookmarking and favorites API route controllers."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Initialize Flask test client, generate tokens, and configure shared fixtures before each test."""
        app = create_app()
        app.config['TESTING'] = True
        app.config["RATELIMIT_ENABLED"] = False
        app.config['JWT_SECRET_KEY'] = 'test-jwt-secret-key-for-medpulse-testing-32bytes'

        self.client = app.test_client()
        self.base_url = "/api/v1/favorites"

        self.mock_user_id = 42
        self.mock_drug_id = 99

        # Generate a valid JWT token within the application context
        with app.app_context():
            self.token = create_access_token(identity=str(self.mock_user_id))

        # Shared Bearer token authorization header
        self.headers = {
            "Authorization": f"Bearer {self.token}"
        }

    # Add Favorite Medication (POST /api/v1/favorites)
    @patch('app.routes.favorite.get_jwt_identity')
    @patch('app.utils.db.Database.execute_query')
    def test_add_favorite_success(self, mock_query, mock_jwt):
        """Test adding a drug to favorites with valid drug_id and authorization token."""
        mock_jwt.return_value = str(self.mock_user_id)
        mock_query.return_value = {
            "id": 1,
            "user_id": self.mock_user_id,
            "drug_id": self.mock_drug_id,
            "created_at": "2026-07-20 02:22:42"
        }

        payload = {"drug_id": self.mock_drug_id}
        response = self.client.post(self.base_url, json=payload, headers=self.headers)

        assert response.status_code == 201
        res_data = json.loads(response.data)
        assert res_data["status"] == "success"
        assert res_data["data"]["drug_id"] == self.mock_drug_id

    @patch('app.routes.favorite.get_jwt_identity')
    def test_add_favorite_missing_id(self, mock_jwt):
        """Test rejection (HTTP 400) when drug_id is missing from request payload."""
        mock_jwt.return_value = str(self.mock_user_id)

        response = self.client.post(self.base_url, json={}, headers=self.headers)

        assert response.status_code == 400
        res_data = json.loads(response.data)
        assert res_data["error"] == "Missing drug_id"

    # Remove Favorite Medication (DELETE /api/v1/favorites/<drug_id>)
    @patch('app.routes.favorite.get_jwt_identity')
    @patch('app.utils.db.Database.execute_query')
    def test_remove_favorite_success(self, mock_query, mock_jwt):
        """Test successful removal of a favorited medication for the authenticated user."""
        mock_jwt.return_value = str(self.mock_user_id)
        mock_query.return_value = None

        response = self.client.delete(f"{self.base_url}/{self.mock_drug_id}", headers=self.headers)

        assert response.status_code == 200
        res_data = json.loads(response.data)
        assert res_data["status"] == "success"
        assert str(self.mock_drug_id) in res_data["message"]

    # Check Favorite Status (GET /api/v1/favorites/check/<drug_id>)
    @pytest.mark.parametrize("db_return, expected_status", [
        ({"1": 1}, True),
        (None, False)
    ])
    @patch('app.routes.favorite.get_jwt_identity')
    @patch('app.utils.db.Database.execute_query')
    def test_check_favorite_status(self, mock_query, mock_jwt, db_return, expected_status):
        """Parametrized test verifying status resolution for both favorited and non-favorited drugs."""
        mock_jwt.return_value = str(self.mock_user_id)
        mock_query.return_value = db_return

        response = self.client.get(f"{self.base_url}/check/{self.mock_drug_id}", headers=self.headers)

        assert response.status_code == 200
        res_data = json.loads(response.data)
        assert res_data["is_favorited"] == expected_status

    # Fetch User Favorites (GET /api/v1/favorites)
    @patch('app.routes.favorite.get_jwt_identity')
    @patch('app.utils.db.Database.execute_query')
    def test_get_favorites_success(self, mock_query, mock_jwt):
        """Test retrieving complete joined list of favorited drugs for the authenticated user."""
        mock_jwt.return_value = str(self.mock_user_id)
        mock_query.return_value = [
            {
                "favorite_id": 1,
                "favorited_at": "2026-07-20 02:22:42",
                "drug_id": self.mock_drug_id,
                "brand_name": "Advils Fast Relief",
                "generic_name": "Ibuprofen",
                "manufacturer_name": "Pfizer Inc.",
                "purpose": "Pain Reliever / Fever Reducer",
                "indications_and_usage": "For temporary relief of minor aches and pains..."
            }
        ]

        response = self.client.get(self.base_url, headers=self.headers)

        assert response.status_code == 200
        res_data = json.loads(response.data)
        assert res_data["status"] == "success"
        assert len(res_data["favorites"]) == 1
        assert res_data["favorites"][0]["brand_name"] == "Advils Fast Relief"

    # Error Handling & Database Exceptions
    @patch('app.routes.favorite.get_jwt_identity')
    @patch('app.utils.db.Database.execute_query')
    def test_add_favorite_database_error(self, mock_query, mock_jwt):
        """Test proper HTTP 500 error handling when a database exception occurs."""
        mock_jwt.return_value = str(self.mock_user_id)
        mock_query.side_effect = Exception("Database connection failed")

        payload = {"drug_id": self.mock_drug_id}
        response = self.client.post(self.base_url, json=payload, headers=self.headers)

        assert response.status_code == 500
        res_data = json.loads(response.data)
        assert "error" in res_data
        assert "Failed to add favorite" in res_data["error"]