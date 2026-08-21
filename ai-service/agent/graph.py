import os
import re
import json
import time
import inspect
import asyncio
from typing import TypedDict, List, Dict, Any, Optional
import asyncpg
from llama_cpp import Llama, LlamaGrammar
from langgraph.graph import StateGraph, START, END
from sentence_transformers import SentenceTransformer
from google import genai
from google.genai.errors import ClientError, APIError

from app.core.config import settings
from app.agent.database import query_medical_metrics_async, hybrid_search_fallback_async
from app.agent.grammar import JSON_GRAMMAR


# ====================================================================
# 1. 載入模型與 Gemini Client 初始化
# ====================================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "model", settings.LLM_MODEL_FILE)

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Cannot find model file! Verified path: {MODEL_PATH}")

print(f"[Startup] Loading local fine-tuned LLM brain from: {MODEL_PATH} ...")
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=2048,
    verbose=False
)

print(f"[Startup] Loading SentenceTransformer embedding model ({settings.EMBEDDING_MODEL_NAME})...")
embed_model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)

# 讀取並配置 Gemini Client
raw_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
gemini_api_key = raw_key.strip().strip('"\'')
gemini_client = genai.Client(api_key=gemini_api_key) if gemini_api_key else None

llm_lock = asyncio.Lock()

# ====================================================================
# 2. Agent 狀態大腦
# ====================================================================
class AgentState(TypedDict, total=False):
    clinical_text: str             # 原始輸入病歷
    extracted_metrics: List[str]   # 大腦抓出的指標
    rag_data: Dict[str, Any]       # PostgreSQL 撈出的正常值與定義
    clinical_synthesis: str        # Gemini 臨床生成解讀 (A+G 產物)
    final_analysis: Dict[str, Any] # 最終比對報告
    retry_count: int               # 重試次數
    json_valid: bool               # 標記 JSON 是否解析成功
    is_correction: bool            # 標記是否處於自我修正狀態
    db_pool: Optional[Any]         # PostgreSQL 連線池

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

def check_extraction_quality(state: AgentState) -> str:
    retry_count = state.get("retry_count", 0)
    if retry_count == 99:
        return "continue_to_rag"
    if state.get("json_valid", False):
        return "continue_to_rag"
    if retry_count < 2:
        print(f"[LangGraph Reflection] Output invalid. Bouncing back to Node 1 for retry #{retry_count + 1}...")
        return "retry_extraction"
    
    print("[LangGraph CircuitBreaker] Maximum retries reached. Forcing fallback pipeline.")
    return "continue_to_rag"

RRF_THRESHOLD = 0.0163

