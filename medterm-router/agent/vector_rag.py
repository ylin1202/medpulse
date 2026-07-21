# agent/vector_rag.py
import asyncio
import asyncpg
from sentence_transformers import SentenceTransformer


class FactCheckRAGService:
    """
    全英文健康闢謠 Vector RAG 服務類別 (Vector Retrieval-Augmented Generation)
    採用單例模式 (Singleton Pattern) 設計：在應用程式啟動時預先將模型載入記憶體 (約 90MB)，
    避免每次使用者打 API 時重新載入模型造成 1~2 秒的大幅延遲。
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        初始化服務並載入 SentenceTransformer 英文 Embedding 模型。
        輕量級模型 all-MiniLM-L6-v2 會產出 384 維度的向量。
        """
        print("[Startup] 正在初始化 Embedding 模型...")
        self.model = SentenceTransformer(model_name)
        print("[Startup] Embedding 模型載入完成！")

    async def search(
        self, user_query: str, db_pool: asyncpg.Pool, top_k: int = 1, correlation_id: str = "UNKNOWN"
    ) -> dict:
        """
        執行闢謠檢索的主要非同步函式：
        1. 使用 asyncio.to_thread 將向量編碼 (Encoding) 丟給 worker thread，防止卡住 asyncio Event Loop。
        2. 透過 asyncpg 向 PostgreSQL 執行 pgvector Cosine Similarity 檢索。
        """

        if not db_pool:
            return {"found": False, "message": "Database connection pool is uninitialized."}
        # 1. 基礎輸入防護：空字串直接退回
        if not user_query.strip():
            return {"found": False, "message": "Query text cannot be empty."}

        # ⚡ 2. 向量化 (Vector Encoding)：
        # 使用 asyncio.to_thread 將 CPU 密集型的模型推論運算移至獨立線程執行，
        # 確保在高效能/高併發情境下，完全不占用 FastAPI 主 Event Loop！
        query_vector = await asyncio.to_thread(
            lambda: self.model.encode(
                [user_query], normalize_embeddings=True
            )[0].tolist()
        )

        # 轉成 PostgreSQL pgvector 接受的字串格式: '[0.123, -0.456, ...]'
        vector_str = f"[{','.join(map(str, query_vector))}]"

        # 3. SQL 語意檢索：
        # <=> 為 pgvector 的 Cosine Distance 運算子，值越小代表越相似。
        # 1 - Distance 即為 Cosine Similarity 相似度得分。
        query = """
            SELECT claim, explanation, label, claim_url,
                   1 - (embedding <=> $1::vector) AS similarity_score
            FROM factcheck_vectors
            ORDER BY embedding <=> $1::vector ASC
            LIMIT $2;
        """

        try:
            # 使用 asyncpg 非同步連線池取得連線並執行查詢
            async with db_pool.acquire() as conn:
                row = await conn.fetchrow(query, vector_str, top_k)

            # 4. 門檻值過濾 (Cosine Similarity < 0.6 代表查無足夠相關的闢謠紀錄)
            if not row or row["similarity_score"] < 0.6:
                return {
                    "found": False,
                    "message": "No relevant health fact-check found.",
                }

            # 5. 格式化回傳結構化資料
            return {
                "found": True,
                "verdict": str(row["label"]).upper(),  # 闢謠結果 (如 FALSE, MIXTURE)
                "matched_claim": row["claim"],          # 資料庫中比對到的原始謠言
                "explanation": row["explanation"],      # 權威查核報告解釋
                "source_url": row["claim_url"],         # 查核來源網址
                "similarity_score": round(float(row["similarity_score"]), 4),  # 相似度得分 (四捨五入至小數第四位)
            }
        except Exception as e:
            print(f"[{correlation_id}] pgvector RAG 檢索失敗: {e}")
            return {"found": False, "message": str(e)}


# 在模組載入時建立全域實例 (Global Singleton Instance)
# main.py 或其他路由可以直接 import 此物件調用 search()，享有秒級記憶體快取優勢
factcheck_service = FactCheckRAGService()