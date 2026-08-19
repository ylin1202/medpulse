# scripts/populate_embeddings.py
import asyncio
import os
import asyncpg
from sentence_transformers import SentenceTransformer

# 載入 384 維 Embedding 模型 (與 pgvector schema 完全對齊)
print("[Init] Loading SentenceTransformer model (all-MiniLM-L6-v2)...")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# 資料庫連線配置 (讀取環境變數或預設值)
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "medpulse_db")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

async def populate_embeddings():
    print(f"[Connecting] Connecting to PostgreSQL at {DB_HOST}:{DB_PORT}/{DB_NAME}...")
    try:
        conn = await asyncpg.connect(DATABASE_URL)
    except Exception as e:
        print(f"[Error] Failed to connect to database: {e}")
        return

    try:
        # 撈出尚未產生 embedding 或全部的指標資料
        rows = await conn.fetch("SELECT id, metric_label, metric_definition FROM medical_metrics;")
        print(f"[Processing] Found {len(rows)} medical metrics to encode.")

        for row in rows:
            metric_id = row["id"]
            label = row["metric_label"]
            definition = row["metric_definition"] or ""
            
            # 將指標名稱與醫學定義拼接後產生特徵向量
            text_to_embed = f"{label}: {definition}".strip()
            embedding_vector = embed_model.encode(text_to_embed).tolist()
            
            # 更新寫入 pgvector 欄位
            await conn.execute(
                "UPDATE medical_metrics SET embedding = $1::vector WHERE id = $2;",
                str(embedding_vector), metric_id
            )
            print(f"  └─ Updated embedding for: {label}")

        print("\n All embeddings successfully generated and stored in PostgreSQL!")
    except Exception as e:
        print(f"[Error] Failed during embedding update: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(populate_embeddings())