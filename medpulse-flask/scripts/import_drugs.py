import json
import psycopg2
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

def extract_drug_data(item):
    """清理並抽取單筆 OpenFDA 藥品 JSON 資料"""
    openfda = item.get("openfda", {})
    
    # 取出陣列中的第一項作為字串
    brand_name = openfda.get("brand_name", [None])[0]
    generic_name = openfda.get("generic_name", [None])[0]
    manufacturer = openfda.get("manufacturer_name", [None])[0]
    product_type = openfda.get("product_type", [None])[0]
    route = openfda.get("route", [None])[0]

    # 合併文字陣列為段落
    active_ingredient = "\n".join(item.get("active_ingredient", [])) or None
    purpose = "\n".join(item.get("purpose", [])) or None
    indications = "\n".join(item.get("indications_and_usage", [])) or None
    warnings = "\n".join(item.get("warnings", [])) or None
    do_not_use = "\n".join(item.get("do_not_use", [])) or None
    boxed_warning = "\n".join(item.get("boxed_warning", [])) or None

    return (
        item.get("id"),
        brand_name,
        generic_name,
        manufacturer,
        product_type,
        route,
        active_ingredient,
        purpose,
        indications,
        warnings,
        do_not_use,
        boxed_warning,
        json.dumps(openfda) # 轉為 JSONB 儲存
    )

def import_json_to_db(json_file_path):
    """讀取 JSON 並匯入 PostgreSQL"""
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5432),
        dbname=os.getenv("DB_NAME", "med_db"),
        user=os.getenv("DB_USER", "yilin"),
        password=os.getenv("DB_PASSWORD", "")
    )
    cursor = conn.cursor()

    # 1. 自動建表
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS drugs (
        id VARCHAR(100) PRIMARY KEY,
        brand_name VARCHAR(255),
        generic_name VARCHAR(255),
        manufacturer_name VARCHAR(255),
        product_type VARCHAR(100),
        route VARCHAR(100),
        active_ingredient TEXT,
        purpose TEXT,
        indications_and_usage TEXT,
        warnings TEXT,
        do_not_use TEXT,
        boxed_warning TEXT,
        raw_openfda JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    cursor.execute(create_table_sql)

    # 2. 讀取 JSON 檔案
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    results = data.get("results", [])
    print(f"準備匯入 {len(results)} 筆藥品資料...")

    # 3. 批次寫入資料庫
    insert_sql = """
    INSERT INTO drugs (
        id, brand_name, generic_name, manufacturer_name, product_type, route,
        active_ingredient, purpose, indications_and_usage, warnings, do_not_use, boxed_warning, raw_openfda
    ) VALUES %s
    ON CONFLICT (id) DO NOTHING;
    """

    drug_records = [extract_drug_data(item) for item in results if item.get("id")]
    
    execute_values(cursor, insert_sql, drug_records)
    conn.commit()

    print(f"成功匯入 {len(drug_records)} 筆藥品資料至 'drugs' 資料表！")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    # 自動取得目前 import_drugs.py 所在的資料夾路徑
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # 指向同在 scripts 資料夾下的 drug-label-0014.json
    JSON_PATH = os.path.join(CURRENT_DIR, "drug-label-0014.json")
    
    import_json_to_db(JSON_PATH)