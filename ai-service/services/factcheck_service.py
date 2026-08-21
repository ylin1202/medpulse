import asyncio
import inspect
import logging
import os
import asyncpg
from google import genai
from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger(__name__)


class FactCheckRAGService:
    """Singleton Vector RAG service for evidence-based health rumor verification and claim debunking."""

    def __init__(self, model_name: str = settings.EMBEDDING_MODEL_NAME):
        logger.info(f"[Startup] Initializing embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        
        raw_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        self.api_key = raw_key.strip().strip('"\'')
        
        if self.api_key:
            self.gemini_client = genai.Client(api_key=self.api_key)
            logger.info("[Startup] Gemini Client initialized successfully.")
        else:
            self.gemini_client = None
            logger.warning("[Startup] GEMINI_API_KEY is empty or not configured!")

    async def _generate_rag_summary(self, user_query: str, matched_data: dict, correlation_id: str) -> str:
        """Generation Stage: Synthesize fact-check context using Gemini with automated retries."""
        if not self.gemini_client:
            return matched_data.get("explanation", "")

        prompt = inspect.cleandoc(f"""
        You are a professional medical fact-checking assistant. Answer the user query clearly and accurately based strictly on the retrieved medical fact-check data.

        ### FACT-CHECK CONTEXT:
        - Original Claim: {matched_data.get('claim', '')}
        - Verdict: {matched_data.get('label', '')}
        - Explanation: {matched_data.get('explanation', '')}
        - Evidence: {str(matched_data.get('main_text') or '')[:600]}

        ### USER QUERY:
        "{user_query}"

        ### REQUIREMENTS:
        1. Clearly state whether the rumor is true, false, or unproven at the beginning.
        2. Synthesize the medical reasoning concisely based on the context provided.
        3. Keep the response concise and objective (around 100-150 words).
        """)

        candidate_models = ["gemini-3.6-flash", "gemini-3.5-flash"]

        for model_name in candidate_models:
            for attempt in range(2):
                try:
                    response = await asyncio.to_thread(
                        lambda m=model_name: self.gemini_client.models.generate_content(
                            model=m,
                            contents=prompt
                        )
                    )
                    if response.text:
                        logger.info(f"[{correlation_id}] Successfully generated summary using {model_name}.")
                        return response.text.strip()
                except Exception as e:
                    logger.warning(f"[{correlation_id}] Model {model_name} attempt {attempt + 1} failed: {e}")
                    if "503" in str(e):
                        await asyncio.sleep(0.5 * (attempt + 1))

        logger.error(f"[{correlation_id}] All Gemini models failed. Falling back to DB explanation.")
        return matched_data.get("explanation", "")

    async def search(
        self, user_query: str, db_pool: asyncpg.Pool, top_k: int = 1, correlation_id: str = "UNKNOWN"
    ) -> dict:
        """
        Execute vector similarity search across verified claims in PostgreSQL (pgvector)
        and augment matched evidence with AI-synthesized clinical reasoning.
        """
        if not db_pool:
            return {"found": False, "message": "Database connection pool is uninitialized."}
        if not user_query.strip():
            return {"found": False, "message": "Query text cannot be empty."}

        # 1. Retrieval (Embed query and search vector index)
        query_vector = await asyncio.to_thread(
            lambda: self.model.encode([user_query], normalize_embeddings=True)[0].tolist()
        )
        vector_str = f"[{','.join(map(str, query_vector))}]"

        query = """
            SELECT id, claim, explanation, label, claim_url, main_text, sources,
                   1 - (embedding <=> $1::vector) AS similarity_score
            FROM factcheck_vectors
            ORDER BY embedding <=> $1::vector ASC
            LIMIT $2;
        """

        try:
            async with db_pool.acquire() as conn:
                await conn.execute("SET LOCAL ivfflat.probes = 10;")
                row = await conn.fetchrow(query, vector_str, top_k)

            if not row or row["similarity_score"] < 0.45:
                return {"found": False, "message": "No relevant health fact-check found.", "data": []}

            score = round(float(row["similarity_score"]), 4)
            row_dict = dict(row)

            # 2. Generation (Grounded Synthesis)
            rag_explanation = await self._generate_rag_summary(user_query, row_dict, correlation_id)

            # 3. Extract ground-truth literature context from database
            raw_db_text = (row_dict.get("explanation") or row_dict.get("main_text") or "").strip()
            
            # Prioritize sources metadata column
            raw_sources = (row_dict.get("sources") or row_dict.get("claim_url") or "").strip()

            return {
                "found": True,
                "status": "success",
                "data": [{
                    "id": str(row_dict.get("id", "")),
                    "matched_claim": row_dict.get("claim", ""),
                    "claim": row_dict.get("claim", ""),
                    "verdict": str(row_dict.get("label", "UNVERIFIED")).upper(),
                    "explanation": rag_explanation,                    # AI-synthesized explanation for modal preview
                    "original_explanation": raw_db_text,               # PUBHEALTH literature source text for details view
                    "summary": rag_explanation[:150] + "..." if len(rag_explanation) > 150 else rag_explanation,
                    "claim_url": raw_sources,                          # Full source reference URL
                    "source": raw_sources,                             # Evidence source
                    "sources": raw_sources,
                    "score": score,
                }]
            }
        
        except Exception as e:
            logger.error(f"[{correlation_id}] RAG retrieval failed: {e}", exc_info=True)
            return {"found": False, "message": str(e), "data": []}


factcheck_service = FactCheckRAGService()