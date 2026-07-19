import json
import pytest
from unittest.mock import patch
from app import create_app

class TestFactCheckAPI:
    """闢謠專區 API 路由控制器的單元測試類別"""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """在每個測試方法執行前，自動初始化 Flask 測試客戶端"""
        app = create_app()
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.base_url = "/api/v1/fact-checks"

    # ====================================================================
    # 1. 測試：取得闢謠清單 (GET /api/v1/fact-checks)
    # ====================================================================
    @patch('app.utils.db.Database.execute_query')
    def test_get_fact_checks_success(self, mock_query):
        """測試成功獲取分頁與關鍵字篩選後的闢謠清單"""
        
        # 模擬 get_list() 內部的兩次資料庫連續查詢：
        # 第 1 次調用：count_query (回傳總筆數)
        # 第 2 次調用：base_query (回傳全英文的闢謠資料紀錄)
        mock_query.side_effect = [
            {"count": 1},  # 模擬總筆數 total_items
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

        # 發送 GET 請求，帶入英文關鍵字進行搜尋測試
        response = self.client.get(f"{self.base_url}?q=covid&page=1&limit=10")
        
        # 斷言驗證
        assert response.status_code == 200
        res_data = json.loads(response.data)
        
        assert res_data["status"] == "success"
        assert len(res_data["data"]) == 1
        assert "lemon water" in res_data["data"][0]["claim"]
        assert res_data["data"][0]["label"] == "FALSE"
        assert res_data["pagination"]["total_items"] == 1
        assert res_data["pagination"]["total_pages"] == 1

    # ====================================================================
    # 2. 測試：取得單篇闢謠詳情 - 成功 (GET /api/v1/fact-checks/<id>)
    # ====================================================================
    @patch('app.utils.db.Database.execute_query')
    def test_get_fact_check_detail_success(self, mock_query):
        """測試帶入正確的整數 ID 能成功返回單篇闢謠的詳細內容"""
        
        # 模擬 get_by_id() 的資料庫回傳值
        mock_query.return_value = {
            "id": 101,
            "claim": "Drinking lemon water cures COVID-19 within 24 hours.",
            "explanation": "There is no scientific evidence that lemon water eliminates the coronavirus.",
            "label": "FALSE",
            "claim_url": "https://example.com/hoax-lemon",
            "main_text": "A viral social media post claims...",
            "sources": "World Health Organization (WHO), CDC"
        }

        # 路由有嚴格的 <int:item_id> 限制，傳入整數 101
        response = self.client.get(f"{self.base_url}/101")
        
        assert response.status_code == 200
        res_data = json.loads(response.data)
        assert res_data["status"] == "success"
        assert res_data["data"]["id"] == 101
        assert res_data["data"]["label"] == "FALSE"

    # ====================================================================
    # 3. 測試：取得單篇闢謠詳情 - 查無此資料 (GET /api/v1/fact-checks/<id>)
    # ====================================================================
    @patch('app.utils.db.Database.execute_query')
    def test_get_fact_check_detail_not_found(self, mock_query):
        """測試當傳入不存在的 ID 時，系統能優雅地返回 404 錯誤回應"""
        
        # 模擬當資料庫找不到該 ID 時回傳 None 的情境
        mock_query.return_value = None

        response = self.client.get(f"{self.base_url}/9999")
        
        assert response.status_code == 404
        res_data = json.loads(response.data)
        assert "error" in res_data
        assert res_data["error"] == "Fact check item not found"