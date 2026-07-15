import json
import os
import time
import requests
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

# 從 .env 取得 Google API Key
GOOGLE_API_KEY = os.getenv("GOOGLE_GEOCODING_API_KEY")

def get_coordinates_from_google(address):
    """
    使用 Google Maps Geocoding API 將台灣地址轉為 (latitude, longitude)
    """
    if not GOOGLE_API_KEY:
        print("未偵測到 GOOGLE_GEOCODING_API_KEY，請確認 .env 設定")
        return 25.0380, 121.5644  # 預設備用座標 (臺北市)

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": GOOGLE_API_KEY,
        "language": "zh-TW"
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if data.get("status") == "OK" and data.get("results"):
            location = data["results"][0]["geometry"]["location"]
            return location["lat"], location["lng"]
        else:
            print(f"Google Geocoding 查無座標 ({address}): {data.get('status')}")

    except Exception as e:
        print(f"Geocoding API 請求失敗: {e}")

    # 若失敗則回傳預設座標
    return 25.0380, 121.5644


def import_pharmacies_json(json_file_path):
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5432),
        dbname=os.getenv("DB_NAME", "med_db"),
        user=os.getenv("DB_USER", "yilin"),
        password=os.getenv("DB_PASSWORD", "")
    )
    cursor = conn.cursor()

    # 1. 自動建表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pharmacies (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        status VARCHAR(50),
        city VARCHAR(50),
        district VARCHAR(50),
        address TEXT NOT NULL,
        phone VARCHAR(50),
        is_nhi_contracted BOOLEAN DEFAULT TRUE,
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_pharmacies_coords ON pharmacies(latitude, longitude);
    """)

    # 2. 讀取 JSON 資料
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"準備透過 Google Geocoding 轉換 {len(data)} 筆藥局地址...")

    records = []
    # 1-4499] 已經有了 剩餘就是跳著用 6000-6399), 8000-8200), 9000-9100) 這些都取得
    for item in data[9000:9100]:
        name = item.get("機構名稱")
        status = item.get("機構狀態")
        city = item.get("地址縣市別", "").strip()
        district = item.get("地址鄉鎮市區", "").strip()
        street = item.get("地址街道巷弄號", "").strip()

        # 組合標準完整地址
        full_address = f"{city}{district}{street}"
        phone = item.get("電話")
        is_nhi = True if item.get("是否為健保特約藥局") == "Y" else False

        # 透過 Google API 轉座標
        lat, lon = get_coordinates_from_google(full_address)
        
        # Google API 速度很快，給予極短延遲即可 (0.1秒)
        time.sleep(0.1)

        records.append((name, status, city, district, full_address, phone, is_nhi, lat, lon))
        print(f"成功轉換: {name} | Lat: {lat}, Lon: {lon}")

    # 3. 批次寫入 PostgreSQL
    insert_sql = """
    INSERT INTO pharmacies (name, status, city, district, address, phone, is_nhi_contracted, latitude, longitude)
    VALUES %s;
    """
    execute_values(cursor, insert_sql, records)
    conn.commit()

    print(f"\n 成功寫入 {len(records)} 筆藥局資料至 PostgreSQL 表 'pharmacies'！")
    cursor.close()
    conn.close()


if __name__ == "__main__":
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    JSON_PATH = os.path.join(CURRENT_DIR, "pharmacies.json")
    import_pharmacies_json(JSON_PATH)