async def query_database_node(state: AgentState) -> Dict[str, Any]:
    print("\n [Node 2] Initiating PostgreSQL Relational RAG retrieval...")
    metrics = state.get("extracted_metrics", [])
    db_pool = state.get("db_pool")
    
    if not metrics:
        print("  └─ No valid metrics extracted. Skipping RAG stage safely.")
        return {"rag_data": {}}
        
    print(f"  └─ 🔍 [Step 1] Exact batch querying for: {metrics}")
    rag_results = await query_medical_metrics_async(metrics, db_pool)
    
    missing_metrics = [m for m in metrics if m not in rag_results]
    
    if missing_metrics and db_pool is not None:
        print(f"  └─ ⚠️ [Step 2B] Triggering Hybrid Search Fallback for: {missing_metrics}")
        for missing in missing_metrics:
            emb = await asyncio.to_thread(embed_model.encode, missing)
            embedding_list = emb.tolist()
            
            fallback_matches = await hybrid_search_fallback_async(
                query_text=missing,
                query_embedding=embedding_list,
                db_pool=db_pool,
                top_k=1
            )
            
            if fallback_matches:
                best = fallback_matches[0]
                label = best["metric_label"]
                rrf_score = best["rrf_score"]
                
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
# 3. Augmentation & Generation 節點 (RAG 的 A 與 G)
# ====================================================================
async def clinical_synthesis_node(state: AgentState) -> Dict[str, Any]:
    print("\n [Node 3] Performing RAG Augmentation & Generation (Gemini Clinical Synthesis)...")
    clinical_text = state.get("clinical_text", "").strip()
    rag_data = state.get("rag_data", {})
    
    if not rag_data or not gemini_client:
        print("  └─ No retrieved metrics or Gemini client not ready. Skipping clinical generation.")
        return {"clinical_synthesis": ""}

    # 1. Augmentation (增強上下文拼接)
    metrics_benchmarks = []
    for name, info in rag_data.items():
        ref_range = f"{info.get('lower', 'N/A')} - {info.get('upper', 'N/A')} {info.get('unit', '')}"
        desc = info.get('definition', '')[:120]
        metrics_benchmarks.append(f"- {name}: Normal Range ({ref_range}), Clinical Role: {desc}")
    
    context_str = "\n".join(metrics_benchmarks)

    prompt = inspect.cleandoc(f"""
    You are an expert clinical decision support assistant. Explain why the following lab tests were ordered for this specific clinical case and provide concise diagnostic insights.

    ### CLINICAL CASE / NOTE:
    "{clinical_text}"

    ### RETRIEVED LAB BENCHMARKS & CONTEXT:
    {context_str}

    ### REQUIREMENTS:
    1. Explain the clinical correlation between the patient's symptoms (e.g. fever, acute presentation) and these specific lab metrics.
    2. Briefly mention key risks or what abnormal findings would indicate in this context.
    3. Keep the tone concise, objective, and professional (around 80-120 words).
    """)

    # 2. Generation (呼叫 Gemini 生成，含 429 容錯備援)
    candidate_models = ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-2.5-flash"]
    synthesis_result = ""

    for model_name in candidate_models:
        try:
            response = await asyncio.to_thread(
                lambda m=model_name: gemini_client.models.generate_content(
                    model=m,
                    contents=prompt
                )
            )
            if response and response.text:
                synthesis_result = response.text.strip()
                print(f"  └─ Successfully generated synthesis with {model_name}.")
                break
        except (ClientError, APIError) as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print(f"  └─ Model {model_name} quota exhausted (429). Retrying next model...")
                continue
        except Exception as e:
            print(f"  └─ Synthesis failed on {model_name}: {e}")

    return {"clinical_synthesis": synthesis_result}

def analyze_and_compare_node(state: AgentState) -> Dict[str, Any]:
    print("\n [Node 4] Assembling final RAG + Agent structured report...")
    rag_data = state.get("rag_data", {})
    synthesis = state.get("clinical_synthesis", "")
    retry_count = state.get("retry_count", 1)
    
    status_str = "security_blocked" if retry_count == 99 else ("success" if rag_data else "no_metrics_found")
    
    analysis = {
        "status": status_str,
        "detected_metrics_count": len(rag_data),
        "clinical_synthesis": synthesis, # 注入 AI 生成解讀
        "metrics_reference": rag_data,
        "total_attempts_used": 0 if retry_count == 99 else retry_count
    }
    return {"final_analysis": analysis}

# ====================================================================
# 4. 構建狀態圖 (請確保節點與 Edge 都有連到 synthesis)
# ====================================================================
workflow = StateGraph(AgentState)

workflow.add_node("guardrail", guardrail_node)
workflow.add_node("extract_metrics", extract_metrics_node)
workflow.add_node("query_database", query_database_node)
workflow.add_node("synthesis", clinical_synthesis_node)         # 1. 確保有註冊 synthesis 節點
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

# ⚠️ 注意這裡：舊的是 query_database -> analyze_compare
# 必須改成：query_database -> synthesis -> analyze_compare
workflow.add_edge("query_database", "synthesis")                # 2. 檢索完接 synthesis
workflow.add_edge("synthesis", "analyze_compare")               # 3. synthesis 完再接組裝報告
workflow.add_edge("analyze_compare", END)

app = workflow.compile()