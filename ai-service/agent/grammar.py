import json
from llama_cpp import LlamaGrammar

# JSON Schema enforcing structured clinical entity extraction for fine-tuned Gemma inference
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
    """Compile and return JSON Constrained Decoding Grammar for llama.cpp execution."""
    try:
        return LlamaGrammar.from_json_schema(json.dumps(EXTRACTION_JSON_SCHEMA))
    except Exception:
        return LlamaGrammar.from_json_schema(EXTRACTION_JSON_SCHEMA)


# Pre-compile grammar for reuse across inference threads
JSON_GRAMMAR = get_json_grammar()