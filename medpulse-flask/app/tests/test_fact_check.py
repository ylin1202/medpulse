import json
from unittest.mock import patch
import pytest

from app import create_app


class TestFactCheckAPI:
    """Unit test suite for public health fact-checking API route controllers."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Automatically initialize Flask test client and configuration prior to each test case."""
        app = create_app()
        app.config['TESTING'] = True
        app.config["RATELIMIT_ENABLED"] = False
        self.client = app.test_client()
        self.base_url = "/api/v1/fact-checks"

    # Fetch Paginated Fact Checks (GET /api/v1/fact-checks)
    @patch('app.utils.cache.CacheService.get', return_value=None)
    @patch('app.utils.db.Database.execute_query')
    def test_get_fact_checks_success(self, mock_query, mock_cache_get):
        """Test successful retrieval of paginated and filtered fact checks on cache miss."""
        # Mock sequential execute_query invocations from DAO:
        # Call 1: count_query (returns total matching records)
        # Call 2: base_query (returns list of fact-checking records)
        mock_query.side_effect = [
            {"count": 1},
            [{
                "id": 101,
                "claim": "Drinking lemon water cures COVID-19 within 24 hours.",
                "explanation": "There is no scientific evidence that lemon water eliminates the coronavirus.",
                "label": "FALSE",
                "claim_url": "https://example.com/hoax-lemon",
                "main_text": "A viral social media post claims...",
                "sources": "World Health Organization (WHO), CDC"
            }]
        ]

        # Dispatch GET request with search query parameters
        response = self.client.get(f"{self.base_url}?q=covid&page=1&limit=10")

        # Assert response status and schema validation
        assert response.status_code == 200
        res_data = json.loads(response.data)

        assert res_data["status"] == "success"
        assert len(res_data["data"]) == 1
        assert "lemon water" in res_data["data"][0]["claim"]
        assert res_data["data"][0]["label"] == "FALSE"
        assert res_data["pagination"]["total_items"] == 1
        assert res_data["pagination"]["total_pages"] == 1

    # Fetch Single Fact Check Details - Success (GET /api/v1/fact-checks/<id>)
    @patch('app.utils.cache.CacheService.get', return_value=None)
    @patch('app.utils.db.Database.execute_query')
    def test_get_fact_check_detail_success(self, mock_query, mock_cache_get):
        """Test successful retrieval of detailed fact-check record by ID."""
        mock_query.return_value = {
            "id": 101,
            "claim": "Drinking lemon water cures COVID-19 within 24 hours.",
            "explanation": "There is no scientific evidence that lemon water eliminates the coronavirus.",
            "label": "FALSE",
            "claim_url": "https://example.com/hoax-lemon",
            "main_text": "A viral social media post claims...",
            "sources": "World Health Organization (WHO), CDC"
        }

        # Dispatch GET request with integer resource ID
        response = self.client.get(f"{self.base_url}/101")

        assert response.status_code == 200
        res_data = json.loads(response.data)
        assert res_data["status"] == "success"
        assert res_data["data"]["id"] == 101
        assert res_data["data"]["label"] == "FALSE"

    # Fetch Single Fact Check Details - Not Found (GET /api/v1/fact-checks/<id>)
    @patch('app.utils.cache.CacheService.get', return_value=None)
    @patch('app.utils.db.Database.execute_query')
    def test_get_fact_check_detail_not_found(self, mock_query, mock_cache_get):
        """Test graceful HTTP 404 response handling when querying a non-existent record ID."""
        # Mock database returning None for missing record
        mock_query.return_value = None

        response = self.client.get(f"{self.base_url}/9999")

        assert response.status_code == 404
        res_data = json.loads(response.data)
        assert "error" in res_data
        assert res_data["error"] == "Fact check item not found"