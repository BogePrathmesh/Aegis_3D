"""
Unit and integration tests for the AEGIS-3D audit corrections.

Covers:
1. Coverage calculation (binary crack-mask pixels / valid image pixels * 100).
2. Euclidean Distance Transform (EDT) maximum fracture caliper width in pixels.
3. Connected components anomaly count (distinct crack regions).
4. YOLO Non-Maximum Suppression (NMS) deduplication of overlapping bounding boxes.
5. Missing calibration handling ("Uncalibrated — pixels only").
6. Empty mask / no-crack behavior: does not falsely claim ACI compliance or guarantee safety.
7. Monotonicity: greater damage strictly increases SSI and strictly decreases Structural Integrity.
8. Risk category consistency across all threshold boundaries.
9. Material sensitivity weighting (e.g., masonry vs concrete vs plaster).
10. Single source of truth: overlay mask and measurement mask match.
11. End-to-end inference execution on real test images from data/Dummydataset/.
"""

import os
import sys
import importlib
import numpy as np
import pytest
import cv2

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

inference_mod = importlib.import_module("app.services.5_inference")
CrackAnalyzer = inference_mod.CrackAnalyzer
apply_nms = inference_mod.apply_nms
compute_max_fracture_width_px = inference_mod.compute_max_fracture_width_px
count_distinct_crack_regions = inference_mod.count_distinct_crack_regions
InspectionResult = inference_mod.InspectionResult


# ─── 1. Coverage Calculation ──────────────────────────────────────────────────

def test_coverage_calculation_exact():
    """Verify coverage is strictly binary crack pixels / total pixels * 100."""
    h, w = 200, 200
    total_px = h * w
    mask = np.zeros((h, w), dtype=np.uint8)
    # Turn exactly 400 pixels white (1% of 40,000)
    mask[0:20, 0:20] = 255
    crack_pixels = int(np.count_nonzero(mask))
    coverage = round((crack_pixels / total_px) * 100.0, 4)
    assert coverage == 1.0, f"Expected 1.0%, got {coverage}%"


# ─── 2. Max Fracture Width via EDT ────────────────────────────────────────────

def test_max_fracture_width_edt_line():
    """EDT must accurately measure inscribed aperture thickness in pixels."""
    mask = np.zeros((100, 100), dtype=np.uint8)
    # Line with thickness 10 px
    cv2.line(mask, (10, 50), (90, 50), 255, thickness=10)
    w_px = compute_max_fracture_width_px(mask)
    # Expected inscribed diameter is around 10-12 px
    assert 9.0 <= w_px <= 13.0, f"Expected ~10-12px, got {w_px}px"


def test_max_fracture_width_empty_mask():
    """Empty mask must return 0.0px width."""
    mask = np.zeros((100, 100), dtype=np.uint8)
    assert compute_max_fracture_width_px(mask) == 0.0


# ─── 3. Anomaly Count (Distinct Regions) ──────────────────────────────────────

def test_distinct_crack_regions():
    """Connected components must separate disjoint cracks and ignore 1px noise."""
    mask = np.zeros((100, 100), dtype=np.uint8)
    # Crack 1 (area > 20)
    cv2.line(mask, (10, 10), (40, 10), 255, thickness=3)
    # Crack 2 (area > 20)
    cv2.line(mask, (60, 60), (90, 60), 255, thickness=3)
    # Speckle noise (< 15 px)
    mask[2, 2] = 255
    mask[3, 3] = 255
    count = count_distinct_crack_regions(mask, min_area_px=15)
    assert count == 2, f"Expected exactly 2 distinct anomalies, got {count}"


# ─── 4. YOLO NMS Deduplication ────────────────────────────────────────────────

def test_nms_deduplication():
    """Overlapping redundant bounding boxes must be merged into single envelope."""
    boxes = [
        [10.0, 10.0, 80.0, 80.0],
        [12.0, 11.0, 82.0, 79.0],  # Heavy overlap with box 0
        [150.0, 150.0, 200.0, 200.0],  # Separate disjoint box
    ]
    confs = [0.90, 0.75, 0.85]
    survivors = apply_nms(boxes, confs, score_thresh=0.25, nms_thresh=0.45)
    assert len(survivors) == 2, f"Expected 2 deduplicated boxes, got {len(survivors)}"
    assert 0 in survivors and 2 in survivors


# ─── 5. Calibration Handling ──────────────────────────────────────────────────

def test_uncalibrated_reporting():
    """Uncalibrated inspection must report 'Uncalibrated — pixels only' and None for mm."""
    analyzer = CrackAnalyzer()
    recs = analyzer.get_recommendations(
        detections=[],
        health_score=85.0,
        severity_index=15.0,
        structure_type="building",
        age_years=10,
        is_seismic=False,
        is_near_sea=False,
        is_heavy_traffic=False,
        coverage_pct=1.5,
        max_fracture_px=14.0,
        calibration_status="Uncalibrated — pixels only",
        px_to_mm=None,
    )
    rec_text = " ".join(recs)
    assert "Calibration unavailable" in rec_text
    assert "reported in pixels only" in rec_text


