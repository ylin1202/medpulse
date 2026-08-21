import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values


# 1. MedlinePlus Clinical Metric Definitions
METRIC_DEFINITIONS = {
    "RDW": "A red cell distribution width (RDW) test measures how much the volume and size of your red blood cells (erythrocytes) varies.",
    "Red Blood Cells": "A red blood cell (RBC) count measures the number of red blood cells, also known as erythrocytes, in your blood. Red blood cells are made in your bone marrow, the spongy tissue inside your large bones. They contain hemoglobin, an iron-rich protein that carries oxygen from your lungs to every cell in your body. Your cells need oxygen to grow, reproduce, and make energy for you to function. An RBC count that is higher or lower than normal is often the first sign of an illness.",
    "White Blood Cells": "White blood cells are part of your immune system. They help your body fight off infections and other diseases.",
    "MCHC": "Mean Corpuscular Hemoglobin Concentration (MCHC) measures how concentrated (close together) the hemoglobin is in your red blood cells. It also includes a calculation of the size and volume of your red blood cells.",
    "Hematocrit": "Hematocrit is a blood test that measures how much of a person's blood is made up of red blood cells as opposed to plasma.",
    "Hemoglobin": "Hemoglobin is an iron-rich protein in your red blood cells. It carries oxygen from your lungs to the rest of your body.",
    "Platelet Count": "A platelet count is a lab test to measure how many platelets you have in your blood. Platelets are particles in the blood that help the blood clot. They are smaller than red or white blood cells.",
    "MCV": "MCV stands for mean corpuscular volume. An MCV blood test measures the average size of your red blood cells.",
    "MCH": "Mean corpuscular hemoglobin (MCH), which measures the average amount of hemoglobin in a single red blood cell.",
    "Chloride": "Chloride is a type of electrolyte. Electrolytes are electrically charged minerals that help control the amount of fluids and the balance of acids and bases (pH balance) in your body.",
    "Bicarbonate": "Bicarbonate is necessary to maintain the proper acid-base balance in the body, which is necessary for most biological reactions to proceed properly.",
    "Magnesium": "Magnesium helps control blood pressure and blood glucose, also called blood sugar. It's important for building strong bones, and it supports your immune system.",
    "Urea Nitrogen": "Urea nitrogen is a waste product that forms as your body breaks down proteins. It's carried in your blood and then removed by your kidneys when you urinate (pee).",
    "Calcium, Total": "Total calcium test measures all the calcium in your blood. You have two types of blood calcium that are normally present in about equal amounts: 1. Bound calcium is attached to proteins in your blood. 2. Free calcium is not attached to proteins. It's also called ionized calcium. This form of blood calcium is active in many body functions.",
    "Sodium": "Sodium is an element that the body needs to work properly. Salt contains sodium.",
    "Potassium": "Potassium is a mineral that your body needs to work properly. It is a type of electrolyte. It helps your nerves to function and muscles to contract. It helps your heartbeat stay regular.",
    "Anion Gap": "The anion gap blood test shows whether your electrolytes are out of balance or if your blood is too acidic or not acidic enough.",
    "Creatinine": "Creatinine is a normal waste product in your body. It's made when you use your muscles and some of the muscle tissue breaks down.",
    "Glucose": "Blood glucose, or blood sugar, is the main sugar found in your blood. It is your body's primary source of energy. It comes from the food you eat. Your body breaks down most of that food into glucose and releases it into your bloodstream.",
    "Phosphate": "A phosphate in blood test measures the amount of phosphate in a sample of your blood. Phosphate contains the mineral phosphorus. So, a phosphate test is sometimes called a phosphorus test."
}


def init_postgres_db():
    """
    Initialize PostgreSQL relational schema for clinical metrics and enable
    the pgvector extension with HNSW indexing for vector fact-checking.
    """
    print("1. Connecting to PostgreSQL database...")
    conn_params = {
        "dbname": os.getenv("DB_NAME", "med_db"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", ""),
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432")
    }
    
    try:
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        print("Database connection established successfully.")
        
        print("2. Creating 'medical_metrics' schema...")
        cursor.execute("DROP TABLE IF EXISTS medical_metrics CASCADE;")
        cursor.execute("""
            CREATE TABLE medical_metrics (
                id SERIAL PRIMARY KEY,
                itemid INT UNIQUE,
                metric_label VARCHAR(150),
                fluid VARCHAR(50),
                category VARCHAR(50),
                ref_range_lower FLOAT,
                ref_range_upper FLOAT,
                valueuom VARCHAR(30),
                metric_definition TEXT
            );
        """)
        
        print("3. Loading cleaned CSV dataset and mapping MedlinePlus clinical definitions...")
        df = pd.read_csv('data/cleaned_metrics_base.csv')
        
        # Map authoritative definitions by metric label with a fallback default
        df['metric_definition'] = df['label'].map(METRIC_DEFINITIONS).fillna("Standard clinical metric definition not found.")
        
        # Explicit column ordering to guarantee alignment with the SQL INSERT statement
        df_ordered = df[[
            'itemid', 'label', 'fluid', 'category', 
            'ref_range_lower', 'ref_range_upper', 'valueuom', 'metric_definition'
        ]]
        
        # Convert records to a list of tuples for batch execution
        records_to_insert = [tuple(x) for x in df_ordered.to_numpy()]
        
        print(f"4. Ingesting {len(records_to_insert)} clinical metric records into PostgreSQL...")
        insert_query = """
            INSERT INTO medical_metrics (
                itemid, metric_label, fluid, category, 
                ref_range_lower, ref_range_upper, valueuom, metric_definition
            ) VALUES %s
        """
        execute_values(cursor, insert_query, records_to_insert)
        conn.commit()
        print("Clinical metrics table initialized and populated successfully.")
        
        # Spot check verification query
        cursor.execute(
            "SELECT metric_label, ref_range_lower, ref_range_upper, valueuom, metric_definition "
            "FROM medical_metrics WHERE metric_label = 'Glucose';"
        )
        row = cursor.fetchone()
        if row:
            print("\nDatabase verification check (Glucose):")
            print(f"  Metric Label: {row[0]}")
            print(f"  Reference Range: {row[1]} ~ {row[2]} {row[3]}")
            print(f"  Definition: {row[4]}")

        # ====================================================================
        # 2. Enable pgvector and create fact-checking vector schema with HNSW index
        # ====================================================================
        print("\n5. Enabling 'vector' extension and setting up 'factcheck_vectors' schema...")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS factcheck_vectors (
                id SERIAL PRIMARY KEY,
                claim TEXT NOT NULL,
                explanation TEXT NOT NULL,
                label VARCHAR(50),
                claim_url TEXT,
                main_text TEXT,
                sources TEXT,
                embedding vector(384)
            );
        """)

        # Create HNSW index for sub-10ms cosine similarity retrieval
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS factcheck_vector_hnsw_idx 
            ON factcheck_vectors USING hnsw (embedding vector_cosine_ops);
        """)
        
        conn.commit()
        print("Database schema migration complete (MIMIC metrics + pgvector fact-check tables).")

    except Exception as e:
        print(f"Database initialization error: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    init_postgres_db()