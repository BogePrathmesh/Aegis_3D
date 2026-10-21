"""
Full inference pipeline for structural crack analysis.

Pipeline stages:
  1. Crack Detection    — YOLOv8 bounding boxes
  2. Crack Segmentation — YOLOv8-seg pixel masks
  3. Health Score        — weighted composite (0-100)
  4. Risk Level         — Critical / High / Medium / Low / Safe
  5. Annotated Output   — image with overlays, gauge, recommendations

Health-score formula (aligned with IS:456-2000 & ACI 224R):
  40 %  total crack area
  30 %  maximum crack width
  20 %  crack density (count relative to image)
  10 %  crack-type severity
"""

import os
import logging
import cv2
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional
from ultralytics import YOLO
from PIL import Image as PilImage
from PIL.ExifTags import TAGS, GPSTAGS

# U-Net integration (preserved for reference/future integration; disabled for stable YOLO baseline)
ENABLE_UNET: bool = False

try:
    from app.services.unet_model import (
        run_unet_inference,
        overlay_unet_mask,
        compute_agreement,
        get_unet_model,
    )
    UNET_AVAILABLE = True
except ImportError:
    UNET_AVAILABLE = False

# Material classifier (optional — falls back gracefully if weights unavailable)
try:
    from app.services.material_classifier import classify_surface_material
    MATERIAL_CLASSIFIER_AVAILABLE = True
except Exception:
    MATERIAL_CLASSIFIER_AVAILABLE = False
    def classify_surface_material(bgr_image):
        return {"material": "unknown", "label": "Unknown / Uncertain",
                "confidence": 0.0, "source": "Classifier unavailable",
                "note": "", "all_scores": {}, "error": "Import failed"}

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# GEOMETRY & MEASUREMENT HELPERS
# ─────────────────────────────────────────────

def apply_nms(boxes_xyxy: List[List[float]], confidences: List[float], score_thresh: float = 0.25, nms_thresh: float = 0.45) -> List[int]:
    """
    Filter overlapping bounding boxes using OpenCV Non-Maximum Suppression (NMS).
    Prevents counting overlapping duplicate YOLO detections as separate fractures.
    """
    if len(boxes_xyxy) == 0:
        return []
    boxes_xywh = []
    for b in boxes_xyxy:
        boxes_xywh.append([int(b[0]), int(b[1]), int(max(1, b[2] - b[0])), int(max(1, b[3] - b[1]))])
    indices = cv2.dnn.NMSBoxes(boxes_xywh, confidences, score_thresh, nms_thresh)
    if len(indices) == 0:
        return []
    if isinstance(indices, np.ndarray):
        indices = indices.flatten().tolist()
    return [int(i) for i in indices]


def compute_max_fracture_width_px(binary_mask: np.ndarray) -> float:
    """
    Computes maximum fracture aperture/caliper width in pixels using Euclidean Distance Transform (EDT).
    Returns 2 * max distance transform value (inscribed diameter of widest crack channel).
    """
    if binary_mask is None or np.sum(binary_mask) == 0:
        return 0.0
    dist = cv2.distanceTransform((binary_mask > 0).astype(np.uint8), cv2.DIST_L2, 5)
    max_radius = float(np.max(dist)) if np.max(dist) > 0 else 0.0
    return round(max_radius * 2.0, 1)


def count_distinct_crack_regions(binary_mask: np.ndarray, min_area_px: int = 15) -> int:
    """
    Count distinct spatially separated crack regions using 8-way connected components analysis.
    Filters out background and small noise speckles below min_area_px.
    """
    if binary_mask is None or np.sum(binary_mask) == 0:
        return 0
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        (binary_mask > 0).astype(np.uint8), connectivity=8
    )
    valid = [i for i in range(1, num_labels) if stats[i, cv2.CC_STAT_AREA] >= min_area_px]
    return len(valid)

# ─────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────

@dataclass
class CrackDetection:
    bbox: List[float]          # [x1, y1, x2, y2]
    confidence: float
    crack_type: str            # hairline / longitudinal / transverse / alligator / structural
    area_pixels: int
    area_percentage: float     # % of total image
    width_pixels: float        # estimated crack width
    length_pixels: float       # estimated crack length


