from typing import List, Optional
from pydantic import BaseModel, Field


class FactCheckRequest(BaseModel):
    """Request payload schema for semantic health rumor and claim verification."""
    query: str = Field(..., min_length=1, description="Claim or statement text to fact-check.")


class FactCheckItem(BaseModel):
    """Schema representing an individual verified fact-check record."""
    id: str
    claim: Optional[str] = None
    verdict: Optional[str] = None
    summary: Optional[str] = None
    explanation: Optional[str] = None              # AI-synthesized clinical summary for modal/preview
    original_explanation: Optional[str] = None     # Ground-truth source literature from PUBHEALTH database
    source: str = "PUBHEALTH Dataset"              # Default evidence source repository
    claim_url: Optional[str] = None
    score: Optional[float] = None


class FactCheckResponse(BaseModel):
    """Response payload schema for fact-check search results."""
    status: str
    data: List[FactCheckItem]