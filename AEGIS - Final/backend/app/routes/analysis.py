import os
import base64
import importlib
import csv
from datetime import datetime
from pathlib import Path
from typing import Optional, List

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from pydantic import BaseModel

router = APIRouter()

# ─── Model loader ──────────────────────────────────
_analyzer = None

def get_analyzer():
    global _analyzer
    if _analyzer is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        weights = os.path.join(base_dir, "models", "crack_detection", "weights", "best.pt")
        seg_weights = os.path.join(base_dir, "models", "crack_segmentation", "weights", "best.pt")
        
        if not os.path.exists(weights):
            raise HTTPException(
                status_code=503,
                detail=f"Model weights not found at {weights}."
            )
        
        # Load from the moved scripts (now in app.services)
        mod = importlib.import_module("app.services.5_inference")
        _analyzer = mod.CrackAnalyzer(
            detection_weights=weights,
            segmentation_weights=seg_weights,
        )
    return _analyzer


# ─── Response Models ───────────────────────────────
class CrackDetail(BaseModel):
    id: int
    type: str
    confidence: float
    area_pct: float
    width_px: float
    length_px: float

class AnalysisResponse(BaseModel):
    filename: str
    structure_type: str
    health_score: float
    severity_index: float
    risk_level: str
    crack_count: int
    total_crack_area_pct: float
    max_crack_width: float
    cracks: list[CrackDetail]
    recommendations: list[str]
    annotated_image_b64: str   # base64 JPEG for frontend display
    edge_image_b64: str        # base64 binary edge map
    depth_map_data: Optional[List[List[float]]] = None # WebGL array
    latitude: float = 18.5204
    longitude: float = 73.8567
    gps_status: str = "fallback"

@router.get("/health")
def health():
    return {"status": "ok"}

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_image(
    file: UploadFile = File(...),
    structure_type: str = Form("building"),
    age_years: int = Form(10),
    is_seismic: bool = Form(False),
    is_near_sea: bool = Form(False),
    has_heavy_traffic: bool = Form(False)
):
    contents = await file.read()
    np_arr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image file")

    tmp_path = f"tmp_upload_{file.filename}"
    cv2.imwrite(tmp_path, img)

    try:
        analyzer = get_analyzer()
        result = analyzer.analyze(
            tmp_path, 
            structure_type=structure_type,
            age_years=age_years,
            is_seismic=is_seismic,
            is_near_sea=is_near_sea,
            is_heavy_traffic=has_heavy_traffic
        )
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    _, buf = cv2.imencode(".jpg", result.annotated_image, [cv2.IMWRITE_JPEG_QUALITY, 90])
    b64 = base64.b64encode(buf).decode("utf-8")

    _, edge_buf = cv2.imencode(".jpg", result.edge_detected_image, [cv2.IMWRITE_JPEG_QUALITY, 80])
    edge_b64 = base64.b64encode(edge_buf).decode("utf-8")

    cracks = [
        CrackDetail(
            id=i + 1,
            type=d.crack_type,
            confidence=round(d.confidence, 3),
            area_pct=round(d.area_percentage, 3),
            width_px=round(d.width_pixels, 1),
            length_px=round(d.length_pixels, 1),
        )
        for i, d in enumerate(result.detections)
    ]

    return AnalysisResponse(
        filename=file.filename,
        structure_type=result.structure_type,
        health_score=result.health_score,
        severity_index=result.severity_index,
        risk_level=result.risk_level,
        crack_count=len(result.detections),
        total_crack_area_pct=round(result.total_crack_area_pct, 3),
        max_crack_width=round(result.max_crack_width, 1),
        cracks=cracks,
        recommendations=result.recommendations,
        annotated_image_b64=b64,
        edge_image_b64=edge_b64,
        depth_map_data=result.depth_map_data,
        latitude=result.latitude,
        longitude=result.longitude,
        gps_status=result.gps_status
    )

@router.post("/analyze/batch")
async def analyze_batch(
    files: list[UploadFile] = File(...),
    structure_type: str = Form(default="building"),
):
    results = []
    for file in files:
        contents = await file.read()
        np_arr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            continue
        tmp_path = f"tmp_batch_{file.filename}"
        cv2.imwrite(tmp_path, img)
        try:
            analyzer = get_analyzer()
            result = analyzer.analyze(tmp_path, structure_type)
            results.append({
                "filename": file.filename,
                "health_score": result.health_score,
                "risk_level": result.risk_level,
                "crack_count": len(result.detections),
                "total_crack_area_pct": round(result.total_crack_area_pct, 3),
            })
        except Exception as e:
            results.append({"filename": file.filename, "error": str(e)})
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    return {"results": results, "total": len(results)}
