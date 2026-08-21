import json
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values

# Load environment variables
load_dotenv()


def extract_drug_data(item):
    """Clean and extract a single OpenFDA drug JSON record."""
    openfda = item.get("openfda", {})
    
    # Extract the first element from arrays as a single string
    brand_name = openfda.get("brand_name", [None])[0]
    generic_name = openfda.get("generic_name", [None])[0]
    manufacturer = openfda.get("manufacturer_name", [None])[0]
    product_type = openfda.get("product_type", [None])[0]
    route = openfda.get("route", [None])[0]

    # Join multiline text arrays into paragraphs
    active_ingredient = "\n".join(item.get("active_ingredient", [])) or None
    purpose = "\n".join(item.get("purpose", [])) or None
    indications = "\n".join(item.get("indications_and_usage", [])) or None
    warnings = "\n".join(item.get("warnings", [])) or None
    do_not_use = "\n".join(item.get("do_not_use", [])) or None
    boxed_warning = "\n".join(item.get("boxed_warning", [])) or None

    return (
        item.get("id"),
        brand_name,
        generic_name,
        manufacturer,
        product_type,
        route,
        active_ingredient,
        purpose,
        indications,
        warnings,
        do_not_use,
        boxed_warning,
        json.dumps(openfda)  # Store as JSONB
    )


def import_json_to_db(json_file_path):
    """Parse JSON dataset and perform batch ingestion into PostgreSQL."""
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5432),
        dbname=os.getenv("DB_NAME", "med_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "")
    )
    cursor = conn.cursor()

    # Create table schema, constraints, and indexes idempotently
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS drugs (
        id SERIAL PRIMARY KEY,
        openfda_id VARCHAR(100),
        brand_name VARCHAR(255),
        generic_name VARCHAR(255),
        manufacturer_name VARCHAR(255),
        product_type VARCHAR(100),
        route VARCHAR(100),
        active_ingredient TEXT,
        purpose TEXT,
        indications_and_usage TEXT,
        warnings TEXT,
        do_not_use TEXT,
        boxed_warning TEXT,
        raw_openfda JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Ensure unique constraint on openfda_id safely
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'unique_openfda_id'
        ) THEN
            ALTER TABLE drugs ADD CONSTRAINT unique_openfda_id UNIQUE (openfda_id);
        END IF;
    END $$;

    CREATE INDEX IF NOT EXISTS idx_drugs_brand_name ON drugs(brand_name);
    CREATE INDEX IF NOT EXISTS idx_drugs_generic_name ON drugs(generic_name);
    CREATE INDEX IF NOT EXISTS idx_drugs_openfda_id ON drugs(openfda_id);
    """
    cursor.execute(create_table_sql)

    # Load JSON source file
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    results = data.get("results", [])
    print(f"Preparing to import {len(results)} drug records...")

    # Batch insert with conflict avoidance on unique OpenFDA IDs
    insert_sql = """
    INSERT INTO drugs (
        openfda_id, brand_name, generic_name, manufacturer_name, product_type, route,
        active_ingredient, purpose, indications_and_usage, warnings, do_not_use, boxed_warning, raw_openfda
    ) VALUES %s
    ON CONFLICT (openfda_id) DO NOTHING;
    """

    drug_records = [extract_drug_data(item) for item in results if item.get("id")]
    
    execute_values(cursor, insert_sql, drug_records)
    conn.commit()

    print(f"Successfully imported {len(drug_records)} drug records into 'drugs' table.")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    JSON_PATH = os.path.join(CURRENT_DIR, "drug-label-0014.json")
    import_json_to_db(JSON_PATH)