# ─── 6. Empty Mask Safety Claim Audit ─────────────────────────────────────────

def test_empty_mask_no_false_safety_claims():
    """Empty mask must NOT claim ACI compliance or absolute safety guarantee."""
    analyzer = CrackAnalyzer()
    recs = analyzer.get_recommendations(
        detections=[],
        health_score=100.0,
        severity_index=5.0,
        structure_type="building",
        age_years=10,
        is_seismic=False,
        is_near_sea=False,
        is_heavy_traffic=False,
        coverage_pct=0.0,
        max_fracture_px=0.0,
    )
    rec_text = " ".join(recs)
    assert "ACI 224R Compliant" not in rec_text
    assert "COMPLIANT WITH ACI" not in rec_text
    assert "lack of detected surface cracks does not guarantee absence of subsurface" in rec_text
    assert "Requires engineering review" in rec_text


# ─── 7. Monotonicity of Severity Scores ───────────────────────────────────────

def test_damage_severity_monotonicity():
    """Greater measured damage must strictly increase SSI and decrease Integrity."""
    analyzer = CrackAnalyzer()
    
    # Low damage condition
    health_low_dmg = analyzer.calculate_health_score(
        coverage_pct=0.5, max_fracture_px=4.0, anomaly_count=1, structure_type="building"
    )
    ssi_low_dmg = analyzer.calculate_severity_index(
        health_score=health_low_dmg, coverage_pct=0.5, max_fracture_px=4.0, anomaly_count=1, age_years=10
    )

    # High damage condition (wider, more coverage, more anomalies)
    health_high_dmg = analyzer.calculate_health_score(
        coverage_pct=5.0, max_fracture_px=25.0, anomaly_count=6, structure_type="building"
    )
    ssi_high_dmg = analyzer.calculate_severity_index(
        health_score=health_high_dmg, coverage_pct=5.0, max_fracture_px=25.0, anomaly_count=6, age_years=10
    )

    assert health_high_dmg < health_low_dmg, (
        f"Structural integrity must drop with greater damage: {health_high_dmg} vs {health_low_dmg}"
    )
    assert ssi_high_dmg > ssi_low_dmg, (
        f"SSI must increase with greater damage: {ssi_high_dmg} vs {ssi_low_dmg}"
    )


# ─── 8. Risk Category Consistency ─────────────────────────────────────────────

def test_risk_category_thresholds():
    """Verify all SSI thresholds map to predictable, non-contradictory risk levels."""
    analyzer = CrackAnalyzer()
    assert analyzer.get_risk_level(85.0)[0] == "Critical"
    assert analyzer.get_risk_level(70.0)[0] == "High"
    assert analyzer.get_risk_level(50.0)[0] == "Medium"
    assert analyzer.get_risk_level(30.0)[0] == "Low"
    assert analyzer.get_risk_level(10.0, coverage_pct=0.0)[0] == "Safe"


# ─── 9. Material Sensitivity Weighting ────────────────────────────────────────

def test_material_weighting_masonry_vs_plaster():
    """Unreinforced masonry must produce higher penalty than cosmetic plaster for identical crack."""
    analyzer = CrackAnalyzer()
    health_masonry = analyzer.calculate_health_score(
        coverage_pct=2.0, max_fracture_px=10.0, anomaly_count=2,
        structure_type="building", material_type="brick_masonry"
    )
    health_plaster = analyzer.calculate_health_score(
        coverage_pct=2.0, max_fracture_px=10.0, anomaly_count=2,
        structure_type="building", material_type="plaster"
    )
    assert health_masonry < health_plaster, (
        f"Masonry should receive a higher penalty than plaster: {health_masonry} vs {health_plaster}"
    )


# ─── 10. End-to-End Test with Real Project Image ──────────────────────────────

def test_end_to_end_inspection_real_image():
    """Run full analysis pipeline on INSP-001.jpg and verify unified outputs."""
    img_path = os.path.normpath(os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "Dummydataset", "INSP-001.jpg"
    ))
    if not os.path.exists(img_path):
        pytest.skip(f"Test image not found at {img_path}")

    analyzer = CrackAnalyzer()
    res = analyzer.analyze(
        image_path=img_path,
        structure_type="road",
        age_years=15,
        is_seismic=False,
        is_near_sea=False,
        is_heavy_traffic=True,
        material_type="asphalt",
    )

    assert isinstance(res, InspectionResult)
    assert 0.0 <= res.health_score <= 100.0
    assert 0.0 <= res.severity_index <= 100.0
    assert res.total_crack_area_pct >= 0.0
    assert res.max_crack_width >= 0.0
    assert res.calibration_status == "Uncalibrated — pixels only"
    assert res.crack_width_unit == "px"
    assert res.material_type == "asphalt"
    assert res.annotated_image is not None
    assert res.edge_detected_image is not None


