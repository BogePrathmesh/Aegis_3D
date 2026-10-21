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
    annotated_image_b64: str   # base64 JPEG — combined YOLO + U-Net overlay
    edge_image_b64: str        # base64 binary edge map
    depth_map_data: Optional[List[List[float]]] = None  # WebGL array
    latitude: float = 18.5204
    longitude: float = 73.8567
    gps_status: str = "fallback"
    # ── U-Net / hybrid fields (optional, None when U-Net unavailable) ──────────
    unet_mask_b64: Optional[str] = None       # base64 JPEG — U-Net segmentation overlay only
    yolo_boxes_b64: Optional[str] = None      # base64 JPEG — YOLO bounding boxes only (no U-Net)
    unet_crack_area_pct: Optional[float] = None  # crack area % from U-Net mask
    model_agreement: Optional[str] = None        # 'agree' | 'partial' | 'disagree'
    agreement_iou: Optional[float] = None        # IoU between U-Net mask and YOLO box pixels
    agreement_note: Optional[str] = None         # human-readable explanation
    # ── Material and Calibration fields ───────────────────────────────────────
    material_type: Optional[str] = "concrete"           # display material (AI or user)
    material_ai: Optional[str] = "unknown"              # AI predicted class
    material_ai_label: Optional[str] = "Unknown / Uncertain"  # human-readable
    material_ai_confidence: Optional[float] = 0.0       # cosine similarity [0..1]
    material_source: Optional[str] = "User-selected material"  # display source
    calibration_status: Optional[str] = "Uncalibrated — pixels only"
    crack_width_unit: Optional[str] = "px"
    max_crack_width_mm: Optional[float] = None
    base_damage_penalty: Optional[float] = 0.0

class RecalculateRequest(BaseModel):
    total_crack_area_pct: float = 0.0
    max_crack_width: float = 0.0
    crack_count: int = 0
    cracks: List[CrackDetail] = []
    structure_type: str = "building"
    material_type: str = "auto"
    material_ai: Optional[str] = "unknown"
    age_years: int = 10
    is_seismic: bool = False
    is_near_sea: bool = False
    has_heavy_traffic: bool = False
    sim_load_pct: Optional[float] = 0.0
    calibration_status: Optional[str] = "Uncalibrated — pixels only"
    px_to_mm: Optional[float] = None

class RecalculateResponse(BaseModel):
    health_score: float
    severity_index: float
    risk_level: str
    recommendations: List[str]
    material_type: str
    material_source: str

@router.get("/health")
def health():
    return {"status": "ok"}

