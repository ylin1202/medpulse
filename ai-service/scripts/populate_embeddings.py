import asyncio
import os
import asyncpg
from sentence_transformers import SentenceTransformer

# Load 384-dimensional embedding model (aligned with pgvector schema)
print("[Init] Loading SentenceTransformer model (all-MiniLM-L6-v2)...")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# Database connection configuration (read environment variables with fallbacks)
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "medpulse_db")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


async def populate_embeddings():
    """
    Encode clinical lab metrics and definitions into 384-dimensional dense vectors
    and batch update the pgvector column in PostgreSQL.
    """
    print(f"[Connecting] Connecting to PostgreSQL at {DB_HOST}:{DB_PORT}/{DB_NAME}...")
    try:
        conn = await asyncpg.connect(DATABASE_URL)
    except Exception as e:
        print(f"[Error] Failed to connect to database: {e}")
        return

    try:
        # Fetch all medical metric records
        rows = await conn.fetch("SELECT id, metric_label, metric_definition FROM medical_metrics;")
        print(f"[Processing] Found {len(rows)} medical metrics to encode.")

        for row in rows:
            metric_id = row["id"]
            label = row["metric_label"]
            definition = row["metric_definition"] or ""
            
            # Concatenate metric label and clinical definition for contextual embedding
            text_to_embed = f"{label}: {definition}".strip()
            embedding_vector = embed_model.encode(text_to_embed).tolist()
            
            # Update pgvector embedding column
            await conn.execute(
                "UPDATE medical_metrics SET embedding = $1::vector WHERE id = $2;",
                str(embedding_vector), metric_id
            )
            print(f"  └─ Updated embedding for: {label}")

        print("\nAll embeddings successfully generated and stored in PostgreSQL.")
    except Exception as e:
        print(f"[Error] Failed during embedding update: {e}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(populate_embeddings())