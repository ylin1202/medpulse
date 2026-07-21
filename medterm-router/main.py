import hashlib
import json
import uuid
import time
import os

from contextlib import asynccontextmanager
from dotenv import load_dotenv
import asyncpg
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from fastapi.middleware.cors import CORSMiddleware

from agent.graph import app as agent_app
from agent.vector_rag import factcheck_service

# ====================================================================
# 1. 系統環境與資料庫連線設定檔
# ====================================================================

# 載入 .env 檔案中的環境變數
load_dotenv()

# PostgreSQL 連線設定
DB_CONFIG = {
    "database": os.getenv("DB_NAME", "med_db"),
    "user": os.getenv("DB_USER", "yilin"),
    "password": os.getenv("DB_PASSWORD", ""),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT") or 5432)
}

# Redis 連線設定（優先讀取 REDIS_URL，若無則組合 REDIS_HOST 與 REDIS_PORT）
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_URL = os.getenv("REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}")

# ====================================================================
# 2. Dependency Injection (依賴注入項目)
# ====================================================================
async def get_db_pool(request: Request) -> asyncpg.Pool:
    """從 app.state 安全獲取資料庫連線池"""
    return request.app.state.db_pool

async def get_redis(request: Request) -> aioredis.Redis:
    """從 app.state 安全獲取 Redis 客戶端"""
    return request.app.state.redis

# ====================================================================
# 3. Lifecycle 生命週期管理器
# ====================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Startup] Establishing PostgreSQL asyncpg connection pool...")
    app.state.db_pool = await asyncpg.create_pool(**DB_CONFIG)
    print("[Startup] PostgreSQL connection pool established successfully!")

    print("[Startup] Connecting to Redis cache server...")
    app.state.redis = aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    print("[Startup] Redis connected successfully!")

    yield

    print("[Shutdown] Closing PostgreSQL connection pool...")
    await app.state.db_pool.close()
    print("[Shutdown] Closing Redis connection...")
    await app.state.redis.close()
    print("[Shutdown] All backend resources released gracefully.")

# ====================================================================
# 4. 初始化 FastAPI 主應用程式實例與全域設定
# ====================================================================
app = FastAPI(
    title="Medical Agent Dual-RAG API",
    description="結合微調 Gemma-3、LangGraph 自適應狀態機與 pgvector 語意闢謠的高效能雙引擎醫療 API",
    version="2.2.0",
    lifespan=lifespan,
)

# 加上 CORS 設定讓 Flutter 存取
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生產環境可替換為特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware：自動注入 X-Correlation-ID 追蹤碼與請求耗時計算
@app.middleware("http")
async def add_correlation_id_and_timer(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id
    
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    
    print(f" [{correlation_id}] {request.method} {request.url.path} latency: {process_time:.4f}s")
    return response

# 全域未預期錯誤攔截器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    correlation_id = getattr(request.state, "correlation_id", "UNKNOWN")
    print(f"[{correlation_id}] Internal Server Error Cause: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "An unexpected error occurred on the server. Please try again later.",
            "correlation_id": correlation_id
        }
    )

# ====================================================================
# 5. Redis-Based Fixed Window Rate Limiter
# ====================================================================
async def is_rate_limited(redis_client: aioredis.Redis, key: str, limit: int, window: int) -> bool:
    """
    基於 Redis 的固定窗口限流算法 (全英文日誌與降級容錯設計)
    """
    try:
        current_requests = await redis_client.incr(key)
        if current_requests == 1:
            await redis_client.expire(key, window)
            
        if current_requests > limit:
            return True
        return False
    except Exception as e:
        # 降級容錯思維：Redis 異常時放行請求，避免阻斷服務，但記錄警告 Log
        print(f"[RateLimiter] Redis error encountered (bypassed protection): {e}")
        return False

# ====================================================================
# 6. Pydantic Schemas
# ====================================================================
class ClinicalTextRequest(BaseModel):
    clinical_text: str = Field(..., min_length=1)

class MetricReference(BaseModel):
    lower: Optional[float] = None
    upper: Optional[float] = None
    unit: Optional[str] = None
    definition: Optional[str] = None

class AnalysisResponse(BaseModel):
    status: str
    detected_metrics_count: int
    metrics_reference: Dict[str, MetricReference]
    total_attempts_used: int
    cached: bool = False

class FactCheckRequest(BaseModel):
    query: str = Field(..., min_length=1)

# ====================================================================
# 7. API Endpoints
# ====================================================================

@app.get("/health", summary="伺服器健康檢查")
async def health_check():
    return {"status": "healthy", "service": "Medical Agent API v2.2"}

# 🩺 端點 1：臨床病歷指標解析 (已完美注入 Redis Rate Limiter 防護欄與 db_pool 依賴)
@app.post("/api/v1/analyze", response_model=AnalysisResponse, status_code=status.HTTP_200_OK)
async def analyze_clinical_text(
    payload: ClinicalTextRequest,
    request: Request,
    redis_client: aioredis.Redis = Depends(get_redis),
    db_pool: asyncpg.Pool = Depends(get_db_pool)  # 1. 注入 PostgreSQL 連線池 Dependency
):
    text = payload.clinical_text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Clinical text content cannot be empty.")

    correlation_id = request.state.correlation_id
    
    # [限流防護防線]
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"rate_limit:analyze:{client_ip}"
    
    # 設定防護：同一個 IP 每 60 秒只能請求最多 5 次
    if await is_rate_limited(redis_client, rate_limit_key, limit=5, window=60):
        print(f"[{correlation_id}] IP {client_ip} has been rate limited. Request rejected.")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. You are allowed to submit 5 requests per minute."
        )

    cache_key = f"medical_rag:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"

    # 1. 嘗試快取命中
    cached_result = await redis_client.get(cache_key)
    if cached_result:
        print(f"⚡ [{correlation_id}] [Redis Cache HIT] Query result resolved via shared cache.")
        response_data = json.loads(cached_result)
        response_data["cached"] = True
        return response_data

    # 2. 快取未命中，調用 Agent 大腦
    print(f"🐢 [{correlation_id}] [Redis Cache MISS] Invoking Gemma-3 and LangGraph state machine...")
    inputs = {
        "clinical_text": text,
        "retry_count": 0,
        "json_valid": False,
        "is_correction": False,
        "db_pool": db_pool  # 2. 將 db_pool 帶入 LangGraph Agent 狀態機！
    }

    result = await agent_app.ainvoke(inputs)
    final_analysis = result["final_analysis"]
    final_analysis["cached"] = False

    # 3. 寫入快取 (快取有效期設定為 1 小時 / 3600秒)
    await redis_client.setex(cache_key, 3600, json.dumps(final_analysis))
    return final_analysis


# 端點 2：健康闢謠語意檢索
@app.post("/api/v1/factcheck", status_code=status.HTTP_200_OK)
async def factcheck_endpoint(
    payload: FactCheckRequest, 
    request: Request,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):
    user_query = payload.query.strip()
    if not user_query:
        raise HTTPException(status_code=400, detail="Query statement cannot be empty.")

    correlation_id = request.state.correlation_id
    print(f"[{correlation_id}] Executing pgvector factcheck retrieval for query: '{user_query}'")
    
    # 呼叫 pgvector 檢索
    result = await factcheck_service.search(user_query, db_pool, correlation_id=correlation_id)
    
    # 若查無資料，回傳空陣列以利前端 UI 判斷
    if not result.get("found"):
        return {"status": "success", "data": []}

    # 將 pgvector 的結果包裝成 Flutter FactCheckModel 能無縫解析的格式
    formatted_item = {
        "id": correlation_id,
        "claim": result.get("matched_claim"),
        "verdict": result.get("verdict"),
        "summary": result.get("explanation", "")[:120] + "...",  # 摘要切片
        "explanation": result.get("explanation"),
        "source": "Medical Fact-Check Center",
        "claim_url": result.get("source_url", ""),
        "score": result.get("similarity_score")
    }

    return {"status": "success", "data": [formatted_item]}