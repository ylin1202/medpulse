import os
import re
import json
import asyncio
from typing import TypedDict, List, Dict, Any, Optional
from llama_cpp import Llama
from langgraph.graph import StateGraph, START, END
from agent.database import query_medical_metrics_async

# ====================================================================
# 1. 設定模型路徑 (絕對路徑防呆，確保在任何目錄下執行都抓得到模型)
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

# 加上非同步鎖，防止多併發請求同時觸發 llama_cpp 底層崩潰
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
    db_pool: Optional[Any]

# ====================================================================
# 3. Helper Functions: Prompt Injection Detection (防護欄機制)
# ====================================================================
def is_potential_injection(text: str) -> bool:
    """
    Basic input sanitizer to intercept common LLM hijacking keywords.
    """
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
# Node 0: Guardrail 安全過濾節點 (新增防線)
# ====================================================================
async def guardrail_node(state: AgentState) -> Dict[str, Any]:
    text = state['clinical_text'].strip()
    print(f"\n [Node 0] Triggering input guardrail safety verification...")
    
    if is_potential_injection(text):
        print("  └─ [ALERT] Potential Prompt Injection detected! Aborting state machine execution immediately.")
        return {
            "extracted_metrics": [],
            "json_valid": False,
            "retry_count": 99,  # Use 99 as a special marker for security violation
            "is_correction": False
        }
        
    print("  └─ Security check passed. Proceeding to entity extraction.")
    return {"is_correction": False}

# ====================================================================
# 關卡 1: 實體提取節點 (已對齊英文日誌，整合安全熔斷機制)
# ====================================================================
async def extract_metrics_node(state: AgentState) -> Dict[str, Any]:
    text = state['clinical_text'].strip()
    current_retry = state.get("retry_count", 0)
    is_correction = state.get("is_correction", False)
    
    # 安全熔斷：如果是被防護欄攔截的惡意請求，跳過 LLM 推論
    if current_retry == 99:
        return {
            "extracted_metrics": [],
            "json_valid": True,  # Mark as valid to smoothly bypass to the end
            "retry_count": 99,
            "is_correction": False
        }
    
    print(f"\n [Node 1] Extracting medical metrics from text... (Attempt #{current_retry + 1})")
    
    if len(text) < 4 or not re.search(r'[a-zA-Z0-9]', text):
        print("  └─ [Guard 1] Input text too short or invalid. Empty query assumed.")
        return {
            "extracted_metrics": [],
            "json_valid": True,
            "retry_count": current_retry + 1,
            "is_correction": False
        }

    if is_correction:
        print("  └─ Self-correction triggered: Increasing temperature for retry.")
        temp = 0.3
    else:
        temp = 0.1

    instruction = "Extract valid medical metrics from the clinical text. Output JSON only."

    prompt = (
        "Below is an instruction that describes a task, paired with an input that provides further context. "
        "Write a response that appropriately completes the request.\n\n"
        f"### Instruction:\n{instruction}\n\n"
        f"### Input:\n{text}\n\n"
        "### Response:\n"
    )

    async with llm_lock:
        response = await asyncio.to_thread(
            llm,
            prompt, 
            max_tokens=512, 
            stop=["\n\n", "###"],
            temperature=temp
        )
    
    raw_text = response['choices'][0]['text'].strip()
    
    cleaned_text = raw_text
    start_idx = raw_text.find('{')
    end_idx = raw_text.rfind('}')
    
    if start_idx != -1 and end_idx != -1:
        cleaned_text = raw_text[start_idx : end_idx + 1]
    
    extracted = []
    json_valid = False
    
    try:
        parsed = json.loads(cleaned_text)
        extracted = parsed.get("query", [])
        
        if isinstance(extracted, list):
            json_valid = True
            
        print(f"  └─ LLM Raw Output: {raw_text}")
        print(f"  └─ Cleaned JSON: {cleaned_text}")
        print(f"  └─ Extracted Metrics: {extracted}")
    except Exception as e:
        print(f"  └─ LLM Raw Output: {raw_text}")
        print(f"  └─ JSON Parsing Failed: {e}")

    return {
        "extracted_metrics": extracted,
        "json_valid": json_valid,
        "retry_count": current_retry + 1,
        "is_correction": not json_valid
    }

