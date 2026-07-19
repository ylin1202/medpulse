import json
import pytest
from unittest.mock import patch
from app import create_app


# ====================================================================
# Pharmacies in Taiwan (the only Chinese dataset in the system) stored in the database.
# ====================================================================


class TestPharmacyAPI:
    """藥局資料 API 路由控制器的單元測試類別 (中文資料集專用)"""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """在每個測試方法執行前，自動初始化 Flask 測試客戶端"""
        app = create_app()
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.base_url = "/api/v1/pharmacies"

    # ====================================================================
    # 1. 測試：取得全量藥局清單 - 無篩選條件 (GET /api/v1/pharmacies)
    # ====================================================================
    @patch('app.utils.db.Database.execute_query')
    def test_get_pharmacies_all_success(self, mock_query):
        """測試：當不帶任何 query 參數時，能成功回傳完整的中文藥局列表"""
        
        # 模擬資料庫撈回的真實中文藥局紀錄
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
                "longitude": 121.5324
            }
        ]

        response = self.client.get(self.base_url)
        
        # 斷言驗證
        assert response.status_code == 200
        res_data = json.loads(response.data)
        
        assert res_data["status"] == "success"
        assert res_data["count"] == 1
        assert len(res_data["data"]) == 1
        assert res_data["data"][0]["name"] == "祥全健保藥局"
        assert res_data["data"][0]["city"] == "臺北市"

    # ====================================================================
    # 2. 測試：帶中文條件篩選藥局 (GET /api/v1/pharmacies?q=祥全&city=臺北市)
    # ====================================================================
    @patch('app.utils.db.Database.execute_query')
    def test_get_pharmacies_with_filters_success(self, mock_query):
        """測試：當帶入中文關鍵字 q 與縣市 city 篩選時，系統能正確調用並回傳過濾結果"""
        
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
                "longitude": 121.5324
            }
        ]

        # 傳入中文的 query params (Flask test client 會自動處理 URL 編碼)
        url = f"{self.base_url}?q=祥全&city=臺北市"
        response = self.client.get(url)
        
        assert response.status_code == 200
        res_data = json.loads(response.data)
        assert res_data["status"] == "success"
        assert res_data["count"] == 1
        
        # 驗證 Model 內部的 Database.execute_query 是否有拿到正確的中文參數防禦
        # 呼叫參數會儲存在 called_kwargs["params"] 中
        called_args, called_kwargs = mock_query.call_args
        assert "%祥全%" in called_kwargs["params"]
        assert "臺北市" in called_kwargs["params"]

    # ====================================================================
    # 3. 測試：資料庫異常保護 (Error Handling)
    # ====================================================================
    @patch('app.utils.cache.CacheService.get')  # 新增：Mock 快取服務
    @patch('app.utils.db.Database.execute_query')
    def test_get_pharmacies_database_error(self, mock_query, mock_cache_get):
        """測試：當資料庫查詢噴出強烈異常時，控制器應能捕捉並回應 500 狀態碼"""
        
        # 1. 強制讓快取未命中 (Cache Miss)，逼迫系統一定要往下走去查資料庫
        mock_cache_get.return_value = None
        
        # 2. 強制讓資料庫拋出 Exception
        mock_query.side_effect = Exception("OperationalError: Connection timed out.")

        response = self.client.get(self.base_url)
        
        # 3. 驗證斷言
        assert response.status_code == 500
        res_data = json.loads(response.data)
        assert "error" in res_data
        assert "Failed to fetch pharmacies" in res_data["error"]