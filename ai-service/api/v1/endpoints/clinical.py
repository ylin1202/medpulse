import logging
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.agent.graph import app as agent_app
from app.api.deps import get_cache_service, get_db_pool
from app.schemas.clinical import AnalysisResponse, ClinicalTextRequest
from app.services.cache_service import RedisCacheService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/analyze", response_model=AnalysisResponse, status_code=status.HTTP_200_OK)
async def analyze_clinical_text(
    payload: ClinicalTextRequest,
    request: Request,
    cache_service: RedisCacheService = Depends(get_cache_service),
    db_pool: asyncpg.Pool = Depends(get_db_pool),
):
    """
    Analyze unstructured clinical text using fine-tuned Gemma extraction and Dual-RAG retrieval.
    Includes distributed Redis rate limiting, deterministic query caching, and LangGraph workflow orchestration.
    """
    text = payload.clinical_text.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Clinical text content cannot be empty."
        )

    correlation_id = getattr(request.state, "correlation_id", "UNKNOWN")
    client_ip = request.client.host if request.client else "unknown"

    # Rate limiting guardrail: 5 requests per 60-second window
    rate_limit_key = f"rate_limit:analyze:{client_ip}"
    if await cache_service.is_rate_limited(rate_limit_key, limit=5, window=60):
        logger.warning(f"[{correlation_id}] IP {client_ip} has been rate limited.")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. You are allowed to submit 5 requests per minute."
        )

    cache_key = cache_service.generate_cache_key("medical_rag", text)

    # 1. Query Redis Cache
    cached_result = await cache_service.get_json(cache_key)
    if cached_result:
        logger.info(f"[{correlation_id}] [Redis Cache HIT] Query resolved via cache.")
        cached_result["cached"] = True
        return cached_result

    # 2. Invoke LangGraph Agentic State Machine
    logger.info(f"[{correlation_id}] [Redis Cache MISS] Invoking fine-tuned Gemma and LangGraph state machine...")
    inputs = {
        "clinical_text": text,
        "retry_count": 0,
        "json_valid": False,
        "is_correction": False,
        "db_pool": db_pool
    }

    result = await agent_app.ainvoke(inputs)
    final_analysis = result["final_analysis"]
    final_analysis["cached"] = False

    # 3. Populate cache on successful metric detection (1-hour TTL)
    if final_analysis.get("detected_metrics_count", 0) > 0:
        await cache_service.set_json(cache_key, final_analysis, ttl=3600)

    return final_analysis