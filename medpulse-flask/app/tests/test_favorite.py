import json
import pytest
from unittest.mock import patch
from app import create_app
from flask_jwt_extended import create_access_token

class TestFavoriteAPI:
    """使用者藥品收藏夾 API 路由控制器的單元測試類別"""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """在每個測試方法執行前，自動初始化 Flask 測試客戶端、生成 Token 與共用變數"""
        app = create_app()
        app.config['TESTING'] = True
        app.config['JWT_SECRET_KEY'] = 'test-jwt-secret-key-for-medpulse-testing-32bytes'
        
        self.client = app.test_client()
        self.base_url = "/api/v1/favorites"
        
        self.mock_user_id = 42
        self.mock_drug_id = 99

        # 在 app 上下文中生成一個測試專用的真實 JWT Token
        with app.app_context():
            self.token = create_access_token(identity=str(self.mock_user_id))
            
        # 建立共用帶有 Bearer Token 的 Headers 字典
        self.headers = {
            "Authorization": f"Bearer {self.token}"
        }

    # ====================================================================
    # 1. 測試：新增藥品收藏 (POST /api/v1/favorites)
    # ====================================================================
    @patch('app.routes.favorite.get_jwt_identity')
    @patch('app.utils.db.Database.execute_query')
    def test_add_favorite_success(self, mock_query, mock_jwt):
        """測試：當傳入正確的 drug_id 且帶有合法 Token 時，成功建立收藏"""
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
        """測試：當請求遺漏 drug_id 時，系統應攔截並回傳 400 錯誤"""
        mock_jwt.return_value = str(self.mock_user_id)
        
        response = self.client.post(self.base_url, json={}, headers=self.headers)
        
        assert response.status_code == 400
        res_data = json.loads(response.data)
        assert res_data["error"] == "Missing drug_id"

    # ====================================================================
    # 2. 測試：取消藥品收藏 (DELETE /api/v1/favorites/<drug_id>)
    # ====================================================================
    @patch('app.routes.favorite.get_jwt_identity')
    @patch('app.utils.db.Database.execute_query')
    def test_remove_favorite_success(self, mock_query, mock_jwt):
        """測試：成功將特定藥品從使用者的收藏清單中移除"""
        mock_jwt.return_value = str(self.mock_user_id)
        mock_query.return_value = None

        response = self.client.delete(f"{self.base_url}/{self.mock_drug_id}", headers=self.headers)
        
        assert response.status_code == 200
        res_data = json.loads(response.data)
        assert res_data["status"] == "success"
        assert str(self.mock_drug_id) in res_data["message"]

    # ====================================================================
    # 3. 測試：檢查藥品是否已被收藏 (GET /api/v1/favorites/check/<drug_id>)
    # ====================================================================
    @pytest.mark.parametrize("db_return, expected_status", [
        ({"1": 1}, True),
        (None, False)
    ])
    @patch('app.routes.favorite.get_jwt_identity')
    @patch('app.utils.db.Database.execute_query')
    def test_check_favorite_status(self, mock_query, mock_jwt, db_return, expected_status):
        """參數化測試：驗證系統在「已收藏」與「未收藏」兩種狀態下的回傳值是否正確"""
        mock_jwt.return_value = str(self.mock_user_id)
        mock_query.return_value = db_return

        response = self.client.get(f"{self.base_url}/check/{self.mock_drug_id}", headers=self.headers)
        
        assert response.status_code == 200
        res_data = json.loads(response.data)
        assert res_data["is_favorited"] == expected_status

    # ====================================================================
    # 4. 測試：取得使用者收藏清單 (GET /api/v1/favorites)
    # ====================================================================
    @patch('app.routes.favorite.get_jwt_identity')
    @patch('app.utils.db.Database.execute_query')
    def test_get_favorites_success(self, mock_query, mock_jwt):
        """測試：成功撈出目前登入使用者的全英文收藏藥品詳細清單"""
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