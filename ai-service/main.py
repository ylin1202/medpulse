from contextlib import asynccontextmanager
import logging
import time
import uuid

import asyncpg
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import redis.asyncio as aioredis

from app.api.v1.router import api_router
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for initializing and tearing down asynchronous
    database connection pools and Redis cache clients.
    """
    logger.info("[Startup] Establishing PostgreSQL AsyncPG connection pool...")
    app.state.db_pool = await asyncpg.create_pool(**settings.asyncpg_dsn_dict)
    logger.info("[Startup] PostgreSQL connection pool established successfully!")

    logger.info("[Startup] Connecting to Redis cache server...")
    app.state.redis = aioredis.from_url(
        settings.redis_connection_url,
        encoding="utf-8",
        decode_responses=True
    )
    logger.info("[Startup] Redis connected successfully!")

    yield

    logger.info("[Shutdown] Closing PostgreSQL connection pool...")
    await app.state.db_pool.close()
    logger.info("[Shutdown] Closing Redis connection...")
    await app.state.redis.close()
    logger.info("[Shutdown] All backend resources released gracefully.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Dual-Engine Medical API combining fine-tuned Gemma-3, "
        "LangGraph adaptive state machines, and pgvector semantic fact-checking."
    ),
    version=settings.VERSION,
    lifespan=lifespan,
)

# Cross-Origin Resource Sharing (CORS) configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_correlation_id_and_timer(request: Request, call_next):
    """
    HTTP middleware attaching distributed tracing Correlation IDs and
    measuring execution latency across request lifecycles.
    """
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id
    
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    
    logger.info(f"[{correlation_id}] {request.method} {request.url.path} latency: {process_time:.4f}s")
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to capture unhandled errors and return structured diagnostics."""
    correlation_id = getattr(request.state, "correlation_id", "UNKNOWN")
    logger.error(f"[{correlation_id}] Internal Server Error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "An unexpected error occurred on the server. Please try again later.",
            "correlation_id": correlation_id
        }
    )


# Register API v1 versioned routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", summary="Service Health Check")
async def health_check():
    """Endpoint verifying service availability, metadata, and active deployment version."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }