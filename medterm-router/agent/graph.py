import os
import re
import json
import time
import asyncio
from typing import TypedDict, List, Dict, Any, Optional
import asyncpg
from llama_cpp import Llama, LlamaGrammar
from langgraph.graph import StateGraph, START, END
from agent.database import query_medical_metrics_async, hybrid_search_fallback_async
from sentence_transformers import SentenceTransformer

# ====================================================================
# 0. 定義嚴格的 JSON Schema 與預編譯 Grammar (Constrained Decoding)
# ====================================================================
JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "thought": {"type": "string"},
        "query": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["query"]
}

try:
    JSON_GRAMMAR = LlamaGrammar.from_json_schema(json.dumps(JSON_SCHEMA))
except Exception:
    JSON_GRAMMAR = LlamaGrammar.from_json_schema(JSON_SCHEMA)

# ====================================================================
# 1. 設定模型路徑與載入 Embedding 模型
# ====================================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_FILENAME = os.getenv("LLM_MODEL_FILE", "gemma-3-4b-it.Q4_K_M.gguf")
MODEL_PATH = os.path.join(BASE_DIR, "model", MODEL_FILENAME)

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Cannot find model file! Verified path: {MODEL_PATH}")

print(f"[Startup] Loading local fine-tuned LLM brain from: {MODEL_PATH} ...")
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=2048,
    verbose=False
)

# 載入輕量 384-dim Embedding 模型 (專供 pgvector Hybrid Fallback 使用)
print("[Startup] Loading SentenceTransformer embedding model (all-MiniLM-L6-v2)...")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# 非同步鎖，防止多併發請求同時觸發底層推論崩潰
llm_lock = asyncio.Lock()

# ====================================================================
# 2. 定義 Agent 狀態大腦 (State)
# ====================================================================
class AgentState(TypedDict, total=False):
    clinical_text: str             # 原始輸入病歷
    extracted_metrics: List[str]   # 大腦抓出的指標
    rag_data: Dict[str, Any]       # PostgreSQL 撈出的正常值與定義
    final_analysis: Dict[str, Any] # 最終比對報告
    retry_count: int               # 重試次數
    json_valid: bool               # 標記 JSON 是否解析成功
    is_correction: bool            # 標記是否處於自我修正狀態
    db_pool: Optional[Any]         # PostgreSQL 連線池

# ====================================================================
# 3. Helper Functions: Prompt Injection Detection (防護欄機制)
# ====================================================================
def is_potential_injection(text: str) -> bool:
    injection_patterns = [
        r"ignore current instruction",
        r"ignore the prompt",
        r"forget previous instruction",
        r"forget the above instruction", 
        r"system override",
        r"you are now an assistant",
        r"bypass restriction",          
        r"bypass guardrails"            
    ]
    text_lower = text.lower()
    for pattern in injection_patterns:
        if re.search(pattern, text_lower):
            return True
    return False

# ====================================================================
# Node 0: Guardrail 安全過濾節點
# ====================================================================
async def guardrail_node(state: AgentState) -> Dict[str, Any]:
    text = state.get('clinical_text', '').strip()
    print(f"\n [Node 0] Triggering input guardrail safety verification...")
    
    if is_potential_injection(text):
        print("  └─ [ALERT] Potential Prompt Injection detected! Aborting state machine execution immediately.")
        return {
            "extracted_metrics": [],
            "json_valid": False,
            "retry_count": 99,
            "is_correction": False
        }
        
    print("  └─ Security check passed. Proceeding to entity extraction.")
    return {"is_correction": False}

