import json
import os
import time
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values
import requests

load_dotenv()

# Retrieve Google API Key from environment variables
GOOGLE_API_KEY = os.getenv("GOOGLE_GEOCODING_API_KEY")


def get_coordinates_from_google(address):
    """
    Geocode an address into (latitude, longitude) coordinates using the Google Maps Geocoding API.
    """
    if not GOOGLE_API_KEY:
        print("Warning: GOOGLE_GEOCODING_API_KEY is not set. Using default coordinates.")
        return 25.0380, 121.5644  # Fallback coordinates (Taipei City)

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
            print(f"Geocoding lookup returned no results for ({address}): {data.get('status')}")

    except Exception as e:
        print(f"Geocoding API request failed: {e}")

    # Fallback to default coordinates upon failure
    return 25.0380, 121.5644


def import_pharmacies_json(json_file_path):
    """Parse local pharmacy dataset, resolve geolocations, and batch insert into PostgreSQL."""
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5432),
        dbname=os.getenv("DB_NAME", "med_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "")
    )
    cursor = conn.cursor()

    # Create table schema and coordinate indexes idempotently
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

    # Load JSON dataset
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Preparing to geocode and import {len(data)} pharmacy records...")

    records = []
    # Process specified slice batch
    for item in data[9000:9100]:
        name = item.get("機構名稱")
        status = item.get("機構狀態")
        city = item.get("地址縣市別", "").strip()
        district = item.get("地址鄉鎮市區", "").strip()
        street = item.get("地址街道巷弄號", "").strip()

        # Construct full canonical address string
        full_address = f"{city}{district}{street}"
        phone = item.get("電話")
        is_nhi = True if item.get("是否為健保特約藥局") == "Y" else False

        # Resolve coordinates via Google Maps Geocoding API
        lat, lon = get_coordinates_from_google(full_address)
        
        # Brief rate-limiting sleep between external API requests
        time.sleep(0.1)

        records.append((name, status, city, district, full_address, phone, is_nhi, lat, lon))
        print(f"Successfully processed: {name} | Lat: {lat}, Lon: {lon}")

    # Batch insert records into PostgreSQL
    insert_sql = """
    INSERT INTO pharmacies (name, status, city, district, address, phone, is_nhi_contracted, latitude, longitude)
    VALUES %s;
    """
    execute_values(cursor, insert_sql, records)
    conn.commit()

    print(f"\nSuccessfully imported {len(records)} pharmacy records into 'pharmacies' table.")
    cursor.close()
    conn.close()


if __name__ == "__main__":
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    JSON_PATH = os.path.join(CURRENT_DIR, "pharmacies.json")
    import_pharmacies_json(JSON_PATH)