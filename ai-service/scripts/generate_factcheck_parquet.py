import pandas as pd
from sentence_transformers import SentenceTransformer

# 1. 載入模型
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
print(f"Loading embedding model: {MODEL_NAME}...")
model = SentenceTransformer(MODEL_NAME)

# 2. 讀取原始 TSV
TSV_FILE_PATH = "data/train.tsv"
print(f"Reading TSV dataset from {TSV_FILE_PATH}...")
df = pd.read_csv(TSV_FILE_PATH, sep="\t")

# 3. 切塊邏輯 (滑動視窗)
def split_into_chunks(text: str, chunk_size: int = 250, overlap: int = 50) -> list[str]:
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

# 4. 展開切塊並組裝資料
print("Splitting documents into chunks...")
chunk_records = []

for _, row in df.iterrows():
    claim = str(row.get("claim", "")).strip()
    explanation = str(row.get("explanation", "")).strip()
    label = str(row.get("label", "unproven")).strip()
    claim_url = str(row.get("claim_url", "")).strip()
    main_text = str(row.get("main_text", "")).strip()

    # 優先切 main_text，若無則以 explanation 或 claim 作為內容
    source_text = main_text if main_text else f"{claim} {explanation}"
    chunks = split_into_chunks(source_text, chunk_size=250, overlap=50)

    # 至少保留一個 Chunk（標題本體）
    if not chunks:
        chunks = [claim]

    for chunk in chunks:
        # 關鍵：每個段落開頭附帶標題提供上下文語意
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

# 5. 批次推論產生向量
print("Generating embeddings for all chunks...")
embeddings = model.encode(
    chunk_df["text_to_embed"].tolist(),
    batch_size=128,
    show_progress_bar=True,
    normalize_embeddings=True
)

chunk_df["embedding"] = embeddings.tolist()

# 6. 輸出 Parquet
OUTPUT_PARQUET_PATH = "data/factcheck_vectors.parquet"
chunk_df.to_parquet(OUTPUT_PARQUET_PATH, index=False)
print(f"Successfully generated {OUTPUT_PARQUET_PATH} with {len(chunk_df)} chunk records!")