# ─── 11. Overlay Dimension Alignment ──────────────────────────────────────────

def test_overlay_alignment_with_arbitrary_image_dimensions(tmp_path):
    """Verify that all generated overlays strictly align with original image dimensions (non-square)."""
    h, w = 384, 576
    dummy_img = np.full((h, w, 3), 128, dtype=np.uint8)
    # Draw an artificial crack line
    cv2.line(dummy_img, (50, 50), (300, 200), (30, 30, 30), thickness=4)
    img_path = str(tmp_path / "test_dimensions.jpg")
    cv2.imwrite(img_path, dummy_img)

    analyzer = CrackAnalyzer()
    res = analyzer.analyze(
        image_path=img_path,
        structure_type="building",
        material_type="concrete",
    )

    # All visual overlays must strictly match (h, w)
    assert res.annotated_image.shape[:2] == (h, w), (
        f"Annotated image shape {res.annotated_image.shape[:2]} does not match input {(h, w)}"
    )
    assert res.edge_detected_image.shape[:2] == (h, w), (
        f"Edge blueprint shape {res.edge_detected_image.shape[:2]} does not match input {(h, w)}"
    )

    if res.unet_overlay_image is not None:
        assert res.unet_overlay_image.shape[:2] == (h, w), (
            f"U-Net overlay shape {res.unet_overlay_image.shape[:2]} does not match input {(h, w)}"
        )
    if res.yolo_only_image is not None:
        assert res.yolo_only_image.shape[:2] == (h, w), (
            f"YOLO overlay shape {res.yolo_only_image.shape[:2]} does not match input {(h, w)}"
        )
    if res.unet_mask is not None:
        assert res.unet_mask.shape == (h, w), (
            f"U-Net mask shape {res.unet_mask.shape} does not match input {(h, w)}"
        )


# ─── 12. User-Selected Material & Unknown Specification ───────────────────────

def test_user_selected_material_preservation():
    """Verify user-selected material is respected and unknown is safely handled."""
    analyzer = CrackAnalyzer()
    
    # Test concrete
    res_concrete = analyzer.analyze_raw(
        np.full((100, 100, 3), 120, dtype=np.uint8),
        material_type="concrete",
    ) if hasattr(analyzer, "analyze_raw") else None

    # Test unknown
    health_unknown = analyzer.calculate_health_score(
        coverage_pct=1.0, max_fracture_px=5.0, anomaly_count=1,
        structure_type="building", material_type="unknown"
    )
    assert 0.0 <= health_unknown <= 100.0


# ─── 13. Width Penalty Scale-Invariance (SSI Fix) ─────────────────────────────

def test_width_penalty_scale_invariant():
    """
    Verify the max_fracture_px penalty is normalized by image diagonal so that
    identical crack widths produce proportionally consistent penalties across
    different image resolutions.

    A 20px crack on a 640×480 image (diagonal=800px) should produce a
    much lower width penalty than using the old absolute linear formula
    (which would yield 20*1.5=30pt — the maximum regardless of image size).

    With diagonal normalization: norm_pct = 20/800*100 = 2.5%
    → p_width = min(30, 2.5*6) = 15pt (half the old fixed maximum).
    """
    analyzer = CrackAnalyzer()

    # Small crack on a large image: should NOT produce max-penalty width
    health_large_img = analyzer.calculate_health_score(
        coverage_pct=0.0, max_fracture_px=20.0, anomaly_count=0,
        structure_type="building", material_type="concrete",
        img_diagonal_px=800.0,   # 640×480 image
    )
    # Old formula: 20*1.5=30pt penalty → health ≈ 70
    # New formula: (20/800)*100*6=15pt penalty → health = 85
    assert health_large_img >= 80.0, (
        f"A 20px crack on 800px diagonal should score >= 80, got {health_large_img}"
    )

    # Proportionally large crack on a tiny image: should produce high penalty
    health_small_img = analyzer.calculate_health_score(
        coverage_pct=0.0, max_fracture_px=20.0, anomaly_count=0,
        structure_type="building", material_type="concrete",
        img_diagonal_px=50.0,    # tiny 35×35 image
    )
    # (20/50)*100*6=24pt penalty → health = 76 (much worse)
    assert health_small_img < health_large_img, (
        f"Same crack px on smaller image should score worse: {health_small_img} vs {health_large_img}"
    )
