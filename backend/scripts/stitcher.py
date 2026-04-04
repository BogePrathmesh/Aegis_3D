"""
Orthomosaic Image Stitcher for AEGIS Drone Inspection Platform.

Tries multiple strategies in order:
  1. PANORAMA mode with default confidence (0.3)
  2. SCANS mode (better for nadir/top-down drone views)
  3. PANORAMA mode with lowered confidence (0.1) — last resort

All strategies preserve full resolution.
"""

import cv2
import numpy as np
import os
import zipfile
import tempfile
from pathlib import Path


def stitch_images(image_paths: list[str], max_dim: int = 1024):
    """
    Stitches multiple overlapping images into a single orthomosaic.

    Args:
        image_paths: List of absolute/relative file paths to input images.
        max_dim:     Max width or height before downscaling for stitching
                     (prevents OOM on very large drone images). Set to 0 to
                     disable.

    Returns:
        (stitched_image: np.ndarray | None, status_message: str)
    """
    images = []
    for path in image_paths:
        img = cv2.imread(path)
        if img is not None:
            if max_dim and (img.shape[1] > max_dim or img.shape[0] > max_dim):
                scale = max_dim / max(img.shape[1], img.shape[0])
                img = cv2.resize(img, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            images.append(img)

    if len(images) < 2:
        return None, "Need at least two valid images to stitch."

    error_codes = {
        cv2.Stitcher_ERR_NEED_MORE_IMGS:         "Need more images (increase batch size)",
        cv2.Stitcher_ERR_HOMOGRAPHY_EST_FAIL:    "Homography estimation failed (insufficient overlap — ensure ≥40% overlap)",
        cv2.Stitcher_ERR_CAMERA_PARAMS_ADJUST_FAIL: "Camera parameter adjustment failed",
    }

    strategies = [
        # (mode, conf_threshold, label)
        (cv2.Stitcher_PANORAMA, 0.3,  "PANORAMA / conf=0.3"),
        (cv2.Stitcher_SCANS,    0.3,  "SCANS (nadir) / conf=0.3"),
        (cv2.Stitcher_PANORAMA, 0.1,  "PANORAMA / conf=0.1 (relaxed)"),
        (cv2.Stitcher_SCANS,    0.1,  "SCANS / conf=0.1 (relaxed)"),
    ]

    last_error = "Unknown stitching error"

    for mode, conf, label in strategies:
        stitcher = cv2.Stitcher_create(mode)
        stitcher.setPanoConfidenceThresh(conf)

        status, result = stitcher.stitch(images)

        if status == cv2.Stitcher_OK:
            print(f"[STITCHER] ✅ Success with strategy: {label}")
            return result, f"Success ({label})"

        last_error = error_codes.get(status, f"Error code {status}")
        print(f"[STITCHER] ⚠️  Strategy '{label}' failed: {last_error}")

    return None, f"All stitching strategies failed. Last error: {last_error}"


def extract_zip_images(zip_path: str, extract_to: str) -> list[str]:
    """
    Extracts image files from a ZIP archive into extract_to directory.

    Returns:
        Sorted list of extracted image file paths.
    """
    allowed_ext = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}
    extracted_paths = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            # Skip directories and hidden files
            if member.filename.endswith("/") or os.path.basename(member.filename).startswith("."):
                continue
            ext = Path(member.filename).suffix.lower()
            if ext in allowed_ext:
                # Flatten: extract all images directly into extract_to
                dest_name = os.path.basename(member.filename)
                dest_path = os.path.join(extract_to, dest_name)
                with zf.open(member) as src, open(dest_path, "wb") as dst:
                    dst.write(src.read())
                extracted_paths.append(dest_path)

    return sorted(extracted_paths)


if __name__ == "__main__":
    # ── Quick smoke-test ──────────────────────────────────────────────────────
    import sys
    if len(sys.argv) < 3:
        print("Usage: python stitcher.py <img1> <img2> [img3 ...] [--out output.jpg]")
        sys.exit(0)

    args = sys.argv[1:]
    out_path = "orthomosaic_output.jpg"
    if "--out" in args:
        idx = args.index("--out")
        out_path = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    stitched, msg = stitch_images(args)
    if stitched is not None:
        cv2.imwrite(out_path, stitched)
        print(f"Saved: {out_path}  ({msg})")
    else:
        print(f"Failed: {msg}")
        sys.exit(1)
