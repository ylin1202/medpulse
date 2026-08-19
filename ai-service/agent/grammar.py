import json
from llama_cpp import LlamaGrammar

# 規範 Gemma-3 必須輸出的 JSON Schema 格式
EXTRACTION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "thought": {
            "type": "string",
            "description": "Short reasoning steps for medical entity identification."
        },
        "query": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of standardized medical metrics extracted from input."
        }
    },
    "required": ["query"]
}

def get_json_grammar() -> LlamaGrammar:
    """編譯並返回用於 llama.cpp 的 JSON Constrained Decoding Grammar"""
    try:
        return LlamaGrammar.from_json_schema(json.dumps(EXTRACTION_JSON_SCHEMA))
    except Exception:
        return LlamaGrammar.from_json_schema(EXTRACTION_JSON_SCHEMA)

# 模組預先編譯好供全域複用
JSON_GRAMMAR = get_json_grammar()