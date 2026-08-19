from pydantic import BaseModel, Field
from typing import List, Optional

class FactCheckRequest(BaseModel):
    query: str = Field(..., min_length=1)

class FactCheckItem(BaseModel):
    id: str
    claim: Optional[str] = None
    verdict: Optional[str] = None
    summary: Optional[str] = None
    explanation: Optional[str] = None
    source: str = "Medical Fact-Check Center"
    claim_url: Optional[str] = None
    score: Optional[float] = None

class FactCheckResponse(BaseModel):
    status: str
    data: List[FactCheckItem]