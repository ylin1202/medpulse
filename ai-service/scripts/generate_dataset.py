import json
import os
import random
from typing import List
import pandas as pd


# 1. Canonical Mapping for 20 Core Medical Metrics (Synonyms & Abbreviations)
METRIC_SYNONYMS = {
    "RDW": ["RDW", "red cell distribution width", "RDW-CV", "erythrocyte distribution width"],
    "Red Blood Cells": ["Red Blood Cells", "RBC", "RBC count", "erythrocytes", "erythrocyte count"],
    "White Blood Cells": ["White Blood Cells", "WBC", "leukocytes", "WBC count", "white count"],
    "MCHC": ["MCHC", "mean corpuscular hemoglobin concentration"],
    "Hematocrit": ["Hematocrit", "HCT", "crit", "packed cell volume", "PCV"],
    "Hemoglobin": ["Hemoglobin", "Hgb", "Hb", "haemoglobin"],
    "Platelet Count": ["Platelet Count", "platelets", "PLT", "thrombocyte count"],
    "MCV": ["MCV", "mean corpuscular volume"],
    "MCH": ["MCH", "mean corpuscular hemoglobin"],
    "Chloride": ["Chloride", "Cl-", "serum chloride", "Cl"],
    "Bicarbonate": ["Bicarbonate", "HCO3-", "serum bicarbonate", "total CO2", "bicarb"],
    "Magnesium": ["Magnesium", "Mg", "serum magnesium", "Mg2+"],
    "Urea Nitrogen": ["Urea Nitrogen", "BUN", "blood urea nitrogen", "serum urea"],
    "Calcium, Total": ["Calcium, Total", "serum calcium", "total calcium", "Ca2+", "calcium level"],
    "Sodium": ["Sodium", "Na+", "serum sodium", "Na"],
    "Potassium": ["Potassium", "K+", "serum potassium", "potassium level", "K"],
    "Anion Gap": ["Anion Gap", "serum anion gap", "AG"],
    "Creatinine": ["Creatinine", "Cr", "serum creatinine", "SCr", "creat"],
    "Glucose": ["Glucose", "blood glucose", "blood sugar", "fasting blood sugar", "GLU", "fasting glucose"],
    "Phosphate": ["Phosphate", "PO4", "serum phosphate", "phosphorus", "serum phosphorus"]
}


# 2. Diverse Clinical Context Templates (12 Scenarios)
CLINICAL_TEMPLATES = [
    # 1. Emergency Department (ED)
    "Patient presented to the ER with acute onset of diaphoresis and tachycardia. Urgent lab workup requested for {mentions}.",
    "Emergency triage note: 58-year-old male with chest tightness and altered mental status. Stat panel ordered for {mentions}.",
    
    # 2. Inpatient Rounds & Acuity Shifts
    "During morning rounds, the attending physician observed clinical deterioration. Recommended immediate re-evaluation of {mentions}.",
    "Inpatient progress note: Patient is currently recovering from sepsis. Continue tracking serial values for {mentions}.",
    
    # 3. Outpatient & Routine Surveillance
    "Routine outpatient check-up for a patient with poorly managed metabolic syndrome. Ordered routine screening for {mentions}.",
    "Discharge summary draft: Patient is clinically stable. Scheduled follow-up visit in 3 weeks to repeat lab testing for {mentions}.",
    
    # 4. Pre/Post-Operative Evaluation
    "Pre-operative clearance note: Ensure baseline metabolic status is established. Documented {mentions} in surgical safety chart.",
    "Post-op Day 2 status: Fluid balance is negative. Order morning blood draws including {mentions} to prevent electrolyte shifts.",
    
    # 5. Intensive Critical Care (ICU)
    "ICU telemetry transfer note: Multi-organ failure protocol initiated. Monitor hourly hemodynamics and draw {mentions} every 8 hours.",
    
    # 6. Clinical Communication & Telehealth Consultations
    "Telehealth consultation summary: Reviewed external laboratory results with patient, focusing specifically on abnormal trends in {mentions}.",
    "Consultation note: Discussed lab findings with family. Clarified clinical implications regarding fluctuating {mentions}."
]


