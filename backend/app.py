import os
import cv2
import numpy as np
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import uuid
import json

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
    """Auto-detect cracks using edge detection and thresholding."""
    img = cv2.imread(image_path)
    if img is None:
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Enhance contrast
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Edge detection
    edges = cv2.Canny(enhanced, 50, 150)

    # Morphological operations to connect crack segments
    kernel = np.ones((3, 3), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=2)
    closed = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel, iterations=3)

    # Find crack-like thin structures using tophat
    kernel_large = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    tophat = cv2.morphologyEx(enhanced, cv2.MORPH_BLACKHAT, kernel_large)
    _, thresh = cv2.threshold(tophat, 30, 255, cv2.THRESH_BINARY)

    # Combine edge and tophat
    combined = cv2.bitwise_or(closed, thresh)

    # Remove noise
    combined = cv2.GaussianBlur(combined, (3, 3), 0)
    _, final_mask = cv2.threshold(combined, 50, 255, cv2.THRESH_BINARY)

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


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "message": "Structural Degradation API running"})


if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")
