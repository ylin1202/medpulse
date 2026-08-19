import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

print("載入 parquet 闢謠資料...")
df = pd.read_parquet("data/factcheck_vectors.parquet")

# 載入 .env 檔案中的環境變數
load_dotenv()

# 🐘 建立 PostgreSQL 連線（優先讀取環境變數，若無則使用預設值）
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME", "med_db"),
    user=os.getenv("DB_USER", "yilin"),
    password=os.getenv("DB_PASSWORD", ""),
    host=os.getenv("DB_HOST", "localhost"),
    port=os.getenv("DB_PORT", "5432")
)
cursor = conn.cursor()

records = []
for _, row in df.iterrows():
    # 關鍵修正：將 embedding (ndarray/list) 強制轉成 Python list，如果是 list 再轉成 str，或確保是標準 list
    emb = row['embedding']
    if hasattr(emb, 'tolist'):
        emb = emb.tolist()  # 將 np.ndarray 轉成一般 Python list
    
    # 轉成 pgvector 接受的字串格式: '[0.1, 0.2, ...]'
    vec_str = f"[{','.join(map(str, emb))}]"

    records.append((
        str(row.get('claim', '')),
        str(row.get('explanation', '')),
        str(row.get('label', 'unproven')),
        str(row.get('claim_url', '')),
        str(row.get('main_text', '')),
        str(row.get('sources', '')),
        vec_str # 傳入格式化好的向量字串
    ))

insert_query = """
INSERT INTO factcheck_vectors (claim, explanation, label, claim_url, main_text, sources, embedding)
VALUES %s;
"""

print("開始批次匯入 PostgreSQL...")
execute_values(cursor, insert_query, records, page_size=1000)
conn.commit()

cursor.close()
conn.close()
print("闢謠向量庫 1.1 萬筆資料全部成功匯入 PostgreSQL `factcheck_vectors` 表格！")