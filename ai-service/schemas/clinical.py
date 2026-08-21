from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


# 1. 請求體模型 (FastAPI 必須 import 的類別)
class ClinicalTextRequest(BaseModel):
    clinical_text: str = Field(..., description="The raw clinical text or medical note to analyze")


# 2. 單一檢驗指標參考值與定義模型
class MetricReference(BaseModel):
    lower: Optional[float] = None
    upper: Optional[float] = None
    unit: Optional[str] = None
    definition: Optional[str] = None
    match_type: Optional[str] = None
    rrf_score: Optional[float] = None


# 3. 分析回應模型 (包含 RAG 生成的 clinical_synthesis)
class AnalysisResponse(BaseModel):
    status: str
    detected_metrics_count: int
    clinical_synthesis: Optional[str] = ""
    metrics_reference: Dict[str, MetricReference]
    total_attempts_used: int
    cached: Optional[bool] = False