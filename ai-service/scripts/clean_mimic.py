import os
import pandas as pd


def build_rag_base():
    """
    Decompress, merge, and clean raw MIMIC-IV datasets to extract the top 20
    clinical laboratory metrics and reference ranges as the foundational RAG knowledge base.
    """
    print("1. Reading and decompressing raw MIMIC-IV gzip files from 'data/' directory...")
    
    # Path guardrails: ensure required MIMIC-IV source files exist
    required_files = [
        'data/d_labitems.csv.gz',
        'data/labevents.csv.gz',
        'data/d_icd_diagnoses.csv.gz'
    ]
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"Error: Required dataset file not found: {file_path}. Please check directory structure.")
            return

    d_labitems = pd.read_csv('data/d_labitems.csv.gz', compression='gzip')       # Lab item dictionary / lookup table
    labevents = pd.read_csv('data/labevents.csv.gz', compression='gzip')         # Patient lab events and reference ranges
    d_icd = pd.read_csv('data/d_icd_diagnoses.csv.gz', compression='gzip')       # ICD diagnosis dictionary
    
    print("2. Joining laboratory measurements with dictionary definitions (Inner Join on 'itemid')...")
    lab_merged = pd.merge(labevents, d_labitems, on='itemid', how='inner')
    
    print("3. Filtering core schema fields and pruning records with missing reference bounds...")
    # Select essential fields and drop records missing reference range boundaries
    lab_filtered = lab_merged[[
        'itemid', 'label', 'fluid', 'category', 
        'ref_range_lower', 'ref_range_upper', 'valueuom'
    ]].dropna(subset=['ref_range_lower', 'ref_range_upper'])
    
    print("4. Calculating event frequencies to select the top 20 clinical metrics...")
    # Identify top 20 most frequent lab items
    top_items_counts = lab_filtered['itemid'].value_counts().head(20).index
    
    # Filter for top metrics and deduplicate by itemid to form canonical dictionary entries
    final_metrics = lab_filtered[lab_filtered['itemid'].isin(top_items_counts)].drop_duplicates(subset=['itemid'])
    
    print(f"\nSuccessfully extracted and cleaned {len(final_metrics)} core clinical lab metrics.")
    print("=" * 70)
    print(final_metrics[['itemid', 'label', 'ref_range_lower', 'ref_range_upper', 'valueuom']].to_string(index=False))
    print("=" * 70)
    
    # Export cleaned metrics base for PostgreSQL ingestion
    os.makedirs('data', exist_ok=True)
    final_metrics.to_csv('data/cleaned_metrics_base.csv', index=False)
    print("Clinical metrics reference table exported to 'data/cleaned_metrics_base.csv'.")
    
    print("\n5. Extracting initial ICD diagnosis reference records...")
    top_diseases = d_icd.head(20)
    
    top_diseases.to_csv('data/cleaned_diseases_base.csv', index=False)
    print("ICD diagnosis reference table exported to 'data/cleaned_diseases_base.csv'.")
    print("Dataset ETL and preprocessing completed successfully.")


if __name__ == "__main__":
    build_rag_base()