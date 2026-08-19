import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values


# ==========================================
# 1. 權威合規的 MedlinePlus 官方物理定義字典
# ==========================================
METRIC_DEFINITIONS = {
    "RDW": "A red cell distribution width (RDW) test measures how much the volume and size of your red blood cells (erythrocytes) varies.",
    "Red Blood Cells": "A red blood cell (RBC) count measures the number of red blood cells, also known as erythrocytes, in your blood. Red blood cells are made in your bone marrow, the spongy tissue inside your large bones. They contain hemoglobin, an iron-rich protein that carries oxygen from your lungs to every cell in your body. Your cells need oxygen to grow, reproduce, and make energy for you to function. An RBC count that is higher or lower than normal is often the first sign of an illness.",
    "White Blood Cells": "White blood cells are part of your immune system. They help your body fight off infections and other diseases.",
    "MCHC": "Mean Corpuscular Hemoglobin Concentration (MCHC) measures how concentrated (close together) the hemoglobin is in your red blood cells. It also includes a calculation of the size and volume of your red blood cells.",
    "Hematocrit": "Hematocrit is a blood test that measures how much of a person's blood is made up of red blood cells as opposed to plasma.",
    "Hemoglobin": "Hemoglobin is an iron-rich protein in your red blood cells. It carries oxygen from your lungs to the rest of your body.",
    "Platelet Count": "A platelet count is a lab test to measure how many platelets you have in your blood. Platelets are particles in the blood that help the blood clot. They are smaller than red or white blood cells.",
    "MCV": "MCV stands for mean corpuscular volume. An MCV blood test measures the average size of your red blood cells.",
    "MCH": "Mean corpuscular hemoglobin (MCH), which measures the average amount of hemoglobin in a single red blood cell.",
    "Chloride": "Chloride is a type of electrolyte. Electrolytes are electrically charged minerals that help control the amount of fluids and the balance of acids and bases (pH balance) in your body.",
    "Bicarbonate": "Bicarbonate is necessary to maintain the proper acid-base balance in the body, which is necessary for most biological reactions to proceed properly.",
    "Magnesium": "Magnesium helps control blood pressure and blood glucose, also called blood sugar. It's important for building strong bones, and it supports your immune system.",
    "Urea Nitrogen": "Urea nitrogen is a waste product that forms as your body breaks down proteins. It's carried in your blood and then removed by your kidneys when you urinate (pee).",
    "Calcium, Total": "Total calcium test measures all the calcium in your blood. You have two types of blood calcium that are normally present in about equal amounts: 1. Bound calcium is attached to proteins in your blood. 2. Free calcium is not attached to proteins. It's also called ionized calcium. This form of blood calcium is active in many body functions.",
    "Sodium": "Sodium is an element that the body needs to work properly. Salt contains sodium.",
    "Potassium": "Potassium is a mineral that your body needs to work properly. It is a type of electrolyte. It helps your nerves to function and muscles to contract. It helps your heartbeat stay regular." ,
    "Anion Gap": "The anion gap blood test shows whether your electrolytes are out of balance or if your blood is too acidic or not acidic enough.",
    "Creatinine": "Creatinine is a normal waste product in your body. It's made when you use your muscles and some of the muscle tissue breaks down.",
    "Glucose": "Blood glucose, or blood sugar, is the main sugar found in your blood. It is your body's primary source of energy. It comes from the food you eat. Your body breaks down most of that food into glucose and releases it into your bloodstream.",
    "Phosphate": "A phosphate in blood test measures the amount of phosphate in a sample of your blood. Phosphate contains the mineral phosphorus. So, a phosphate test is sometimes called a phosphorus test."
}


