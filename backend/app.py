import os
import cv2
import numpy as np
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import uuid
import json
import budget_db

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "Data", "uploads")
MASK_FOLDER = os.path.join(BASE_DIR, "Data", "masks")
DEPTH_FOLDER = os.path.join(BASE_DIR, "Data", "depth")
FRAMES_FOLDER = os.path.join(BASE_DIR, "Data", "simulation_frames")

for folder in [UPLOAD_FOLDER, MASK_FOLDER, DEPTH_FOLDER, FRAMES_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "tiff"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_crack_mask(image_path):
    """Auto-detect cracks and filter out background noise (like asphalt texture)."""
    img = cv2.imread(image_path)
    if img is None:
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Use a bilateral filter to smooth noise while keeping edges sharp
    smoothed = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # Adaptive thresholding to find deep cracks
    thresh = cv2.adaptiveThreshold(smoothed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY_INV, 15, 5)

    # Morphological operations to link cracks and remove small dots
    kernel = np.ones((3, 3), np.uint8)
    opened = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel, iterations=2)

    # Find contours to filter out small asphalt noise
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    final_mask = np.zeros_like(gray)
    
    if contours:
        # Keep only contours above a certain area threshold
        # Or sort them and keep the top N largest
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        # Keep top 10 largest features or those with Area > 100
        for cnt in contours[:10]:
            if cv2.contourArea(cnt) > 50:
                cv2.drawContours(final_mask, [cnt], -1, 255, thickness=cv2.FILLED)
                # optionally draw line matching the contour to widen it a bit
                cv2.drawContours(final_mask, [cnt], -1, 255, thickness=2)

    return final_mask


def generate_depth_map(image_path, mask=None):
    """Generate a simple depth map from image."""
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None

    # Normalize to 0-1
    depth = img.astype(np.float32) / 255.0

    # Apply Gaussian blur to simulate depth
    depth_blurred = cv2.GaussianBlur(depth, (21, 21), 10)

    if mask is not None:
        # Make crack regions appear as depressions (dark in depth map)
        mask_norm = mask.astype(np.float32) / 255.0
        depth_blurred = depth_blurred * (1.0 - mask_norm * 0.8)

    depth_uint8 = (depth_blurred * 255).astype(np.uint8)
    return depth_uint8


def analyze_crack_properties(mask):
    """Analyze crack properties from mask."""
    if mask is None:
        return {"length": 100, "width": 5, "depth": 10, "severity": 0.5}

    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return {"length": 100, "width": 5, "depth": 10, "severity": 0.5}

    # Get largest contour as primary crack
    largest = max(contours, key=cv2.contourArea)
    rect = cv2.minAreaRect(largest)

    length = max(rect[1][0], rect[1][1])
    width = min(rect[1][0], rect[1][1])

    # Calculate severity based on mask coverage
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


@app.route("/api/upload", methods=["POST"])
def upload_image():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400

    # Generate unique session ID
    session_id = str(uuid.uuid4())[:8]
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{session_id}_original.{ext}"

    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # Get image dimensions
    img = cv2.imread(filepath)
    if img is None:
        return jsonify({"error": "Could not read image"}), 400

    h, w = img.shape[:2]

    # Generate crack mask
    mask = generate_crack_mask(filepath)
    mask_filename = None
    if mask is not None:
        mask_filename = f"{session_id}_mask.png"
        cv2.imwrite(os.path.join(MASK_FOLDER, mask_filename), mask)

    # Generate depth map
    depth = generate_depth_map(filepath, mask)
    depth_filename = None
    if depth is not None:
        depth_filename = f"{session_id}_depth.png"
        cv2.imwrite(os.path.join(DEPTH_FOLDER, depth_filename), depth)

    # Analyze crack properties
    props = analyze_crack_properties(mask)

    return jsonify(
        {
            "session_id": session_id,
            "filename": filename,
            "mask_filename": mask_filename,
            "depth_filename": depth_filename,
            "width": w,
            "height": h,
            "crack_properties": props,
        }
    )


@app.route("/api/uploads/<filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/api/masks/<filename>")
def serve_mask(filename):
    return send_from_directory(MASK_FOLDER, filename)


@app.route("/api/depth/<filename>")
def serve_depth(filename):
    return send_from_directory(DEPTH_FOLDER, filename)


@app.route("/api/structures", methods=["GET"])
def get_structures():
    return jsonify(budget_db.get_all_structures())

@app.route("/api/optimize-budget", methods=["POST"])
def optimize_budget_endpoint():
    data = request.json or {}
    budget = float(data.get("budget", 50))
    result = budget_db.optimize_budget(budget)
    return jsonify(result)
    

import simulation_engine

@app.route("/api/simulate/<int:structure_id>", methods=["GET"])
def run_simulation(structure_id):
    result = simulation_engine.simulate_structure(structure_id, BASE_DIR)
    return jsonify(result)

@app.route("/api/frames/<filename>")
def serve_frames(filename):
    return send_from_directory(FRAMES_FOLDER, filename)

@app.route("/api/simulate-upload/<session_id>", methods=["GET"])
def run_upload_simulation(session_id):
    # Find assets for this session
    orig_path = None
    for ext in ["png", "jpg", "jpeg"]:
        p = os.path.join(UPLOAD_FOLDER, f"{session_id}_original.{ext}")
        if os.path.exists(p):
            orig_path = p
            break
            
    mask_path = os.path.join(MASK_FOLDER, f"{session_id}_mask.png")
    
    if not (orig_path and os.path.exists(mask_path)):
        return jsonify({"error": "Assets not found for session"}), 404
        
    # Analyze initial props for simulation parameters
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    props = analyze_crack_properties(mask)
    
    # Generic init data for an upload
    init_data = {
        "crack_length": props['length'],
        "crack_width": props['width'],
        "crack_depth": props['depth'],
        "health_score": 100.0 - (props['severity'] * 50), # Rough initial health
        "age": 10 # Default age for unknown uploads
    }
    
    result = simulation_engine.simulate_by_assets(
        BASE_DIR, 
        orig_path, 
        mask_path, 
        None, 
        init_data, 
        output_prefix=f"sim_upload_{session_id}"
    )
    
    # Mock structure data for frontend
    result['structure'] = {
        "id": session_id,
        "structure_name": f"Session {session_id}",
        "structure_type": "Uploaded Asset",
        "health_score": init_data["health_score"]
    }
    
    return jsonify(result)

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "message": "Structural Degradation API running", "budget_db": "connected"})


if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")
