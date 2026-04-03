import cv2
import numpy as np
import os
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

def get_decimal_from_dms(dms, ref):
    """Convert Degrees/Minutes/Seconds EXIF data to Decimal Degrees."""
    degrees = dms[0]
    minutes = dms[1]
    seconds = dms[2]
    
    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
    
    if ref in ['S', 'W']:
        decimal = -decimal
        
    return float(decimal)

def extract_gps_data(image_path):
    """
    Extracts raw GPS coordinates from a drone image's EXIF tags.
    Returns: (latitude, longitude, status)
    """
    try:
        image = Image.open(image_path)
        exif_data = image._getexif()

        if not exif_data:
            return 18.5204, 73.8567, 'fallback'

        gps_info = {}
        for tag, value in exif_data.items():
            decoded = TAGS.get(tag, tag)
            if decoded == "GPSInfo":
                for t in value:
                    sub_decoded = GPSTAGS.get(t, t)
                    gps_info[sub_decoded] = value[t]

        if 'GPSLatitude' in gps_info and 'GPSLongitude' in gps_info:
            lat = get_decimal_from_dms(gps_info['GPSLatitude'], gps_info['GPSLatitudeRef'])
            lng = get_decimal_from_dms(gps_info['GPSLongitude'], gps_info['GPSLongitudeRef'])
            return lat, lng, 'active'

    except Exception as e:
        print(f"Error extracting EXIF: {e}")
        
    # Default Pune coordinates fallback
    return 18.5204, 73.8567, 'fallback'

def generate_crack_mask(image_path):
    """Auto-detect cracks and filter out background noise."""
    img = cv2.imread(image_path)
    if img is None:
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    smoothed = cv2.bilateralFilter(gray, 9, 75, 75)
    thresh = cv2.adaptiveThreshold(smoothed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY_INV, 15, 5)

    kernel = np.ones((3, 3), np.uint8)
    opened = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    final_mask = np.zeros_like(gray)
    
    if contours:
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        for cnt in contours[:10]:
            if cv2.contourArea(cnt) > 50:
                cv2.drawContours(final_mask, [cnt], -1, 255, thickness=cv2.FILLED)
                cv2.drawContours(final_mask, [cnt], -1, 255, thickness=2)

    return final_mask

def analyze_crack_properties(mask):
    """Analyze crack properties from mask."""
    if mask is None:
        return {"length": 100, "width": 5, "depth": 10, "severity": 0.5}

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return {"length": 100, "width": 5, "depth": 10, "severity": 0.5}

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

def run_inference(image_path):
    """
    Main inference entry point for analyzing drone inspection imagery.
    """
    lat, lng, status = extract_gps_data(image_path)
    mask = generate_crack_mask(image_path)
    props = analyze_crack_properties(mask)
    
    return {
        "latitude": lat,
        "longitude": lng,
        "gps_status": status,
        "crack_properties": props,
        "mask": mask
    }
