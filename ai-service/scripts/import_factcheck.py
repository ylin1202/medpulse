import os
from dotenv import load_dotenv
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# Load environment variables
load_dotenv()

print("Loading serialized fact-checking vector dataset from Parquet...")
df = pd.read_parquet("data/factcheck_vectors.parquet")

# Establish PostgreSQL connection using environment variables with defaults
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME", "med_db"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", ""),
    host=os.getenv("DB_HOST", "localhost"),
    port=os.getenv("DB_PORT", "5432")
)
cursor = conn.cursor()

records = []
for _, row in df.iterrows():
    # Convert numpy array or raw list to standard Python list
    emb = row['embedding']
    if hasattr(emb, 'tolist'):
        emb = emb.tolist()
    
    # Format embedding as a PostgreSQL pgvector literal string: '[0.1, 0.2, ...]'
    vec_str = f"[{','.join(map(str, emb))}]"

    records.append((
        str(row.get('claim', '')),
        str(row.get('explanation', '')),
        str(row.get('label', 'unproven')),
        str(row.get('claim_url', '')),
        str(row.get('main_text', '')),
        str(row.get('sources', '')),
        vec_str  # Formatted pgvector vector literal string
    ))

insert_query = """
INSERT INTO factcheck_vectors (claim, explanation, label, claim_url, main_text, sources, embedding)
VALUES %s;
"""

print(f"Beginning batch ingestion of {len(records)} records into PostgreSQL...")
execute_values(cursor, insert_query, records, page_size=1000)
conn.commit()

cursor.close()
conn.close()
print("Successfully imported all fact-checking vector records into the 'factcheck_vectors' table.")