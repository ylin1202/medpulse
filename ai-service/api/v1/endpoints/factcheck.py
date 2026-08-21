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
    
    if not result or not result.get("found"):
        logger.warning(f"[{correlation_id}] No factcheck match found.")
        return FactCheckResponse(status="success", data=[])

    data_list = result.get("data", [])
    if not data_list:
        logger.warning(f"[{correlation_id}] Result data list is empty.")
        return FactCheckResponse(status="success", data=[])
    
    item_dict = data_list[0]

    formatted_item = FactCheckItem(
        id=item_dict.get("id") or correlation_id,
        claim=item_dict.get("matched_claim") or item_dict.get("claim"),
        verdict=item_dict.get("verdict"),
        summary=item_dict.get("summary"),
        explanation=item_dict.get("explanation"),                      # AI 摘要
        original_explanation=item_dict.get("original_explanation"),    # 原始資料庫文本
        source=item_dict.get("source") or "PUBHEALTH Dataset",
        claim_url=item_dict.get("claim_url", ""),
        score=item_dict.get("score")
    )

    # 在這裡印出完整回傳內容到 Docker Log
    logger.info(
        f"[{correlation_id}] Response payload -> "
        f"Claim: '{formatted_item.claim}', "
        f"Verdict: '{formatted_item.verdict}', "
        f"AI Explanation: '{formatted_item.explanation}'"
    )

    return FactCheckResponse(status="success", data=[formatted_item])