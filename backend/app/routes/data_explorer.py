import os, csv
from fastapi import APIRouter
from typing import List, Dict
# from app.services.aegis_model import AegisModel # Model analysis now managed by CSV pre-processing or upload workflow

router = APIRouter(tags=["Data Explorer"])

# HARDCODED ABSOLUTE PATH FOR HACKATHON ENVIRONMENT
# Based on Get-ChildItem results: C:\Programz\Hackaton\Ignisia\data\P\CP\001-146.jpg
IMAGES_DIR = r"C:\Programz\Hackaton\Ignisia\data\P\CP"

@router.get("/list-images")
async def list_images():
    BASE_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data"))
    CSV_PATH = os.path.join(BASE_DATA_DIR, "dummy_inspection_data.csv")
    
    if not os.path.exists(CSV_PATH):
         return {"error": "Dataset CSV not found", "path": CSV_PATH}
    
    try:
        results = []
        with open(CSV_PATH, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    insp_id = row['inspection_id']
                    # Map CSV data to the exact format expected by DataExplorer.tsx
                    risk_val = float(row.get('severity_index', 0))
                    
                    results.append({
                        "image_name": f"{insp_id}.jpg",
                        "structure_name": f"{row['structure_type']} {insp_id}",
                        "risk_score": int(risk_val),
                        "risk_level": row.get('risk_level', "Low"),
                        "failure_probability": round(1.0 - (float(row.get('health_score', 100)) / 100.0), 2),
                        "insurance_score": int(risk_val * 1.15)
                    })
                except Exception as row_error:
                    print(f"Skipping row during data_explorer mapping: {row_error}")
            
        return results
    except Exception as e:
        return {"error": str(e)}
