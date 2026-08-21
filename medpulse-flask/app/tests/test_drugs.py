import json
from unittest.mock import patch
import pytest

from app import create_app


class TestDrugAPI:
    """Unit test suite for drug search, catalog queries, and details API endpoints."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Initialize Flask test client and configuration prior to each test case."""
        app = create_app()
        app.config['TESTING'] = True
        app.config["RATELIMIT_ENABLED"] = False
        self.client = app.test_client()
        self.base_url = "/api/v1/drugs"

    # Fetch Paginated Drug Catalog (GET /api/v1/drugs)
    @patch('app.utils.cache.CacheService.get', return_value=None)
    @patch('app.utils.db.Database.execute_query')
    def test_get_drugs_success(self, mock_query, mock_cache_get):
        """Test successful retrieval of paginated drug records and metadata on cache miss."""
        # Mock sequential execute_query invocations:
        # First call (Count query): returns total records matching criteria
        # Second call (Paginated query): returns list of drug records
        mock_query.side_effect = [
            {"count": 1},
            [{
                "id": "drug-abc",
                "brand_name": "Minoxidil 5%",
                "generic_name": "Minoxidil",
                "manufacturer_name": "MedPulse Lab",
                "product_type": "HUMAN OTC DRUG",
                "route": "TOPICAL",
                "active_ingredient": "Minoxidil",
                "purpose": "Hair Regrowth",
                "boxed_warning": None
            }]
        ]

        # Dispatch GET request with search parameters
        response = self.client.get(f"{self.base_url}?q=minoxidil&page=1&limit=10")

        # Assert response status and schema integrity
        assert response.status_code == 200
        res_data = json.loads(response.data)

        assert res_data["status"] == "success"
        assert len(res_data["data"]) == 1
        assert res_data["data"][0]["brand_name"] == "Minoxidil 5%"
        assert res_data["pagination"]["total_items"] == 1
        assert res_data["pagination"]["total_pages"] == 1

    # Fetch Single Drug Package Insert Details - Success (GET /api/v1/drugs/<id>)
    @patch('app.utils.cache.CacheService.get', return_value=None)
    @patch('app.utils.db.Database.execute_query')
    def test_get_drug_detail_success(self, mock_query, mock_cache_get):
        """Test successful package insert retrieval for a valid drug ID."""
        mock_query.return_value = {
            "id": "drug-xyz",
            "brand_name": "Aspirin",
            "description": "Pain reliever",
            "dosage_and_administration": "Take 1 tablet daily"
        }

        response = self.client.get(f"{self.base_url}/drug-xyz")

        assert response.status_code == 200
        res_data = json.loads(response.data)
        assert res_data["status"] == "success"
        assert res_data["data"]["id"] == "drug-xyz"
        assert res_data["data"]["brand_name"] == "Aspirin"

    # Fetch Single Drug Package Insert Details - Not Found (GET /api/v1/drugs/<id>)
    @patch('app.utils.cache.CacheService.get', return_value=None)
    @patch('app.utils.db.Database.execute_query')
    def test_get_drug_detail_not_found(self, mock_query, mock_cache_get):
        """Test proper HTTP 404 response handling when querying a non-existent drug ID."""
        # Mock database query returning no matching record
        mock_query.return_value = None

        response = self.client.get(f"{self.base_url}/non-existent-id")

        assert response.status_code == 404
        res_data = json.loads(response.data)
        assert "error" in res_data
        assert res_data["error"] == "Drug not found"