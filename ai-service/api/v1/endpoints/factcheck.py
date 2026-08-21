import logging
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import get_db_pool
from app.schemas.factcheck import FactCheckItem, FactCheckRequest, FactCheckResponse
from app.services.factcheck_service import factcheck_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/factcheck", response_model=FactCheckResponse, status_code=status.HTTP_200_OK)
async def factcheck_endpoint(
    payload: FactCheckRequest, 
    request: Request,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Execute semantic rumor verification and claim debunking via pgvector similarity search.
    Enriches matched health claims with AI-synthesized contextual explanations.
    """
    user_query = payload.query.strip()
    if not user_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query statement cannot be empty."
        )

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
        explanation=item_dict.get("explanation"),                      # AI-synthesized explanation
        original_explanation=item_dict.get("original_explanation"),    # Ground-truth database source text
        source=item_dict.get("source") or "PUBHEALTH Dataset",
        claim_url=item_dict.get("claim_url", ""),
        score=item_dict.get("score")
    )

    # Output resolved claim payload to container stdout / logging stream
    logger.info(
        f"[{correlation_id}] Response payload -> "
        f"Claim: '{formatted_item.claim}', "
        f"Verdict: '{formatted_item.verdict}', "
        f"AI Explanation: '{formatted_item.explanation}'"
    )

    return FactCheckResponse(status="success", data=[formatted_item])