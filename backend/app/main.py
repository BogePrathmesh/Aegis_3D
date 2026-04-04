from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routes import risk, report, structures, data_explorer, upload
from app.routes import analysis, simulation, budget
import os
import cv2
import base64
from uuid import uuid4

app = FastAPI(
    title="AEGIS Unified Intelligence Platform API",
    description="Unified backend merging Aegis2 inference, Aegia_3D simulation/budgeting, and Ignisia reporting.",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base directories
# Look for data folder in project root (3 levels up from routes)
current_file = os.path.abspath(__file__)
BASE_DIR = os.path.dirname(os.path.dirname(current_file)) # BACKEND ROOT
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
MASKS_DIR = os.path.join(DATA_DIR, "masks")
DEPTH_DIR = os.path.join(DATA_DIR, "depth")
FRAMES_DIR = os.path.join(DATA_DIR, "simulation_frames")
DUMMY_DIR = os.path.join(DATA_DIR, "Dummydataset")

for d in [REPORTS_DIR, UPLOADS_DIR, IMAGES_DIR, MASKS_DIR, DEPTH_DIR, FRAMES_DIR, DUMMY_DIR]:
    os.makedirs(d, exist_ok=True)

print(f"MAIN: BASE_DIR={BASE_DIR}")
print(f"MAIN: DUMMY_DIR={DUMMY_DIR} exists={os.path.exists(DUMMY_DIR)}")

# Mount statics
app.mount("/static/images", StaticFiles(directory=IMAGES_DIR), name="images")
app.mount("/static/masks",  StaticFiles(directory=MASKS_DIR),  name="masks")
app.mount("/static/depth",  StaticFiles(directory=DEPTH_DIR),  name="depth")
app.mount("/static/frames", StaticFiles(directory=FRAMES_DIR), name="frames")
app.mount("/static/cp", StaticFiles(directory=DUMMY_DIR), name="cp")
app.mount("/static/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/static/reports", StaticFiles(directory=REPORTS_DIR), name="reports")

# Include Routers
app.include_router(analysis.router, prefix="/api/analysis", tags=["Crack Analysis (Aegis2)"])
app.include_router(simulation.router, prefix="/api/simulation", tags=["FEA Simulation (Aegia_3D)"])
app.include_router(budget.router, prefix="/api/budget", tags=["Budgeting (Aegia_3D)"])
app.include_router(structures.router, prefix="/api/structures", tags=["Structures (Ignisia)"])
app.include_router(risk.router, prefix="/api/risk", tags=["Risk Scoring (Ignisia)"])
app.include_router(report.router, prefix="/api/report", tags=["PDF Engine (Ignisia)"])
app.include_router(data_explorer.router, prefix="/api/data", tags=["Explorer (Ignisia)"])
app.include_router(upload.router, prefix="/api/upload", tags=["Upload (Ignisia)"])

# Backward compatibility proxy routes
from app.routes.analysis import analyze_image, analyze_batch
from scripts.stitcher import stitch_images, extract_zip_images
import zipfile
import shutil

@app.post("/analyze/stitch")
async def analyze_stitched(
    files: list[UploadFile] = File(...),
    structure_type: str = Form("bridge")
):
    """
    Drone Special: Accepts a batch of overlapping photos, 
    stitches them into one wide master scan, then runs inference.
    """
    tmp_folder = os.path.join(UPLOADS_DIR, f"tmp_stitch_{uuid4().hex[:8]}")
    os.makedirs(tmp_folder, exist_ok=True)
    paths = []
    
    try:
        # Save all images to disk
        for f in files:
            p = os.path.join(tmp_folder, f.filename)
            with open(p, "wb") as buffer:
                shutil.copyfileobj(f.file, buffer)
            paths.append(p)
            
        # 1. STITCH
        stitched_img, status = stitch_images(paths)
        if stitched_img is None:
            return {"error": f"Stitching Failed: {status}. Please ensure at least 40% image overlap."}
            
        master_path = os.path.join(tmp_folder, "master_orthomosaic.jpg")
        cv2.imwrite(master_path, stitched_img)
        
        # 2. INFER USING AI ENGINE
        from app.routes.analysis import get_analyzer
        analyzer = get_analyzer()
        result = analyzer.analyze(master_path, structure_type=structure_type)
        
        # Binary conversions for frontend
        _, buf = cv2.imencode(".jpg", result.annotated_image, [cv2.IMWRITE_JPEG_QUALITY, 90])
        b64 = base64.b64encode(buf).decode("utf-8")
        
        _, edge_buf = cv2.imencode(".jpg", result.edge_detected_image, [cv2.IMWRITE_JPEG_QUALITY, 80])
        edge_b64 = base64.b64encode(edge_buf).decode("utf-8")
        
        return {
            "status": "success",
            "message": "Orthomosaic stitched and analyzed successfully.",
            "health_score": result.health_score,
            "risk_level": result.risk_level,
            "latitude": result.latitude,
            "longitude": result.longitude,
            "gps_status": result.gps_status,
            "orthomosaic_b64": b64,
            "edge_map_b64": edge_b64,
            "recommendations": result.recommendations
        }
    finally:
        shutil.rmtree(tmp_folder, ignore_errors=True)

app.post("/analyze")(analyze_image)
app.post("/analyze/batch")(analyze_batch)

@app.post("/analyze/stitch-zip")
async def analyze_stitched_zip(
    file: UploadFile = File(...),
    structure_type: str = Form("bridge")
):
    """
    Drone Special: Accepts a ZIP file of overlapping drone photos,
    extracts them, stitches into one master scan, then runs inference.
    """
    if not file.filename.lower().endswith(".zip"):
        return {"error": "Please upload a .zip file containing drone imagery."}

    tmp_folder = os.path.join(UPLOADS_DIR, f"tmp_zip_{uuid4().hex[:8]}")
    os.makedirs(tmp_folder, exist_ok=True)
    zip_path = os.path.join(tmp_folder, "upload.zip")

    try:
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        paths = extract_zip_images(zip_path, tmp_folder)
        if len(paths) < 2:
            return {"error": f"ZIP must contain at least 2 images. Found: {len(paths)}"}

        # 1. STITCH
        stitched_img, status_msg = stitch_images(paths)
        if stitched_img is None:
            return {"error": f"Stitching Failed: {status_msg}. Ensure ≥40% image overlap."}

        master_path = os.path.join(tmp_folder, "master_orthomosaic.jpg")
        cv2.imwrite(master_path, stitched_img)

        # 2. INFER
        from app.routes.analysis import get_analyzer
        analyzer = get_analyzer()
        result = analyzer.analyze(master_path, structure_type=structure_type)

        _, buf = cv2.imencode(".jpg", result.annotated_image, [cv2.IMWRITE_JPEG_QUALITY, 90])
        b64 = base64.b64encode(buf).decode("utf-8")
        _, edge_buf = cv2.imencode(".jpg", result.edge_detected_image, [cv2.IMWRITE_JPEG_QUALITY, 80])
        edge_b64 = base64.b64encode(edge_buf).decode("utf-8")

        return {
            "status": "success",
            "message": f"ZIP orthomosaic stitched ({len(paths)} images) and analyzed.",
            "stitch_strategy": status_msg,
            "image_count": len(paths),
            "health_score": result.health_score,
            "severity_index": result.severity_index,
            "risk_level": result.risk_level,
            "latitude": result.latitude,
            "longitude": result.longitude,
            "gps_status": result.gps_status,
            "orthomosaic_b64": b64,
            "edge_map_b64": edge_b64,
            "recommendations": result.recommendations,
            "depth_map_data": result.depth_map_data,
        }
    finally:
        shutil.rmtree(tmp_folder, ignore_errors=True)

@app.get("/health")
def health():
    return {
        "project": "AEGIS Unified API",
        "status": "operational",
        "base_dir": BASE_DIR,
        "dummy_dir": DUMMY_DIR,
        "dummy_exists": os.path.exists(DUMMY_DIR)
    }