# ====================================================================
# 關卡 1: 實體提取節點 (套用 LlamaGrammar 強制約束與延遲監控)
# ====================================================================
async def extract_metrics_node(state: AgentState) -> Dict[str, Any]:
    text = state.get('clinical_text', '').strip()
    current_retry = state.get("retry_count", 0)
    is_correction = state.get("is_correction", False)
    
    if current_retry == 99:
        return {
            "extracted_metrics": [],
            "json_valid": True,
            "retry_count": 99,
            "is_correction": False
        }
    
    print(f"\n [Node 1] Extracting medical metrics via Constrained Decoding... (Attempt #{current_retry + 1})")
    
    if len(text) < 4 or not re.search(r'[a-zA-Z0-9]', text):
        print("  └─ [Guard 1] Input text too short or invalid. Empty query assumed.")
        return {
            "extracted_metrics": [],
            "json_valid": True,
            "retry_count": current_retry + 1,
            "is_correction": False
        }

    temp = 0.3 if is_correction else 0.1

    instruction = "Extract valid medical metrics from the clinical text. Output JSON only."
    prompt = (
        "Below is an instruction that describes a task, paired with an input that provides further context. "
        "Write a response that appropriately completes the request.\n\n"
        f"### Instruction:\n{instruction}\n\n"
        f"### Input:\n{text}\n\n"
        "### Response:\n"
    )

    extracted = []
    json_valid = False

    try:
        start_time = time.time()
        async with llm_lock:
            response = await asyncio.to_thread(
                llm,
                prompt, 
                max_tokens=256, 
                stop=["\n\n", "###"],
                temperature=temp,
                grammar=JSON_GRAMMAR
            )
        latency = time.time() - start_time
        
        raw_text = response['choices'][0]['text'].strip()
        usage = response.get("usage", {})
        print(f"  └─ Inference Latency: {latency:.4f}s | Tokens: {usage.get('total_tokens', 'N/A')}")
        print(f"  └─ LLM Constrained Output: {raw_text}")

        parsed = json.loads(raw_text)
        extracted = parsed.get("query", [])
        
        if isinstance(extracted, list):
            json_valid = True
            
        print(f"  └─ Extracted Metrics: {extracted}")
    except Exception as e:
        print(f"  └─ Extraction/Parsing Failed: {e}")

    return {
        "extracted_metrics": extracted,
        "json_valid": json_valid,
        "retry_count": current_retry + 1,
        "is_correction": not json_valid
    }

# ====================================================================
# 4. LangGraph 條件路由 (自適應重試與降級)
# ====================================================================
def check_extraction_quality(state: AgentState) -> str:
    retry_count = state.get("retry_count", 0)
    
    if retry_count == 99:
        return "continue_to_rag"
        
    json_valid = state.get("json_valid", False)
    
    if json_valid:
        return "continue_to_rag"
    
    if retry_count < 2:
        print(f"[LangGraph Reflection] Output invalid. Bouncing back to Node 1 for retry #{retry_count + 1}...")
        return "retry_extraction"
    
    print("[LangGraph CircuitBreaker] Maximum retries reached. Forcing fallback pipeline.")
    return "continue_to_rag"

# ====================================================================
# 關卡 2: RAG 檢索節點 (精確比對 + Hybrid Search Fallback + RRF 門檻過濾)
# ====================================================================
RRF_THRESHOLD = 0.0163  # 信心門檻：低於此分數視為無關噪聲，直接丟棄

