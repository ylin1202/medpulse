import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
import asyncpg

from app.schemas.factcheck import FactCheckRequest, FactCheckResponse, FactCheckItem
from app.api.deps import get_db_pool
from app.services.factcheck_service import factcheck_service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/factcheck", response_model=FactCheckResponse, status_code=status.HTTP_200_OK)
async def factcheck_endpoint(
    payload: FactCheckRequest, 
    request: Request,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):
    user_query = payload.query.strip()
    if not user_query:
        raise HTTPException(status_code=400, detail="Query statement cannot be empty.")

    correlation_id = getattr(request.state, "correlation_id", "UNKNOWN")
    logger.info(f"[{correlation_id}] Executing pgvector factcheck for query: '{user_query}'")
    
    result = await factcheck_service.search(user_query, db_pool, correlation_id=correlation_id)
    
    if not result.get("found"):
        return FactCheckResponse(status="success", data=[])

    formatted_item = FactCheckItem(
        id=correlation_id,
        claim=result.get("matched_claim"),
        verdict=result.get("verdict"),
        summary=result.get("explanation", "")[:120] + "...",
        explanation=result.get("explanation"),
        source="Medical Fact-Check Center",
        claim_url=result.get("source_url", ""),
        score=result.get("similarity_score")
    )

    return FactCheckResponse(status="success", data=[formatted_item])