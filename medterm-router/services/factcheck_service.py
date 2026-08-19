import asyncio
import logging
import asyncpg
from sentence_transformers import SentenceTransformer
from app.core.config import settings

logger = logging.getLogger(__name__)

class FactCheckRAGService:
    """全英文健康闢謠 Vector RAG 服務類別 (Singleton)"""

    def __init__(self, model_name: str = settings.EMBEDDING_MODEL_NAME):
        logger.info("[Startup] 正在初始化 Embedding 模型...")
        self.model = SentenceTransformer(model_name)
        logger.info("[Startup] Embedding 模型載入完成！")

    async def search(
        self, user_query: str, db_pool: asyncpg.Pool, top_k: int = 1, correlation_id: str = "UNKNOWN"
    ) -> dict:
        if not db_pool:
            return {"found": False, "message": "Database connection pool is uninitialized."}
        if not user_query.strip():
            return {"found": False, "message": "Query text cannot be empty."}

        # 向量化推論
        query_vector = await asyncio.to_thread(
            lambda: self.model.encode([user_query], normalize_embeddings=True)[0].tolist()
        )
        vector_str = f"[{','.join(map(str, query_vector))}]"

        query = """
            SELECT claim, explanation, label, claim_url,
                   1 - (embedding <=> $1::vector) AS similarity_score
            FROM factcheck_vectors
            ORDER BY embedding <=> $1::vector ASC
            LIMIT $2;
        """

        try:
            async with db_pool.acquire() as conn:
                row = await conn.fetchrow(query, vector_str, top_k)

            if not row or row["similarity_score"] < 0.6:
                return {"found": False, "message": "No relevant health fact-check found."}

            return {
                "found": True,
                "verdict": str(row["label"]).upper(),
                "matched_claim": row["claim"],
                "explanation": row["explanation"],
                "source_url": row["claim_url"],
                "similarity_score": round(float(row["similarity_score"]), 4),
            }
        except Exception as e:
            logger.error(f"[{correlation_id}] pgvector RAG 檢索失敗: {e}")
            return {"found": False, "message": str(e)}

# 全域單例
factcheck_service = FactCheckRAGService()