@dataclass
class InspectionResult:
    image_path: str
    structure_type: str        # building / road / bridge
    detections: List[CrackDetection]
    total_crack_area_pct: float
    max_crack_width: float
    crack_density: float       # cracks per normalised image
    health_score: float        # 0-100
    severity_index: float      # 0-100 (higher = more danger)
    risk_level: str
    risk_color: tuple          # BGR
    recommendations: List[str]
    annotated_image: np.ndarray
    edge_detected_image: np.ndarray
    depth_map_data: Optional[List[List[float]]] = None
    latitude: float = 18.5204
    longitude: float = 73.8567
    gps_status: str = "fallback"
    # ── U-Net fields (None when U-Net is unavailable or fails) ──────────
    unet_mask: Optional[np.ndarray] = None          # binary uint8 mask at original resolution
    unet_overlay_image: Optional[np.ndarray] = None # BGR image with U-Net overlay
    yolo_only_image: Optional[np.ndarray] = None    # BGR image with only YOLO boxes (no U-Net)
    unet_crack_area_pct: Optional[float] = None     # crack area % from U-Net mask
    model_agreement: Optional[str] = None           # 'agree' | 'partial' | 'disagree'
    agreement_iou: Optional[float] = None           # IoU between U-Net mask and YOLO box pixels
    agreement_note: Optional[str] = None            # human-readable explanation of disagreement
    # ── Calibration & Material metadata (backward compatible defaults) ──
    material_type: str = "concrete"           # user-selected fallback
    material_ai: str = "unknown"              # AI-classified surface material
    material_ai_label: str = "Unknown / Uncertain"  # human-readable label
    material_ai_confidence: float = 0.0       # cosine similarity [0..1]
    material_source: str = "User-selected material"  # display source label
    calibration_status: str = "Uncalibrated — pixels only"
    crack_width_unit: str = "px"
    max_crack_width_mm: Optional[float] = None
    base_damage_penalty: float = 0.0

# ─────────────────────────────────────────────
# CRACK ANALYSER
# ─────────────────────────────────────────────