@router.post("/recalculate", response_model=RecalculateResponse)
def recalculate_metrics(req: RecalculateRequest):
    analyzer = get_analyzer()

    user_override = bool(req.material_type and req.material_type.lower() not in ("auto", "none", "", "unknown_auto"))
    if user_override:
        display_mat = req.material_type
        mat_src = "User override"
        scoring_mat = req.material_type
    else:
        display_mat = req.material_ai or "unknown"
        mat_src = "AI prediction"
        scoring_mat = "unknown"

    mod = importlib.import_module("app.services.5_inference")
    CrackDetection = mod.CrackDetection

    mock_detections = []
    for c in req.cracks:
        mock_detections.append(CrackDetection(
            bbox=[0.0, 0.0, 10.0, 10.0],
            confidence=c.confidence,
            crack_type=c.type.lower(),
            area_pixels=int(getattr(c, 'area_pct', 0.0) * 100),
            area_percentage=getattr(c, 'area_pct', 0.0),
            width_pixels=float(getattr(c, 'width_px', 0.0)),
            length_pixels=float(getattr(c, 'length_px', 10.0)),
        ))

    base_health = analyzer.calculate_health_score(
        coverage_pct=req.total_crack_area_pct,
        max_fracture_px=req.max_crack_width,
        anomaly_count=req.crack_count,
        structure_type=req.structure_type,
        material_type=scoring_mat,
        detections=mock_detections,
        img_diagonal_px=1000.0,
    )

    ssi = analyzer.calculate_severity_index(
        health_score=base_health,
        coverage_pct=req.total_crack_area_pct,
        max_fracture_px=req.max_crack_width,
        anomaly_count=req.crack_count,
        age_years=req.age_years,
        is_seismic=req.is_seismic,
        is_near_sea=req.is_near_sea,
        is_heavy_traffic=req.has_heavy_traffic,
        structure_type=req.structure_type,
        material_type=scoring_mat,
    )

    # If simulation load is active (0 to 100), add simulated load stress
    if req.sim_load_pct and req.sim_load_pct > 0:
        sim_stress = (min(100.0, req.sim_load_pct) / 100.0) * 22.0
        ssi = round(min(100.0, ssi + sim_stress), 1)

    # Harmonize Structural Integrity (SI)
    si = round(max(0.0, min(100.0, 100.0 - ssi)), 1)
    risk_level, _, _ = analyzer.get_risk_level(ssi, coverage_pct=req.total_crack_area_pct)

    recs = analyzer.get_recommendations(
        detections=mock_detections,
        health_score=si,
        severity_index=ssi,
        structure_type=req.structure_type,
        age_years=req.age_years,
        is_seismic=req.is_seismic,
        is_near_sea=req.is_near_sea,
        is_heavy_traffic=req.has_heavy_traffic,
        coverage_pct=req.total_crack_area_pct,
        max_fracture_px=req.max_crack_width,
        calibration_status=req.calibration_status,
        px_to_mm=req.px_to_mm,
    )

    if req.sim_load_pct and req.sim_load_pct > 50:
        recs.insert(1, f"⚡ DYNAMIC LOAD ALERT: Simulated stress at {req.sim_load_pct:.0f}% load approaching yield limit.")

    return RecalculateResponse(
        health_score=si,
        severity_index=ssi,
        risk_level=risk_level,
        recommendations=recs,
        material_type=display_mat,
        material_source=mat_src,
    )

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_image(
    file: UploadFile = File(...),
    structure_type: str = Form("building"),
    age_years: int = Form(10),
    is_seismic: bool = Form(False),
    is_near_sea: bool = Form(False),
    has_heavy_traffic: bool = Form(False),
    material_type: str = Form("auto"),
    px_to_mm: Optional[float] = Form(None)
):
    contents = await file.read()
    tmp_path = f"tmp_upload_{file.filename}"
    
    with open(tmp_path, "wb") as f:
        f.write(contents)
        
    img = cv2.imread(tmp_path)
    if img is None:
        if os.path.exists(tmp_path): os.remove(tmp_path)
        raise HTTPException(status_code=400, detail="Invalid image file")

    try:
        analyzer = get_analyzer()
        result = analyzer.analyze(
            tmp_path, 
            structure_type=structure_type,
            age_years=age_years,
            is_seismic=is_seismic,
            is_near_sea=is_near_sea,
            is_heavy_traffic=has_heavy_traffic,
            material_type=material_type,
            px_to_mm=px_to_mm
        )
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    _, buf = cv2.imencode(".jpg", result.annotated_image, [cv2.IMWRITE_JPEG_QUALITY, 90])
    b64 = base64.b64encode(buf).decode("utf-8")

    _, edge_buf = cv2.imencode(".jpg", result.edge_detected_image, [cv2.IMWRITE_JPEG_QUALITY, 80])
    edge_b64 = base64.b64encode(edge_buf).decode("utf-8")

    # Encode U-Net overlay and YOLO-only images (None when U-Net is unavailable)
    unet_mask_b64  = None
    yolo_boxes_b64 = None
    if result.unet_overlay_image is not None:
        _, u_buf = cv2.imencode(".jpg", result.unet_overlay_image, [cv2.IMWRITE_JPEG_QUALITY, 90])
        unet_mask_b64 = base64.b64encode(u_buf).decode("utf-8")
    if result.yolo_only_image is not None:
        _, y_buf = cv2.imencode(".jpg", result.yolo_only_image, [cv2.IMWRITE_JPEG_QUALITY, 90])
        yolo_boxes_b64 = base64.b64encode(y_buf).decode("utf-8")

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

    anomaly_cnt = int(result.crack_density) if result.crack_density is not None and result.crack_density > 0 else len(result.detections)

    return AnalysisResponse(
        filename=file.filename,
        structure_type=result.structure_type,
        health_score=result.health_score,
        severity_index=result.severity_index,
        risk_level=result.risk_level,
        crack_count=anomaly_cnt,
        total_crack_area_pct=round(result.total_crack_area_pct, 3),
        max_crack_width=round(result.max_crack_width, 1),
        cracks=cracks,
        recommendations=result.recommendations,
        annotated_image_b64=b64,
        edge_image_b64=edge_b64,
        depth_map_data=result.depth_map_data,
        latitude=result.latitude,
        longitude=result.longitude,
        gps_status=result.gps_status,
        unet_mask_b64=unet_mask_b64,
        yolo_boxes_b64=yolo_boxes_b64,
        unet_crack_area_pct=result.unet_crack_area_pct,
        model_agreement=result.model_agreement,
        agreement_iou=result.agreement_iou,
        agreement_note=result.agreement_note,
        material_type=result.material_type if hasattr(result, "material_type") else material_type,
        material_ai=result.material_ai if hasattr(result, "material_ai") else "unknown",
        material_ai_label=result.material_ai_label if hasattr(result, "material_ai_label") else "Unknown / Uncertain",
        material_ai_confidence=result.material_ai_confidence if hasattr(result, "material_ai_confidence") else 0.0,
        material_source=result.material_source if hasattr(result, "material_source") else "User-selected material",
        calibration_status=result.calibration_status if hasattr(result, "calibration_status") else "Uncalibrated — pixels only",
        crack_width_unit="px",
        max_crack_width_mm=result.max_crack_width_mm if hasattr(result, "max_crack_width_mm") else None,
        base_damage_penalty=getattr(result, "base_damage_penalty", 0.0),
    )

@router.post("/analyze/batch")
async def analyze_batch(
    files: list[UploadFile] = File(...),
    structure_type: str = Form(default="building"),
):
    results = []
    for file in files:
        contents = await file.read()
        tmp_path = f"tmp_batch_{file.filename}"
        with open(tmp_path, "wb") as f:
            f.write(contents)
            
        img = cv2.imread(tmp_path)
        if img is None:
            if os.path.exists(tmp_path): os.remove(tmp_path)
            continue
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
