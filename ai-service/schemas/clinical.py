from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


# Request payload schema for clinical text analysis
class ClinicalTextRequest(BaseModel):
    clinical_text: str = Field(..., description="The raw clinical text or medical note to analyze")


# Schema for reference ranges, units, and clinical definitions of a single lab metric
class MetricReference(BaseModel):
    lower: Optional[float] = None
    upper: Optional[float] = None
    unit: Optional[str] = None
    definition: Optional[str] = None
    match_type: Optional[str] = None
    rrf_score: Optional[float] = None


# Analysis response payload schema (including Dual-RAG generated clinical synthesis)
class AnalysisResponse(BaseModel):
    status: str
    detected_metrics_count: int
    clinical_synthesis: Optional[str] = ""
    metrics_reference: Dict[str, MetricReference]
    total_attempts_used: int
    cached: Optional[bool] = False