class CrackAnalyzer:

    def __init__(
        self,
        detection_weights: str = "models/crack_detection/weights/best.pt",
        segmentation_weights: str = "models/crack_segmentation/weights/best.pt",
        confidence_threshold: float = 0.15,
    ):
        print("Loading detection model …")
        self.det_model = YOLO(detection_weights)

        self.seg_model = None
        if os.path.exists(segmentation_weights):
            print("Loading segmentation model …")
            self.seg_model = YOLO(segmentation_weights)
        else:
            print("Segmentation weights not found — detection-only mode")

        self.conf_threshold = confidence_threshold

    # ── GPS extraction ──────────────────────
    @staticmethod
    def extract_gps(image_path: str):
        """Extract GPS degrees from EXIF and convert to decimal."""
        try:
            img = PilImage.open(image_path)
            gps_info = {}
            
            # Modern Pillow EXIF extraction
            exif = img.getexif()
            if exif:
                gps_ifd = exif.get_ifd(0x8825) # GPSInfo IFD
                if gps_ifd:
                    for t, value in gps_ifd.items():
                        sub_decoded = GPSTAGS.get(t, t)
                        gps_info[sub_decoded] = value

            # Legacy fallback
            if not gps_info and hasattr(img, '_getexif') and img._getexif():
                old_exif = img._getexif()
                for tag, value in old_exif.items():
                    decoded = TAGS.get(tag, tag)
                    if decoded == "GPSInfo":
                        for t in value:
                            sub_decoded = GPSTAGS.get(t, t)
                            gps_info[sub_decoded] = value[t]

            if not gps_info:
                return 18.5204, 73.8567, "fallback"

            def to_decimal(coords, ref):
                # Check for various formats (older Pillow versions vs modern IFDRational)
                d = float(coords[0].numerator / coords[0].denominator) if hasattr(coords[0], 'numerator') else float(coords[0])
                m = float(coords[1].numerator / coords[1].denominator) if hasattr(coords[1], 'numerator') else float(coords[1])
                s = float(coords[2].numerator / coords[2].denominator) if hasattr(coords[2], 'numerator') else float(coords[2])
                decimal = d + (m / 60.0) + (s / 3600.0)
                if ref in ['S', 'W']: decimal = -decimal
                return decimal

            if "GPSLatitude" in gps_info and "GPSLongitude" in gps_info:
                lat = to_decimal(gps_info["GPSLatitude"], gps_info.get("GPSLatitudeRef", "N"))
                lng = to_decimal(gps_info["GPSLongitude"], gps_info.get("GPSLongitudeRef", "E"))
                return lat, lng, "real"

        except Exception as e:
            print(f"EXIF read error: {e}")
            
        return 18.5204, 73.8567, "fallback"

    # ── geometry helpers ──────────────────────

    @staticmethod
    def classify_crack_type(bbox, img_shape):
        """Classify by aspect ratio and relative area."""
        x1, y1, x2, y2 = bbox
        w = x2 - x1
        h = y2 - y1
        aspect = max(w, h) / (min(w, h) + 1e-6)
        area_pct = (w * h) / (img_shape[0] * img_shape[1]) * 100

        if area_pct < 0.5:
            return "hairline"
        if aspect > 5:
            return "longitudinal" if w > h else "transverse"
        if area_pct > 5:
            return "alligator"
        return "structural"

    @staticmethod
    def estimate_crack_metrics(img, bbox, mask=None):
        """
        Calculates area and width metrics inside the bounding box.
        If a unified segmentation mask is provided, metrics are derived from the mask pixels.
        Otherwise falls back to Canny edge detection.
        """
        x1, y1, x2, y2 = map(int, bbox)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(img.shape[1], x2), min(img.shape[0], y2)

        crop = img[y1:y2, x1:x2]
        if crop.size == 0:
            return 0.0, 0.0, None

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 1.4)
        edges = cv2.Canny(blurred, 50, 150)

        if mask is not None:
            crop_mask = mask[y1:y2, x1:x2]
            if crop_mask.size > 0 and np.sum(crop_mask) > 0:
                real_area = float(np.count_nonzero(crop_mask))
                dist = cv2.distanceTransform((crop_mask > 0).astype(np.uint8), cv2.DIST_L2, 5)
                max_w = float(np.max(dist) * 2.0) if np.max(dist) > 0 else 1.0
                return real_area, max_w, edges

        # Fallback to Canny edge pixel count and distance transform
        edge_pts = np.count_nonzero(edges)
        real_area = float(edge_pts)
        if edge_pts > 0:
            dist = cv2.distanceTransform((edges > 0).astype(np.uint8), cv2.DIST_L2, 5)
            max_w = float(np.max(dist) * 2.0) if np.max(dist) > 0 else 1.0
        else:
            max_w = 0.0
        return real_area, max_w, edges

    def generate_3d_depth_map(self, img, detections):
        """Generates a pseudo-depth topographical array for raw WebGL rendering."""
        if not detections:
            return None
        
        # Target the largest crack
        largest = max(detections, key=lambda d: d.area_percentage)
        x1, y1, x2, y2 = map(int, largest.bbox)
        
        h, w = img.shape[:2]
        pad = int(min(h, w) * 0.1) # 10% padding
        x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
        x2, y2 = min(w, x2 + pad), min(h, y2 + pad)
        
        crop = img[y1:y2, x1:x2]
        if crop.size == 0: return None
        
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Map intensity to physical depth topography
        Z = gray.astype(np.float32)
        Z_surface = np.percentile(Z, 80)
        Z_depth = Z_surface - Z
        Z_depth[Z_depth < 0] = 0
        if np.max(Z_depth) > 0:
            Z_depth = Z_depth / np.max(Z_depth)
            
        Z_plot = -Z_depth

        # Downsample for ultra-fast pure JSON stringification
        target_w = 60
        scale_percent = min(100.0, (target_w / max(1.0, float(Z_plot.shape[1]))) * 100.0)
        new_w = max(10, int(Z_plot.shape[1] * scale_percent / 100.0))
        new_h = max(10, int(Z_plot.shape[0] * scale_percent / 100.0))
        Z_plot_small = cv2.resize(Z_plot, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        Z_plot_small = cv2.GaussianBlur(Z_plot_small, (3, 3), 0)

        # Return as serialised List[List[float]]
        return Z_plot_small.tolist()

    # ── health score ──────────────────────────

    def calculate_health_score(
        self,
        coverage_pct: float,
        max_fracture_px: float,
        anomaly_count: int,
        structure_type: str = "building",
        material_type: str = "concrete",
        detections: Optional[List[CrackDetection]] = None,
        img_diagonal_px: float = 1000.0,
    ) -> float:
        """
        Heuristic Physical Condition Score (0-100, higher = better).

        This is a SCREENING HEURISTIC, not a validated engineering assessment.
        Scores are computed from visible surface crack measurements only.
        Concealed, subsurface, or structural defects are not captured.

        Sub-penalties (all capped individually):
          P_coverage (0-40): proportional to crack-mask area % of image
          P_width    (0-30): proportional to max fracture width as % of image diagonal
          P_count    (0-15): proportional to distinct anomaly regions
          P_type     (0-15): crack morphology severity class

        Final score = max(0, 100 - (P_coverage + P_width + P_count + P_type)
                                   * struct_factor * material_factor)
        """
        if coverage_pct <= 0.0 and max_fracture_px <= 0.0 and anomaly_count == 0 and (not detections or len(detections) == 0):
            return 100.0

        # P_coverage: 5% crack area → ~40pt (full cap). Linear, reasonable.
        p_cov = min(40.0, coverage_pct * 8.0)

        # P_width: normalize fracture width to % of image diagonal so the penalty is
        # scale-invariant. A 20px crack on an 800px diagonal ≈ 2.5% → 15pt penalty.
        # Formula: (fracture_px / img_diagonal_px) * 100 * 6.0, capped at 30.
        norm_width_pct = (max_fracture_px / max(img_diagonal_px, 1.0)) * 100.0
        p_width = min(30.0, norm_width_pct * 6.0)

        # P_count: cap at 6 anomaly regions (beyond that counts as "extensive network")
        p_count = min(15.0, anomaly_count * 2.5)

        type_penalties = {
            "hairline": 2.0,
            "longitudinal": 6.0,
            "transverse": 8.0,
            "structural": 12.0,
            "alligator": 15.0,
        }
        max_tp = 0.0
        if detections:
            max_tp = max((type_penalties.get(d.crack_type, 5.0) for d in detections), default=0.0)

        p_damage = p_cov + p_width + p_count + max_tp

        struct_multipliers = {
            "bridge": 1.20,
            "dam": 1.25,
            "building": 1.00,
            "road": 0.85,
        }
        sm = struct_multipliers.get(structure_type.lower(), 1.00)

        mat_multipliers = {
            "brick_masonry": 1.20,
            "masonry": 1.20,
            "brick": 1.20,
            "concrete": 1.00,
            "stone": 1.10,
            "asphalt": 0.85,
            "plaster": 0.70,
            "steel": 1.00,
            "unknown": 1.00,
        }
        mm = mat_multipliers.get(material_type.lower(), 1.00)

        total_penalty = p_damage * sm * mm
        health_score = round(max(0.0, min(100.0, 100.0 - total_penalty)), 1)
        return health_score

    def calculate_severity_index(
        self,
        health_score: float,
        coverage_pct: float,
        max_fracture_px: float,
        anomaly_count: int,
        age_years: int = 10,
        is_seismic: bool = False,
        is_near_sea: bool = False,
        is_heavy_traffic: bool = False,
        structure_type: str = "building",
        material_type: str = "concrete",
    ) -> float:
        """
        Documented Structural Severity Index (SSI) (0-100, Higher = Worse Risk).
        Combines measured physical damage with operational/environmental hazard multipliers.
        """
        crack_penalty = 100.0 - health_score

        # Environmental Factor Multiplier (1.0 to 1.6)
        env_boost = 0.0
        if is_seismic:
            env_boost += 0.20
        if is_near_sea:
            env_boost += 0.15
        if is_heavy_traffic:
            env_boost += 0.15

        # Age Multiplier for crack propagation
        age_multiplier = 1.0
        if age_years > 50:
            age_multiplier = 1.50
        elif age_years > 20:
            age_multiplier = 1.25
        elif age_years > 5:
            age_multiplier = 1.10

        # Base aging & zone degradation (non-zero even on 0 visible surface cracks)
        base_degradation = age_years * 0.10
        flat_hazard = 0.0
        if is_seismic:
            flat_hazard += 4.0
        if is_near_sea:
            flat_hazard += 3.0
        if is_heavy_traffic:
            flat_hazard += 2.0

        ssi = (crack_penalty * age_multiplier * (1.0 + env_boost)) + base_degradation + flat_hazard
        return round(min(100.0, max(0.0, ssi)), 1)

    # ── risk level ────────────────────────────

    @staticmethod
    def get_risk_level(severity_index: float, coverage_pct: float = 0.0) -> tuple:
        """
        Maps severity_index (0-100) to consistent risk categories:
          SSI < 20.0:  Safe / Low
          20 <= SSI < 40: Low
          40 <= SSI < 65: Medium
          65 <= SSI < 80: High
          SSI >= 80: Critical
        """
        if severity_index >= 80.0:
            return "Critical", (36, 36, 235), "Critical Risk: Immediate structural safety evaluation required."
        elif severity_index >= 65.0:
            return "High", (15, 105, 245), "High Risk: Urgent engineering inspection and monitoring required."
        elif severity_index >= 40.0:
            return "Medium", (11, 175, 245), "Medium Risk: Scheduled inspection and maintenance review advised."
        elif severity_index >= 20.0:
            return "Low", (235, 150, 40), "Low Risk: Minor surface deterioration; routine periodic monitoring."
        else:
            if coverage_pct > 0.0:
                return "Safe", (50, 180, 50), "Minimal Risk: Isolated cosmetic crack; continue standard maintenance."
            else:
                return "Safe", (50, 180, 50), "Minimal Risk: No significant surface cracks detected in image."

    # ── recommendations ───────────────────────

    @staticmethod
    def get_recommendations(
        detections,
        health_score,
        severity_index,
        structure_type,
        age_years,
        is_seismic,
        is_near_sea,
        is_heavy_traffic,
        coverage_pct: float = 0.0,
        max_fracture_px: float = 0.0,
        calibration_status: str = "Uncalibrated — pixels only",
        px_to_mm: Optional[float] = None,
    ) -> List[str]:
        recs = []
        
        # Decision-support header (replaces unsupported compliance claims)
        recs.append("DECISION-SUPPORT EVALUATION (PRELIMINARY SCREENING)")

        if age_years > 50:
            recs.append(f"Historical/Aged Asset ({age_years} yrs): Detailed non-destructive structural audit recommended.")
        elif age_years > 20:
            recs.append(f"Aging Asset ({age_years} yrs): Periodic structural health monitoring advised.")
            
        if is_seismic:
            recs.append("Seismic Hazard Zone: Verify lateral load ductility and joint displacement tolerance.")
        if is_near_sea:
            recs.append("Marine Environment: High risk of chloride-induced rebar corrosion and spalling.")
        if is_heavy_traffic:
            if structure_type.lower() in ["road", "bridge"]:
                recs.append("Dynamic Heavy Traffic: Assess cyclic fatigue and repetitive impact cracking.")
            else:
                recs.append("Heavy Live Load: Assess slab deflection, beam shear stress, and cyclic fatigue.")

        # If no crack detected
        if coverage_pct <= 0.0 and (not detections or len(detections) == 0):
            recs.append(
                "ℹ️ No significant surface cracks detected in analyzed image. Note: Visual screening "
                "is limited to visible surface areas. A lack of detected surface cracks does not guarantee "
                "absence of subsurface, internal, or non-visible defects. Requires engineering review."
            )
            return recs

        # Measured evidence statements
        recs.append(f"Detected Surface Crack Coverage: {coverage_pct:.3f}% of valid image area.")
        recs.append(f"Maximum Fracture Caliper: {max_fracture_px:.1f} px ({calibration_status}).")

        # Uncalibrated notice
        if px_to_mm is None or px_to_mm <= 0:
            recs.append(
                "⚠️ Calibration unavailable: Crack width is reported in pixels only. "
                "Physical code-limit compliance (e.g., ACI 224R / IS 456) cannot be asserted without certified optical scale calibration."
            )
        else:
            w_mm = max_fracture_px * px_to_mm
            recs.append(f"Estimated Physical Width: {w_mm:.2f} mm (based on optical calibration {px_to_mm:.4f} mm/px).")

        # Qualified actions based on severity
        if severity_index >= 80.0:
            recs.append(
                "🚨 CRITICAL SEVERITY: Displaced or extensive fracture network detected. "
                "Recommend immediate on-site safety inspection by a licensed structural engineer and traffic/load restriction consideration."
            )
        elif severity_index >= 65.0:
            recs.append(
                "⚠️ HIGH SEVERITY: Significant fracture progression observed. "
                "Schedule priority engineering review and non-destructive testing (NDT) within 30 days."
            )
        elif severity_index >= 40.0:
            recs.append("Repair and maintenance review recommended within 90 days to prevent moisture/chemical ingress.")
        else:
            recs.append("Routine maintenance and annual visual monitoring recommended.")

        return recs

    # ── visualisation ─────────────────────────

    @staticmethod
    def draw_annotations(img, detections, seg_masks, health_score,
                         risk_level, risk_color, recommendations):
        annotated = img.copy()
        h, w = annotated.shape[:2]

        # Segmentation overlay
        if seg_masks:
            overlay = annotated.copy()
            for mask in seg_masks:
                if mask is not None:
                    coloured = np.zeros_like(annotated)
                    coloured[mask > 0] = risk_color
                    cv2.addWeighted(overlay, 0.7, coloured, 0.3, 0, overlay)
            annotated = overlay

        # Dynamic resolution-aware scale calibration
        diag = float(np.sqrt(h**2 + w**2))
        font_scale = max(0.55, diag / 1350.0)
        font_thickness = max(1, int(round(font_scale * 1.8)))
        box_thickness = max(2, int(round(diag / 420.0)))

        # Bounding boxes + high-contrast labels
        for det in detections:
            x1, y1, x2, y2 = map(int, det.bbox)
            # Clip coordinates to image boundary
            x1, y1 = max(0, min(w - 1, x1)), max(0, min(h - 1, y1))
            x2, y2 = max(0, min(w - 1, x2)), max(0, min(h - 1, y2))

            # 1. Dark outer border around box for 100% contrast on any background
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (18, 18, 22), box_thickness + 2)
            # 2. Primary bounding box in risk color
            cv2.rectangle(annotated, (x1, y1), (x2, y2), risk_color, box_thickness)

            # ASCII label (OpenCV FONT_HERSHEY_SIMPLEX does not support unicode bullet)
            label = f"{det.crack_type.capitalize()} | {det.confidence:.0%}"
            (lw, lh), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness)

            pad_x = max(6, int(10 * font_scale))
            pad_y = max(4, int(7 * font_scale))
            badge_w = lw + 2 * pad_x
            badge_h = lh + baseline + 2 * pad_y

            # Position badge outside bounding box so crack interior remains unobstructed
            if y1 - badge_h - 4 >= 0:
                # 1. Prefer placing ABOVE bounding box
                by2 = y1 - 4
                by1 = by2 - badge_h
            elif y2 + badge_h + 4 <= h:
                # 2. If at top edge, place BELOW bounding box
                by1 = y2 + 4
                by2 = by1 + badge_h
            else:
                # 3. Fallback: inside top of box
                by1 = y1 + 4
                by2 = by1 + badge_h

            bx1 = max(0, min(x1, w - badge_w))
            bx2 = min(w, bx1 + badge_w)

            # Luminance check for text contrast:
            lum = 0.114 * risk_color[0] + 0.587 * risk_color[1] + 0.299 * risk_color[2]
            text_color = (12, 12, 14) if lum > 130 else (255, 255, 255)

            border_w = max(1, int(round(font_scale * 0.8)))
            # Dark outer pill border
            cv2.rectangle(annotated, (bx1 - border_w, by1 - border_w), (bx2 + border_w, by2 + border_w), (18, 18, 22), -1)
            # Solid pill background in risk color
            cv2.rectangle(annotated, (bx1, by1), (bx2, by2), risk_color, -1)
            # High-visibility text with anti-aliasing
            cv2.putText(
                annotated,
                label,
                (bx1 + pad_x, by2 - pad_y - max(1, baseline // 2)),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                text_color,
                font_thickness,
                cv2.LINE_AA,
            )

        return annotated

    # ── MAIN ANALYSIS ─────────────────────────

    def analyze(self, image_path: str, structure_type: str = "building", 
                age_years: int = 10, is_seismic: bool = False, 
                is_near_sea: bool = False, is_heavy_traffic: bool = False,
                material_type: str = "concrete",
                px_to_mm: Optional[float] = None) -> InspectionResult:
        """
        Unified multi-model analysis integrating U-Net segmentation,
        deduplicated YOLO detection, and consistent Structural Severity Index (SSI).
        """
        img = cv2.imread(image_path)
        if img is None: raise ValueError(f"Could not load image: {image_path}")

        img_h, img_w = img.shape[:2]
        img_area = img_h * img_w

        # ── 1. U-Net SEGMENTATION (Primary pixel-level mask) ────────
        unet_mask         = None
        unet_overlay_img  = None
        unet_crack_area   = None

        if ENABLE_UNET and UNET_AVAILABLE:
            try:
                unet_mask = run_unet_inference(img)
                if unet_mask is not None:
                    unet_crack_px = int(np.count_nonzero(unet_mask))
                    unet_crack_area = round((unet_crack_px / img_area) * 100.0, 4)
                    unet_overlay_img = overlay_unet_mask(img, unet_mask)
            except Exception as unet_exc:
                logger.error("U-Net inference failed: %s", unet_exc, exc_info=True)

        # ── 2. YOLO DETECTION & ENHANCED MULTI-PASS ─────────────────
        imgsz = 1024 if max(img_h, img_w) >= 800 else 640
        det_results = self.det_model(img, imgsz=imgsz, conf=self.conf_threshold, verbose=False)
        boxes = det_results[0].boxes
        raw_boxes = []
        raw_confs = []
        if boxes is not None and len(boxes) > 0:
            for box in boxes:
                raw_boxes.append(box.xyxy[0].cpu().numpy().tolist())
                raw_confs.append(float(box.conf[0]))

        # Adaptive contrast pass (CLAHE) for low-contrast/dark/shadowed/wet crack conditions
        # (e.g. wet asphalt potholes, shadowed bridge pier rebar spalling)
        if len(raw_boxes) <= 1:
            try:
                lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                lab[:, :, 0] = clahe.apply(lab[:, :, 0])
                enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
                det_results_enh = self.det_model(enhanced, imgsz=imgsz, conf=self.conf_threshold, verbose=False)
                enh_boxes = det_results_enh[0].boxes
                if enh_boxes is not None and len(enh_boxes) > 0:
                    for box in enh_boxes:
                        raw_boxes.append(box.xyxy[0].cpu().numpy().tolist())
                        raw_confs.append(float(box.conf[0]))
            except Exception as e:
                logger.warning(f"Contrast-enhanced pass skipped: {e}")

        # Apply Non-Maximum Suppression to avoid duplicate boxes around same crack
        keep_indices = apply_nms(raw_boxes, raw_confs, score_thresh=self.conf_threshold, nms_thresh=0.45)

        # ── 3. UNIFIED CRACK MASK & MORPHOLOGICAL FALLBACK ────────
        # If U-Net mask is available, it is the primary mask for both measurements and overlay.
        # If U-Net is unavailable, extract true crack channels inside detected regions without surface texture noise.
        if unet_mask is not None:
            final_mask = unet_mask
        else:
            fallback_mask = np.zeros((img_h, img_w), dtype=np.uint8)
            for idx in keep_indices:
                x1, y1, x2, y2 = map(int, raw_boxes[idx])
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(img_w, x2), min(img_h, y2)
                crop = img[y1:y2, x1:x2]
                if crop.size > 0:
                    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                    blurred = cv2.GaussianBlur(gray, (5, 5), 1.5)
                    # Adaptive valley thresholding to isolate dark crack channels without background pebbles
                    inv = 255 - blurred
                    _, bin_crack = cv2.threshold(inv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    # Filter out small noise speckles (only keep connected contours with significant size)
                    num_l, lbls, stats_c, _ = cv2.connectedComponentsWithStats(bin_crack)
                    clean_crop = np.zeros_like(bin_crack)
                    min_contour_area = max(20, int(0.005 * crop.shape[0] * crop.shape[1]))
                    for li in range(1, num_l):
                        if stats_c[li, cv2.CC_STAT_AREA] >= min_contour_area:
                            clean_crop[lbls == li] = 255
                    fallback_mask[y1:y2, x1:x2] = cv2.bitwise_or(fallback_mask[y1:y2, x1:x2], clean_crop)
            final_mask = fallback_mask

        # ── 4. DERIVED MEASUREMENTS (Single source of truth) ───────
        crack_pixels = int(np.count_nonzero(final_mask))
        total_crack_area_pct = round((crack_pixels / img_area) * 100.0, 4)
        max_fracture_px = compute_max_fracture_width_px(final_mask)

        # Build CrackDetection list from deduplicated boxes
        detections = []
        full_edge_map = np.zeros((img_h, img_w), dtype=np.uint8)

        for idx in keep_indices:
            x1, y1, x2, y2 = map(int, raw_boxes[idx])
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(img_w, x2), min(img_h, y2)

            box_area_px, box_w_px, edges = self.estimate_crack_metrics(img, [x1, y1, x2, y2], mask=final_mask)

            if edges is not None:
                full_edge_map[y1:y2, x1:x2] = cv2.bitwise_or(full_edge_map[y1:y2, x1:x2], edges)

            detections.append(CrackDetection(
                bbox=[float(x1), float(y1), float(x2), float(y2)],
                confidence=raw_confs[idx],
                crack_type=self.classify_crack_type([x1, y1, x2, y2], img.shape),
                area_pixels=int(box_area_px or 1),
                area_percentage=round(((box_area_px or 1) / img_area) * 100.0, 4),
                width_pixels=round(box_w_px, 1),
                length_pixels=round(float(max(x2 - x1, y2 - y1)), 1),
            ))

        # 1:1 anomaly count: exactly equals the number of distinct detected crack instances
        anomaly_count = len(detections)
        if anomaly_count == 0 and unet_mask is not None and np.count_nonzero(unet_mask) > 0:
            anomaly_count = count_distinct_crack_regions(unet_mask, min_area_px=50)

        # ── 5. CALIBRATION & WIDTH UNIT ───────────────────────────
        if px_to_mm is not None and px_to_mm > 0:
            max_crack_width_mm = round(max_fracture_px * px_to_mm, 2)
            calibration_status = f"Calibrated ({px_to_mm:.4f} mm/px)"
        else:
            max_crack_width_mm = None
            calibration_status = "Uncalibrated — pixels only"

        # ── 5b. AUTOMATIC SURFACE MATERIAL CLASSIFICATION ─────────────────────
        mat_result = classify_surface_material(img)
        material_ai = mat_result.get("material", "unknown")
        material_ai_label = mat_result.get("label", "Unknown / Uncertain")
        material_ai_conf = mat_result.get("confidence", 0.0)

        # Check if user explicitly provided a manual override
        user_override = bool(
            material_type
            and material_type.lower() not in ("auto", "none", "", "unknown_auto")
        )

        if user_override:
            display_material = material_type
            material_source = "User override"
            # Explicit user override controls structural scoring material weighting
            scoring_material = material_type
        else:
            # Auto-detect mode: display the AI-predicted surface material
            display_material = material_ai
            material_source = mat_result.get("source", "AI prediction")
            # SAFETY RULE: Do not use unvalidated AI material prediction to alter structural integrity / SSI.
            # Default to neutral baseline multiplier (1.00).
            scoring_material = "unknown"

        # ── 6. CONSISTENT SCORING ─────────────────────────────────
        img_diagonal_px = float(np.sqrt(img_h ** 2 + img_w ** 2))
        health_score = self.calculate_health_score(
            coverage_pct=total_crack_area_pct,
            max_fracture_px=max_fracture_px,
            anomaly_count=anomaly_count,
            structure_type=structure_type,
            material_type=scoring_material,
            detections=detections,
            img_diagonal_px=img_diagonal_px,
        )
        base_damage_penalty = round(max(0.0, 100.0 - health_score), 2)

        severity_index = self.calculate_severity_index(
            health_score=health_score,
            coverage_pct=total_crack_area_pct,
            max_fracture_px=max_fracture_px,
            anomaly_count=anomaly_count,
            age_years=age_years,
            is_seismic=is_seismic,
            is_near_sea=is_near_sea,
            is_heavy_traffic=is_heavy_traffic,
            structure_type=structure_type,
            material_type=scoring_material,
        )

        # Harmonize effective Structural Integrity (SI) with Severity Index (SSI)
        health_score = round(max(0.0, min(100.0, 100.0 - severity_index)), 1)
        risk_level, risk_color, _ = self.get_risk_level(severity_index, coverage_pct=total_crack_area_pct)

        recommendations = self.get_recommendations(
            detections=detections,
            health_score=health_score,
            severity_index=severity_index,
            structure_type=structure_type,
            age_years=age_years,
            is_seismic=is_seismic,
            is_near_sea=is_near_sea,
            is_heavy_traffic=is_heavy_traffic,
            coverage_pct=total_crack_area_pct,
            max_fracture_px=max_fracture_px,
            calibration_status=calibration_status,
            px_to_mm=px_to_mm,
        )

        # ── 7. AGREEMENT METRIC ───────────────────────────────────
        model_agreement   = None
        agreement_iou_val = None
        agreement_note    = None
        if unet_mask is not None:
            yolo_boxes = [d.bbox for d in detections]
            agr = compute_agreement(unet_mask, yolo_boxes, img.shape)
            model_agreement   = agr["agreement"]
            agreement_iou_val = agr["agreement_iou"]
            agreement_note    = agr["note"]

        # ── 8. VISUALIZATION ARTIFACTS ────────────────────────────
        # Blueprint HUD
        blueprint = np.zeros((img_h, img_w, 3), dtype=np.uint8)
        blueprint[:] = (30, 20, 15)
        grid_spacing = int(min(img_h, img_w) * 0.1)
        for x in range(0, img_w, grid_spacing):
            cv2.line(blueprint, (x, 0), (x, img_h), (50, 40, 30), 1)
        for y in range(0, img_h, grid_spacing):
            cv2.line(blueprint, (0, y), (img_w, y), (50, 40, 30), 1)

        edge_mask = (final_mask > 0) if np.sum(final_mask) > 0 else (full_edge_map > 0)
        blueprint[edge_mask] = (255, 255, 0) # High-visibility Cyan in BGR

        if detections:
            worst = max(detections, key=lambda d: d.width_pixels)
            wx1, wy1, wx2, wy2 = map(int, worst.bbox)
            cv2.rectangle(blueprint, (wx1, wy1), (wx2, wy2), (0, 0, 255), max(1, int(img_h/300)))
            cv2.line(blueprint, (wx1, wy1), (wx2, wy2), (0, 255, 0), 1, cv2.LINE_AA)
            cv2.putText(blueprint, "STRUCTURAL VECTOR", (wx1 + 5, int((wy1 + wy2)/2)), 
                        cv2.FONT_HERSHEY_PLAIN, max(1.0, img_h/600), (0, 255, 0), 1)
            cv2.putText(blueprint, f"MAX CALIPER: {max_fracture_px}px | {worst.crack_type.upper()}", 
                        (wx1, max(15, wy1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, max(0.4, img_h/1000.0), (0, 0, 255), 1)

        # Clean crack overlay (without bounding boxes or badges)
        if unet_overlay_img is not None:
            clean_crack_overlay = unet_overlay_img
        else:
            clean_crack_overlay = img.copy()
            if np.count_nonzero(final_mask) > 0:
                coloured_mask = np.zeros_like(img)
                kernel_size = max(1, int(round(img_diagonal_px / 1400.0)))
                dilated_mask = cv2.dilate(final_mask, np.ones((kernel_size, kernel_size), np.uint8), iterations=1)
                coloured_mask[dilated_mask > 0] = risk_color
                cv2.addWeighted(coloured_mask, 0.45, clean_crack_overlay, 0.55, 0, clean_crack_overlay)

        # Views
        yolo_only_img = self.draw_annotations(
            img, detections, [], health_score, risk_level, risk_color, recommendations
        )
        combined = self.draw_annotations(
            clean_crack_overlay, detections, [], health_score, risk_level, risk_color, recommendations
        )

        depth_map_data = self.generate_3d_depth_map(img, detections)
        lat, lng, g_status = self.extract_gps(image_path)

        return InspectionResult(
            image_path=image_path,
            structure_type=structure_type,
            detections=detections,
            total_crack_area_pct=total_crack_area_pct,
            max_crack_width=max_fracture_px,
            crack_density=float(anomaly_count),
            health_score=health_score,
            severity_index=severity_index,
            risk_level=risk_level,
            risk_color=risk_color,
            recommendations=recommendations,
            annotated_image=combined,
            edge_detected_image=blueprint,
            depth_map_data=depth_map_data,
            latitude=lat,
            longitude=lng,
            gps_status=g_status,
            unet_mask=unet_mask,
            unet_overlay_image=clean_crack_overlay,
            yolo_only_image=yolo_only_img,
            unet_crack_area_pct=unet_crack_area if unet_crack_area is not None else total_crack_area_pct,
            model_agreement=model_agreement,
            agreement_iou=agreement_iou_val,
            agreement_note=agreement_note,
            material_type=display_material,
            material_ai=material_ai,
            material_ai_label=material_ai_label,
            material_ai_confidence=material_ai_conf,
            material_source=material_source,
            calibration_status=calibration_status,
            crack_width_unit="px",
            max_crack_width_mm=max_crack_width_mm,
            base_damage_penalty=base_damage_penalty,
        )

    # ── batch ─────────────────────────────────

    def analyze_batch(self, image_dir: str, structure_type: str = "building"):
        results = []
        files = list(Path(image_dir).glob("*.jpg")) + list(Path(image_dir).glob("*.png"))

        for img_path in files:
            print(f"  Analyzing: {img_path.name}")
            result = self.analyze(str(img_path), structure_type)
            results.append(result)

            out_path = str(img_path).replace("raw", "annotated")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            cv2.imwrite(out_path, result.annotated_image)

        return results


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

if __name__ == "__main__":
    analyzer = CrackAnalyzer()

    test_image = "data/raw/test_crack.jpg"
    if not os.path.exists(test_image):
        print(f"[SKIP] Test image not found: {test_image}")
        print("  Place a crack image at that path and re-run.")
        raise SystemExit(0)

    result = analyzer.analyze(test_image, structure_type="building")

    print("\n=== INSPECTION REPORT ===")
    print(f"  Structure    : {result.structure_type}")
    print(f"  Cracks found : {len(result.detections)}")
    print(f"  Crack area   : {result.total_crack_area_pct:.2f} %")
    print(f"  Max width    : {result.max_crack_width:.1f} px")
    print(f"  Health score : {result.health_score} / 100")
    print(f"  Risk level   : {result.risk_level}")
    print("\n  Recommendations:")
    for r in result.recommendations:
        print(f"    • {r}")

    cv2.imwrite("output_annotated.jpg", result.annotated_image)
    print("\n  Annotated image → output_annotated.jpg")
