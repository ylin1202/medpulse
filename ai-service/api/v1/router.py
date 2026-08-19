from fastapi import APIRouter
from app.api.v1.endpoints import clinical, factcheck

api_router = APIRouter()
api_router.include_router(clinical.router, tags=["Clinical Analysis"])
api_router.include_router(factcheck.router, tags=["Fact Checking"])