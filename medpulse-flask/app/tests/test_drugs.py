import json
import pytest
from unittest.mock import patch
from app import create_app

class TestDrugAPI:
    """封裝藥品搜尋與詳情 API (Read) 的類別架構測試"""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """在每個測試方法執行前初始化 Flask 測試客戶端"""
        app = create_app()
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.base_url = "/api/v1/drugs"

    # ====================================================================
    # 1. 測試：取得藥品清單 (GET /api/v1/drugs)
    # ====================================================================
    @patch('app.utils.db.Database.execute_query')
    def test_get_drugs_success(self, mock_query):
        """測試：當資料庫有資料時，正確回傳藥品清單與分頁資訊"""
        
        # 模擬 Database.execute_query 的兩次觸發回傳值
        # 第一次 (Count 查詢): 回傳總筆數
        # 第二次 (List 分頁查詢): 回傳藥品陣列
        mock_query.side_effect = [
            {"count": 1},  # 總筆數
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

        # 發送 GET 請求，並帶上查詢參數
        response = self.client.get(f"{self.base_url}?q=minoxidil&page=1&limit=10")
        
        # 斷言驗證
        assert response.status_code == 200
        res_data = json.loads(response.data)
        
        assert res_data["status"] == "success"
        assert len(res_data["data"]) == 1
        assert res_data["data"][0]["brand_name"] == "Minoxidil 5%"
        assert res_data["pagination"]["total_items"] == 1
        assert res_data["pagination"]["total_pages"] == 1

    # ====================================================================
    # 2. 測試：取得特定藥品詳情 - 成功案例 (GET /api/v1/drugs/<id>)
    # ====================================================================
    @patch('app.utils.db.Database.execute_query')
    def test_get_drug_detail_success(self, mock_query):
        """測試：輸入正確的 drug_id 時，應回傳 200 與完整說明書內容"""
        
        # 模擬單一藥品的完整欄位 (SELECT * FROM drugs)
        mock_query.return_return = {
            "id": "drug-xyz",
            "brand_name": "Aspirin",
            "description": "Pain reliever",
            "dosage_and_administration": "Take 1 tablet daily"
        }
        mock_query.return_value = mock_query.return_return  # 綁定 mock 回傳值

        response = self.client.get(f"{self.base_url}/drug-xyz")
        
        assert response.status_code == 200
        res_data = json.loads(response.data)
        assert res_data["status"] == "success"
        assert res_data["data"]["id"] == "drug-xyz"
        assert res_data["data"]["brand_name"] == "Aspirin"

    # ====================================================================
    # 3. 測試：取得特定藥品詳情 - 查無此藥 (GET /api/v1/drugs/<id>)
    # ====================================================================
    @patch('app.utils.db.Database.execute_query')
    def test_get_drug_detail_not_found(self, mock_query):
        """測試：當輸入不存在的 drug_id 時，應優雅回傳 404 Error"""
        
        # 模擬資料庫查無此資料，回傳 None
        mock_query.return_value = None

        response = self.client.get(f"{self.base_url}/non-existent-id")
        
        assert response.status_code == 404
        res_data = json.loads(response.data)
        assert "error" in res_data
        assert res_data["error"] == "Drug not found"