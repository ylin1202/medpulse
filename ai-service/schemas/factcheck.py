from typing import List, Optional
from pydantic import BaseModel, Field

class FactCheckRequest(BaseModel):
    query: str = Field(..., min_length=1)

class FactCheckItem(BaseModel):
    id: str
    claim: Optional[str] = None
    verdict: Optional[str] = None
    summary: Optional[str] = None
    explanation: Optional[str] = None              # AI 生成的摘要 (彈窗 / 摘要區)
    original_explanation: Optional[str] = None     # 資料庫 PUBHEALTH 原始文獻 (詳情頁底層)
    source: str = "PUBHEALTH Dataset"              # 預設來源改為 PUBHEALTH
    claim_url: Optional[str] = None
    score: Optional[float] = None

class FactCheckResponse(BaseModel):
    status: str
    data: List[FactCheckItem]