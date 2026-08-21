import json
from unittest.mock import patch
import pytest

from app import create_app


# ====================================================================
# Pharmacies in Taiwan (the only Chinese dataset in the system) stored in the database.
# ====================================================================


class TestPharmacyAPI:
    """Unit test suite for pharmacy listings, geolocation queries, and regional filter API endpoints."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Automatically initialize Flask test client and test configuration before each test case."""
        app = create_app()
        app.config['TESTING'] = True
        app.config["RATELIMIT_ENABLED"] = False
        self.client = app.test_client()
        self.base_url = "/api/v1/pharmacies"

    # Fetch Complete Pharmacy Catalog - No Filters (GET /api/v1/pharmacies)
    @patch('app.utils.cache.CacheService.get', return_value=None)
    @patch('app.utils.db.Database.execute_query')
    def test_get_pharmacies_all_success(self, mock_query, mock_cache_get):
        """Test successful retrieval of complete pharmacy directory without query parameters on cache miss."""
        # Mock database returning contracted pharmacy record
        mock_query.return_value = [
            {
                "id": 1,
                "name": "祥全健保藥局",
                "status": "營業中",
                "city": "臺北市",
                "district": "中山區",
                "address": "臺北市中山區長安東路二段123號",
                "phone": "02-12345678",
                "is_nhi_contracted": True,
                "latitude": 25.0478,
                "longitude": 121.5324,
            }
        ]

        response = self.client.get(self.base_url)

        assert response.status_code == 200
        res_data = json.loads(response.data)

        assert res_data["status"] == "success"
        assert res_data["count"] == 1
        assert len(res_data["data"]) == 1
        assert res_data["data"][0]["name"] == "祥全健保藥局"
        assert res_data["data"][0]["city"] == "臺北市"

    # Filter Pharmacies by Keyword and City (GET /api/v1/pharmacies?q=祥全&city=臺北市)
    @patch('app.utils.cache.CacheService.get', return_value=None)
    @patch('app.utils.db.Database.execute_query')
    def test_get_pharmacies_with_filters_success(self, mock_query, mock_cache_get):
        """Test query routing and SQL parameter injection with localized search keywords and administrative city filters."""
        mock_query.return_value = [
            {
                "id": 1,
                "name": "祥全健保藥局",
                "status": "營業中",
                "city": "臺北市",
                "district": "中山區",
                "address": "臺北市中山區長安東路二段123號",
                "phone": "02-12345678",
                "is_nhi_contracted": True,
                "latitude": 25.0478,
                "longitude": 121.5324,
            }
        ]

        # Dispatch GET request with URL-encoded query parameters
        url = f"{self.base_url}?q=祥全&city=臺北市"
        response = self.client.get(url)

        assert response.status_code == 200
        res_data = json.loads(response.data)
        assert res_data["status"] == "success"
        assert res_data["count"] == 1

        called_args, called_kwargs = mock_query.call_args
        assert "%祥全%" in called_kwargs["params"]
        assert "臺北市" in called_kwargs["params"]

    # Database Exception & Error Handling (GET /api/v1/pharmacies)
    @patch('app.utils.cache.CacheService.get', return_value=None)
    @patch('app.utils.db.Database.execute_query')
    def test_get_pharmacies_database_error(self, mock_query, mock_cache_get):
        """Test graceful HTTP 500 error handling when database execution encounters a connection timeout."""
        mock_query.side_effect = Exception("OperationalError: Connection timed out.")

        response = self.client.get(self.base_url)

        assert response.status_code == 500
        res_data = json.loads(response.data)
        assert "error" in res_data
        assert "Failed to fetch pharmacies" in res_data["error"]