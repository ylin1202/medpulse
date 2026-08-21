from typing import List
import pandas as pd
from sentence_transformers import SentenceTransformer

# 1. Load Sentence Transformer model
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
print(f"Loading embedding model: {MODEL_NAME}...")
model = SentenceTransformer(MODEL_NAME)

# 2. Ingest raw PUBHEALTH TSV dataset
TSV_FILE_PATH = "data/train.tsv"
print(f"Reading TSV dataset from {TSV_FILE_PATH}...")
df = pd.read_csv(TSV_FILE_PATH, sep="\t")


# 3. Document chunking logic (Sliding Window)
def split_into_chunks(text: str, chunk_size: int = 250, overlap: int = 50) -> List[str]:
    """Split text into overlapping token/character chunks using a sliding window strategy."""
    if not text or not text.strip():
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += (chunk_size - overlap)
    return chunks


# 4. Flatten document chunks and construct contextual payloads
print("Splitting documents into chunks...")
chunk_records = []

for _, row in df.iterrows():
    claim = str(row.get("claim", "")).strip()
    explanation = str(row.get("explanation", "")).strip()
    label = str(row.get("label", "unproven")).strip()
    claim_url = str(row.get("claim_url", "")).strip()
    main_text = str(row.get("main_text", "")).strip()

    # Prioritize main_text for chunking; fallback to combined claim and explanation
    source_text = main_text if main_text else f"{claim} {explanation}"
    chunks = split_into_chunks(source_text, chunk_size=250, overlap=50)

    # Ensure at least one chunk exists per record
    if not chunks:
        chunks = [claim]

    for chunk in chunks:
        # Prepend claim title to ground each chunk with global context
        text_to_embed = f"Title: {claim}\nContent: {chunk}"
        
        chunk_records.append({
            "claim": claim,
            "explanation": explanation,
            "label": label,
            "claim_url": claim_url,
            "chunk_content": chunk,
            "text_to_embed": text_to_embed
        })

chunk_df = pd.DataFrame(chunk_records)
print(f"Total chunks created: {len(chunk_df)}")

# 5. Batch vector inference
print("Generating embeddings for all chunks...")
embeddings = model.encode(
    chunk_df["text_to_embed"].tolist(),
    batch_size=128,
    show_progress_bar=True,
    normalize_embeddings=True
)

chunk_df["embedding"] = embeddings.tolist()

# 6. Export serialized Parquet dataset
OUTPUT_PARQUET_PATH = "data/factcheck_vectors.parquet"
chunk_df.to_parquet(OUTPUT_PARQUET_PATH, index=False)
print(f"Successfully generated {OUTPUT_PARQUET_PATH} with {len(chunk_df)} chunk records!")