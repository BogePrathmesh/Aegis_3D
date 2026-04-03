import os
import cv2
import numpy as np
import uuid
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import app.services.simulation_engine as simulation_engine

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_FOLDER = os.path.join(DATA_DIR, "uploads")
MASK_FOLDER = os.path.join(DATA_DIR, "masks")
DEPTH_FOLDER = os.path.join(DATA_DIR, "depth")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "tiff"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_crack_mask(image_path):
    # Use imdecode for better compatibility with Windows paths (spaces/unicode)
    try:
        img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None: 
            print(f"FAILED to read image at {image_path} via cv2")
            return None
    except Exception as e:
        print(f"ERROR reading image: {e}")
        return None
        
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Stronger bilateral filter to remove surface texture (bricks/grain) but keep crack edges
    smoothed = cv2.bilateralFilter(gray, 9, 85, 85)
    
    # Finer thresholding for thin cracks
    thresh = cv2.adaptiveThreshold(smoothed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY_INV, 17, 9)
    
    kernel = np.ones((3, 3), np.uint8)
    # Remove small noise dots
    opened = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
    # Close small gaps in cracks without bloating them
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    final_mask = np.zeros_like(gray)
    if contours:
        # Sort by area and pick top candidates
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        for cnt in contours[:15]:
            area = cv2.contourArea(cnt)
            if area > 15:
                # Use thickness 2 instead of FILLED to maintain "hollow" crack look if they are wide
                # or just draw the skeleton
                cv2.drawContours(final_mask, [cnt], -1, 255, thickness=2)
                if area > 500: # Only fill really large definite holes
                    cv2.drawContours(final_mask, [cnt], -1, 255, thickness=cv2.FILLED)
    
    return final_mask

def generate_depth_map(image_path, mask=None):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None: return None
    depth = img.astype(np.float32) / 255.0
    depth_blurred = cv2.GaussianBlur(depth, (21, 21), 10)
    if mask is not None:
        mask_norm = mask.astype(np.float32) / 255.0
        depth_blurred = depth_blurred * (1.0 - mask_norm * 0.8)
    return (depth_blurred * 255).astype(np.uint8)

def analyze_crack_properties(mask):
    if mask is None: return {"length": 100, "width": 5, "depth": 10, "severity": 0.5}
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours: return {"length": 100, "width": 5, "depth": 10, "severity": 0.5}
    largest = max(contours, key=cv2.contourArea)
    rect = cv2.minAreaRect(largest)
    length = max(rect[1][0], rect[1][1])
    width = min(rect[1][0], rect[1][1])
    crack_pixels = np.sum(mask > 0)
    total_pixels = mask.shape[0] * mask.shape[1]
    severity = min(crack_pixels / total_pixels * 20, 1.0)
    return {
        "length": float(length),
        "width": float(max(width, 3)),
        "depth": float(length * 0.1),
        "severity": float(severity),
        "num_cracks": len(contours),
    }

@router.post("/upload")
async def upload_image(image: UploadFile = File(...)):
    if not allowed_file(image.filename):
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    session_id = str(uuid.uuid4())[:8]
    ext = image.filename.rsplit(".", 1)[1].lower()
    filename = f"{session_id}_original.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    contents = await image.read()
    with open(filepath, "wb") as f:
        f.write(contents)
        
    img = cv2.imread(filepath)
    if img is None: raise HTTPException(status_code=400, detail="Could not read image")
    h, w = img.shape[:2]
    
    mask = generate_crack_mask(filepath)
    mask_filename = None
    if mask is not None:
        mask_filename = f"{session_id}_mask.png"
        cv2.imwrite(os.path.join(MASK_FOLDER, mask_filename), mask)

    depth = generate_depth_map(filepath, mask)
    depth_filename = None
    if depth is not None:
        depth_filename = f"{session_id}_depth.png"
        cv2.imwrite(os.path.join(DEPTH_FOLDER, depth_filename), depth)

    props = analyze_crack_properties(mask)
    return {
        "session_id": session_id,
        "filename": filename,
        "mask_filename": mask_filename,
        "depth_filename": depth_filename,
        "width": w,
        "height": h,
        "crack_properties": props,
    }

@router.get("/simulate/{structure_id}")
def run_simulation(structure_id: int):
    result = simulation_engine.simulate_structure(structure_id, BASE_DIR)
    return result

@router.get("/simulate-upload/{session_id}")
def run_upload_simulation(session_id: str):
    orig_path = None
    for ext in ["png", "jpg", "jpeg"]:
        p = os.path.normpath(os.path.join(UPLOAD_FOLDER, f"{session_id}_original.{ext}"))
        print(f"Checking for upload at: {p}")
        if os.path.exists(p):
            orig_path = p
            break
            
    mask_path = os.path.normpath(os.path.join(MASK_FOLDER, f"{session_id}_mask.png"))
    print(f"Checking for mask at: {mask_path}")
    if not (orig_path and os.path.exists(mask_path)):
        print(f"404 triggered in simulate_upload for {session_id}")
        raise HTTPException(status_code=404, detail=f"Assets not found for session {session_id}. Mask Exists: {os.path.exists(mask_path)}")
        
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    props = analyze_crack_properties(mask)
    
    init_data = {
        "crack_length": props['length'],
        "crack_width": props['width'],
        "crack_depth": props['depth'],
        "health_score": 100.0 - (props['severity'] * 50),
        "age": 10
    }
    
    result = simulation_engine.simulate_by_assets(
        BASE_DIR, orig_path, mask_path, None, init_data, output_prefix=f"sim_upload_{session_id}"
    )
    result['structure'] = {
        "id": session_id,
        "structure_name": f"Session {session_id}",
        "structure_type": "Uploaded Asset",
        "health_score": init_data["health_score"]
    }
    return result