# ====================================================================
# 4. LangGraph 條件路由 (優化自適應邏輯)
# ====================================================================
def check_extraction_quality(state: AgentState) -> str:
    retry_count = state.get("retry_count", 0)
    
    # 如果觸發了安全攔截，直接前進到 RAG (RAG 節點沒指標會直接跳過)
    if retry_count == 99:
        return "continue_to_rag"
        
    json_valid = state.get("json_valid", False)
    
    if json_valid:
        return "continue_to_rag"
    
    if retry_count < 2:
        print(f"[LangGraph Reflection] JSON corrupted. Bouncing back to Node 1 for retry #{retry_count + 1}...")
        return "retry_extraction"
    
    print("[LangGraph CircuitBreaker] Maximum retries reached. Forcing fallback pipeline.")
    return "continue_to_rag"

# ====================================================================
# 關卡 2: RAG 檢索節點 (已對齊英文日誌與修復 db_pool 傳參)
# ====================================================================
async def query_database_node(state: AgentState) -> Dict[str, Any]:
    print("\n [Node 2] Initiating PostgreSQL Relational RAG retrieval...")
    metrics = state.get("extracted_metrics", [])
    db_pool = state.get("db_pool")  # 確保有從 state 拿 db_pool
    
    if not metrics:
        print("  └─ No valid metrics extracted. Skipping RAG stage safely.")
        return {"rag_data": {}}
        
    print(f"  └─ 🔍 Querying database for metrics: {metrics}")
    
    # 關鍵：必須將 db_pool 傳入 query_medical_metrics_async！
    rag_results = await query_medical_metrics_async(metrics, db_pool)
    
    if not rag_results:
        print("  └─ Extracted metrics not found in DB whitelist. RAG payload empty.")
    else:
        print(f"  └─ RAG Fetch Successful: {list(rag_results.keys())}")
        
    return {"rag_data": rag_results}

# ====================================================================
# 關卡 3: 邏輯分析與報告打包節點
# ====================================================================
def analyze_and_compare_node(state: AgentState) -> Dict[str, Any]:
    print("\n [Node 3] Assembling final RAG + Agent structured report...")
    rag_data = state.get("rag_data", {})
    retry_count = state.get("retry_count", 1)
    
    # 如果是被資安封殺的，回傳對應的特定 status 欄位
    status_str = "security_blocked" if retry_count == 99 else ("success" if rag_data else "no_metrics_found")
    
    analysis = {
        "status": status_str,
        "detected_metrics_count": len(rag_data),
        "metrics_reference": rag_data,
        "total_attempts_used": 0 if retry_count == 99 else retry_count
    }
    return {"final_analysis": analysis}

# ====================================================================
# 🕸️ 5. 組裝 LangGraph 狀態機工作流 (新增 guardrail 邊界)
# ====================================================================
workflow = StateGraph(AgentState)

# 註冊所有 Node
workflow.add_node("guardrail", guardrail_node)
workflow.add_node("extract_metrics", extract_metrics_node)
workflow.add_node("query_database", query_database_node)
workflow.add_node("analyze_compare", analyze_and_compare_node)

# 設定進入路徑：START -> Guardrail -> ExtractMetrics
workflow.add_edge(START, "guardrail")
workflow.add_edge("guardrail", "extract_metrics")

# 設定自適應條件路由邊界
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

# 編譯工作流
app = workflow.compile()

# ====================================================================
# 6. 本地測試進入點
# ====================================================================
async def main_test():
    # 正常測試問句
    test_patient_note = "Patient came in with fatigue. Urgent lab tests requested for Glucose and Potassium."
    print(f"Testing clinical input: {test_patient_note}")
    
    inputs = {
        "clinical_text": test_patient_note,
        "retry_count": 0,
        "json_valid": False,
        "is_correction": False
    }
    
    result = await app.ainvoke(inputs)
    print("\n ================= Final RAG Analysis Report =================")
    print(json.dumps(result["final_analysis"], indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main_test())