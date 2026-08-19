from pydantic import BaseModel, Field
from typing import Dict, Optional

class ClinicalTextRequest(BaseModel):
    clinical_text: str = Field(..., min_length=1)

class MetricReference(BaseModel):
    lower: Optional[float] = None
    upper: Optional[float] = None
    unit: Optional[str] = None
    definition: Optional[str] = None
    match_type: Optional[str] = "exact"
    rrf_score: Optional[float] = None

class AnalysisResponse(BaseModel):
    status: str
    detected_metrics_count: int
    metrics_reference: Dict[str, MetricReference]
    total_attempts_used: int
    cached: bool = False