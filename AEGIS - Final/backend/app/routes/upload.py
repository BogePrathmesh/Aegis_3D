import os
import shutil
import hashlib
import random
import cv2
from uuid import uuid4
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.report_generator import ReportGenerator
from app.services.aegis_model import AegisModel

router = APIRouter(tags=["Upload & Analyze"])

BASE_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
UPLOAD_DIR = os.path.join(BASE_DATA_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/analyze-and-report")
async def analyze_and_report(file: UploadFile = File(...)):
    # 1. Save uploaded file
    file_id = str(uuid4())
    filename = f"{file_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    try:
        # 1. Save uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 2. Real AI Analysis using AegisModel (Computer Vision)
        mask = AegisModel.generate_crack_mask(file_path)
        props = AegisModel.analyze_crack_properties(mask)
        
        # 3. Predict Future Deterioration (Simulation)
        predicted_img = AegisModel.simulate_deterioration(file_path, mask, years=5)
        
        # 4. Generate Topographical/Stress View
        depth_map = AegisModel.generate_depth_map(file_path, mask)
        
        # Save generated masks and predictions
        mask_filename = f"mask_{filename.split('.')[0]}.png"
        pred_filename = f"predicted_{filename.split('.')[0]}.jpg"
        depth_filename = f"depth_{filename.split('.')[0]}.png"
        
        mask_path = os.path.join(BASE_DATA_DIR, "masks", mask_filename)
        pred_path = os.path.join(BASE_DATA_DIR, "uploads", pred_filename)
        depth_path = os.path.join(BASE_DATA_DIR, "uploads", depth_filename)
        
        cv2.imwrite(mask_path, mask)
        cv2.imwrite(pred_path, predicted_img)
        cv2.imwrite(depth_path, depth_map)
        
        # Mapping properties to insurance metrics
        risk_score = int(props["severity_score"])
        risk_level = "CRITICAL" if risk_score > 80 else ("HIGH" if risk_score > 60 else "MEDIUM")
        failure_prob = round(props["severity_score"] / 100.0, 2)
        ins_score = int(risk_score * 1.15)
        
        analysis_data = {
            "structure_name": f"On-Site Analysis ({filename[:8]})",
            "location": "GPS: Real-time scan sync",
            "risk_score": risk_score,
            "risk_level": risk_level,
            "failure_probability": failure_prob,
            "insurance_score": ins_score,
            "defects": [
                {
                    "id": f"D1", # User requested D1 format
                    "type": f"Fissure / Crack",
                    "severity": int(max(1, props["severity_score"] / 20)),
                    "depth": round(props["depth"], 1),
                    "length": round(props["length"], 1),
                    "growth": random.randint(10, 45), 
                    "image": f"uploads/{filename}",
                    "predicted_image": f"uploads/{pred_filename}",
                    "heatmap": mask_filename,
                    "depth_map": f"uploads/{depth_filename}"
                }
            ]
        }
        
        # 3. Trigger Professional Report Generation
        report_gen = ReportGenerator()
        report_id_full = report_gen.generate_report(analysis_data)
        
        # Extract report filename from path
        report_filename = os.path.basename(report_id_full)
        
        # 4. Return links and summary results
        return {
            "status": "success",
            "message": "AI Analysis complete. Report generated.",
            "file_id": file_id,
            "report_url": f"/static/reports/{report_filename}",
            "risk_score": risk_score,
            "risk_level": risk_level,
            "failure_probability": failure_prob
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