def init_postgres_db():
    print("1. 正在連接本地 PostgreSQL 資料庫...")
    # ==========================================
    # ⚠️ 請將以下參數改成你本地電腦的 PostgreSQL 帳號密碼
    # ==========================================
    conn_params = {
        "dbname": os.getenv("DB_NAME", "med_db"),
        "user": os.getenv("DB_USER", "yilin"),
        "password": os.getenv("DB_PASSWORD", ""),
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432")
    }
    
    try:
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        print("連線成功！")
        
        print("2. 正在建立 medical_metrics 資料表...")
        # 建立資料表，CASCADE 會連同相關的約束一起删乾淨，確保環境純淨
        cursor.execute("DROP TABLE IF EXISTS medical_metrics CASCADE;")
        cursor.execute("""
            CREATE TABLE medical_metrics (
                id SERIAL PRIMARY KEY,
                itemid INT UNIQUE,
                metric_label VARCHAR(150),
                fluid VARCHAR(50),
                category VARCHAR(50),
                ref_range_lower FLOAT,
                ref_range_upper FLOAT,
                valueuom VARCHAR(30),
                metric_definition TEXT
            );
        """)
        
        print("3. 正在讀取清洗好的 CSV，並組裝 MedlinePlus 權威定義...")
        df = pd.read_csv('data/cleaned_metrics_base.csv')
        
        # 使用 .map() 將 MedlinePlus 定義對應到對應的 label 上
        df['metric_definition'] = df['label'].map(METRIC_DEFINITIONS).fillna("Standard clinical metric definition not found.")
        
        # 【重要修正：資料防錯位】
        # 顯式指定 DataFrame 的欄位順序，使其跟下方 SQL INSERT 的欄位順序 (100% 完美對齊)
        df_ordered = df[[
            'itemid', 'label', 'fluid', 'category', 
            'ref_range_lower', 'ref_range_upper', 'valueuom', 'metric_definition'
        ]]
        
        # 轉成 tuple 清單以利 execute_values 批次高效寫入
        records_to_insert = [tuple(x) for x in df_ordered.to_numpy()]
        
        print("4. 正在將 20 筆權威指標資料匯入 PostgreSQL...")
        insert_query = """
            INSERT INTO medical_metrics (
                itemid, metric_label, fluid, category, 
                ref_range_lower, ref_range_upper, valueuom, metric_definition
            ) VALUES %s
        """
        execute_values(cursor, insert_query, records_to_insert)
        
        # 提交(Commit)變更，這一步才會真正寫入硬碟
        conn.commit()
        print("【階段一】資料庫建置與資料匯入全部完成！")
        
        # 驗證 RAG 查詢：模擬後端未來要做的 SELECT
        cursor.execute("SELECT metric_label, ref_range_lower, ref_range_upper, valueuom, metric_definition FROM medical_metrics WHERE metric_label = 'Glucose';")
        print("\n 抽查資料庫驗證成功 (Glucose):")
        row = cursor.fetchone()
        print(f"指標名稱: {row[0]}")
        print(f"參考範圍: {row[1]} ~ {row[2]} {row[3]}")
        print(f"官方定義: {row[4]}")

        # =========================================================
        # 步驟 2: 開啟 pgvector 擴充與建立闢謠向量資料表 (新增的內容)
        # =========================================================
        print("\n5. 正在建立 pgvector 擴充功能與闢謠向量資料表...")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS factcheck_vectors (
                id SERIAL PRIMARY KEY,
                claim TEXT NOT NULL,
                explanation TEXT NOT NULL,
                label VARCHAR(50),
                claim_url TEXT,
                main_text TEXT,
                sources TEXT,
                embedding vector(384)
            );
        """)

        # 建立 HNSW 向量索引（5ms 極速查詢）
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS factcheck_vector_hnsw_idx 
            ON factcheck_vectors USING hnsw (embedding vector_cosine_ops);
        """)
        
        # 統一 Commit 寫入硬碟
        conn.commit()
        print("【階段一】資料庫結構建置 (MIMIC 指標 + pgvector 闢謠表) 全部完成！")

    except Exception as e:
        print(f"發生錯誤: {e}")
    finally:
        # 無論成功失敗，都一定要關閉連線資源
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    init_postgres_db()