async def query_database_node(state: AgentState) -> Dict[str, Any]:
    print("\n [Node 2] Initiating PostgreSQL Relational RAG retrieval...")
    metrics = state.get("extracted_metrics", [])
    db_pool = state.get("db_pool")
    
    if not metrics:
        print("  └─ No valid metrics extracted. Skipping RAG stage safely.")
        return {"rag_data": {}}
        
    print(f"  └─ 🔍 [Step 1] Exact batch querying for: {metrics}")
    rag_results = await query_medical_metrics_async(metrics, db_pool)
    
    # 找出精確比對未命中的指標
    missing_metrics = [m for m in metrics if m not in rag_results]
    
    if missing_metrics and db_pool is not None:
        print(f"  └─ ⚠️ [Step 2B] Triggering Hybrid Search Fallback for: {missing_metrics}")
        for missing in missing_metrics:
            # 產生 Query 語意向量
            emb = await asyncio.to_thread(embed_model.encode, missing)
            embedding_list = emb.tolist()
            
            # 明確傳入 top_k=1
            fallback_matches = await hybrid_search_fallback_async(
                query_text=missing,
                query_embedding=embedding_list,
                db_pool=db_pool,
                top_k=1
            )
            
            # 檢查 Top 1 匹配項是否達標
            if fallback_matches:
                best = fallback_matches[0]
                label = best["metric_label"]
                rrf_score = best["rrf_score"]
                
                # 門檻防護：分數達標才納入 RAG
                if rrf_score >= RRF_THRESHOLD:
                    print(f"     └─ 🎯 Hybrid Search Matched '{missing}' -> '{label}' (RRF: {rrf_score:.4f} >= {RRF_THRESHOLD})")
                    rag_results[label] = {
                        "lower": best["lower"],
                        "upper": best["upper"],
                        "unit": best["unit"],
                        "definition": best["definition"],
                        "match_type": "hybrid_rrf",
                        "rrf_score": rrf_score
                    }
                else:
                    print(f"     └─ 🚫 Discarded weak match '{missing}' -> '{label}' (RRF: {rrf_score:.4f} < {RRF_THRESHOLD})")

    if not rag_results:
        print("  └─ No metrics found after exact & hybrid retrieval. RAG payload empty.")
    else:
        print(f"  └─ RAG Fetch Completed: {list(rag_results.keys())}")
        
    return {"rag_data": rag_results}

# ====================================================================
# 關卡 3: 邏輯分析與報告打包節點
# ====================================================================
def analyze_and_compare_node(state: AgentState) -> Dict[str, Any]:
    print("\n [Node 3] Assembling final RAG + Agent structured report...")
    rag_data = state.get("rag_data", {})
    retry_count = state.get("retry_count", 1)
    
    status_str = "security_blocked" if retry_count == 99 else ("success" if rag_data else "no_metrics_found")
    
    analysis = {
        "status": status_str,
        "detected_metrics_count": len(rag_data),
        "metrics_reference": rag_data,
        "total_attempts_used": 0 if retry_count == 99 else retry_count
    }
    return {"final_analysis": analysis}

# ====================================================================
# 5. 組裝 LangGraph 狀態機工作流
# ====================================================================
workflow = StateGraph(AgentState)

workflow.add_node("guardrail", guardrail_node)
workflow.add_node("extract_metrics", extract_metrics_node)
workflow.add_node("query_database", query_database_node)
workflow.add_node("analyze_compare", analyze_and_compare_node)

workflow.add_edge(START, "guardrail")
workflow.add_edge("guardrail", "extract_metrics")

workflow.add_conditional_edges(
    "extract_metrics",
    check_extraction_quality,
    {
        "retry_extraction": "extract_metrics",
        "continue_to_rag": "query_database" 
    }
)

workflow.add_edge("query_database", "analyze_compare")
workflow.add_edge("analyze_compare", END)

app = workflow.compile()

# ====================================================================
# 6. 本地測試進入點
# ====================================================================
async def main_test():
    test_patient_note = "Patient was brought to the ER with high fever. Urgent lab tests requested for Glucose, White Blood Cells, and Potassium."
    print(f"Testing clinical input: {test_patient_note}")
    
    db_config = {
        "database": os.getenv("DB_NAME", "med_db"),
        "user": os.getenv("DB_USER", "yilin"),
        "password": os.getenv("DB_PASSWORD", ""),
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT") or 5432)
    }
    
    pool = None
    try:
        pool = await asyncpg.create_pool(**db_config)
    except Exception as e:
        print(f"[Warning] Could not connect to local DB for standalone test: {e}")

    inputs = {
        "clinical_text": test_patient_note,
        "retry_count": 0,
        "json_valid": False,
        "is_correction": False,
        "db_pool": pool
    }
    
    result = await app.ainvoke(inputs)
    print("\n ================= Final RAG Analysis Report =================")
    print(json.dumps(result["final_analysis"], indent=2, ensure_ascii=False))

    if pool:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(main_test())