# 3. Negative Sample Repository (General Symptoms / Non-Lab Requests)
NEGATIVE_SAMPLES = [
    "Patient presented with mild tension headache after prolonged screen time. Advised rest, hydration, and OTC acetaminophen as needed.",
    "Follow-up visit for seasonal allergic rhinitis. Prescribed fluticasone nasal spray and recommended allergen avoidance.",
    "Physical therapy progress note: Patient completed 60 minutes of lumbar stabilization exercises without acute pain.",
    "Orthopedic consultation: 24-year-old with right ankle inversion sprain during basketball. X-ray negative for acute fracture; RICE protocol initiated.",
    "Psychiatry note: Patient reports stable mood and improved sleep architecture on current sertraline dosage. No medication adjustments indicated.",
    "Dermatology clinic: Routine skin examination revealed a benign seborrheic keratosis on the right shoulder. No biopsy required.",
    "Administrative note: Patient attended clinic strictly to renew medical driving certificate. Visual acuity and reflex testing within normal limits.",
    "Patient calls regarding mild dry cough persisting for 3 days without fever, shortness of breath, or chest pain. Symptomatic care advised."
]


def format_natural_mentions(alias_list: List[str]) -> str:
    """Format natural English listing with Oxford comma support."""
    if len(alias_list) == 1:
        return alias_list[0]
    elif len(alias_list) == 2:
        return f"{alias_list[0]} and {alias_list[1]}"
    else:
        return f"{', '.join(alias_list[:-1])}, and {alias_list[-1]}"


def generate_fine_tune_data(total_samples: int = 1200, negative_ratio: float = 0.15):
    """Generate fine-tuning instruction-tuning dataset for clinical entity extraction."""
    print(f"1. Initializing clinical NER data synthesis pipeline (Target: {total_samples} samples)...")
    
    canonical_metrics = list(METRIC_SYNONYMS.keys())
    dataset = []
    
    num_negatives = int(total_samples * negative_ratio)
    num_positives = total_samples - num_negatives

    print(f"2. Synthesizing positive samples ({num_positives} records with synonym jitter and permutation)...")
    for _ in range(num_positives):
        # Sample between 1 and 4 metrics per clinical note
        num_metrics = random.choices([1, 2, 3, 4], weights=[0.2, 0.45, 0.25, 0.10])[0]
        chosen_canonical = random.sample(canonical_metrics, num_metrics)
        
        # Sample realistic aliases/abbreviations for selected metrics
        chosen_aliases = [random.choice(METRIC_SYNONYMS[m]) for m in chosen_canonical]
        mentions_text = format_natural_mentions(chosen_aliases)
        
        # Select contextual template
        template = random.choice(CLINICAL_TEMPLATES)
        input_text = template.format(mentions=mentions_text)
        
        # Shuffle target query output to prevent position bias
        target_queries = list(chosen_canonical)
        random.shuffle(target_queries)
        
        thought_process = (
            f"The clinical input mentions {', '.join(chosen_aliases)}. "
            f"Mapped to standardized canonical medical keys: {', '.join(target_queries)}. "
            f"To adhere to safety protocols, I must extract these exact keys without providing diagnostic opinions."
        )
        
        output_json = {
            "thought": thought_process,
            "query": target_queries
        }
        
        dataset.append({
            "instruction": "Extract valid medical metrics from the clinical text. Output JSON only.",
            "input": input_text,
            "output": json.dumps(output_json, ensure_ascii=False, indent=2)
        })

    print(f"3. Synthesizing negative samples ({num_negatives} records for empty-query guardrails)...")
    for _ in range(num_negatives):
        base_text = random.choice(NEGATIVE_SAMPLES)
        
        thought_process = (
            "The clinical text describes general symptoms or non-laboratory findings. "
            "No specific medical lab tests or metrics are requested. Returning empty query array."
        )
        
        output_json = {
            "thought": thought_process,
            "query": []
        }
        
        dataset.append({
            "instruction": "Extract valid medical metrics from the clinical text. Output JSON only.",
            "input": base_text,
            "output": json.dumps(output_json, ensure_ascii=False, indent=2)
        })

    # Shuffle full dataset
    random.shuffle(dataset)

    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "train.json")

    print(f"4. Writing {len(dataset)} instruction records to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print("Fine-tuning instruction dataset synthesis completed successfully.")


if __name__ == "__main__":
    generate_fine_tune_data(total_samples=1200, negative_ratio=0.15)