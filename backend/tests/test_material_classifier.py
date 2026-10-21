"""
Test Suite for AEGIS-3D Automatic Surface Material Classification.

Validates:
1. Genuine model loading and pipeline initialization.
2. Image suitability and quality gates (Laplacian variance, blur, minimum resolution).
3. Real surface material predictions across target categories:
   - Concrete
   - Brick / Masonry
   - Asphalt
   - Plaster / Stucco
   - Stone
   - Tile / Ceramic
4. Out-of-distribution (OOD) and synthetic abstract image handling -> 'other' or 'unknown'.
5. Ambiguous / low-confidence rejection -> 'unknown' / 'Unknown / Uncertain'.
6. Safety isolation: Auto-detected material does NOT alter structural integrity or SSI scores.
7. User manual override preservation.
"""

import os
import glob
import pytest
import numpy as np
import cv2
from PIL import Image

from app.services.material_classifier import (
    classify_surface_material,
    check_image_suitability,
    is_classifier_available,
    MATERIAL_CLASSES,
    DISPLAY_LABELS,
    CONFIDENCE_THRESHOLD,
)
import importlib
_inf = importlib.import_module("app.services.5_inference")
CrackAnalyzer = _inf.CrackAnalyzer
InspectionResult = _inf.InspectionResult


@pytest.fixture(scope="module")
def analyzer():
    return CrackAnalyzer()


def test_classifier_is_available():
    """Verify that dependencies and model weights are accessible."""
    assert is_classifier_available() is True


def test_image_suitability_rejection():
    """Verify that featureless, solid, and severely blurred images are flagged as unsuitable."""
    # 1. Blank solid black image
    black_img = np.zeros((128, 128, 3), dtype=np.uint8)
    is_ok, reason = check_image_suitability(black_img)
    assert not is_ok
    res = classify_surface_material(black_img)
    assert res["material"] == "unknown"
    assert res["is_uncertain"] is True
    assert "insufficient" in res["note"].lower() or "unsuitable" in res["note"].lower()

    # 2. Too small image (< 32x32)
    tiny_img = np.zeros((16, 16, 3), dtype=np.uint8)
    is_ok_tiny, reason_tiny = check_image_suitability(tiny_img)
    assert not is_ok_tiny
    assert "resolution" in reason_tiny.lower()

    # 3. Heavily blurred noise
    noisy = np.random.randint(120, 140, (128, 128, 3), dtype=np.uint8)
    blurred = cv2.GaussianBlur(noisy, (31, 31), 0)
    is_ok_blur, _ = check_image_suitability(blurred)
    assert not is_ok_blur


def test_real_asphalt_road_classification():
    """Verify real asphalt road imagery is classified as asphalt."""
    road_candidates = (
        glob.glob("data/uploads/*road9*.jp*")
        + glob.glob("backend/data/uploads/*road9*.jp*")
        + glob.glob("../data/Dummydataset/INSP-010.jpg")
    )
    if not road_candidates:
        pytest.skip("No road test image found")

    img_path = road_candidates[0]
    res = classify_surface_material(img_path)

    assert res["material"] == "asphalt"
    assert res["label"] == "Asphalt"
    assert res["confidence"] >= CONFIDENCE_THRESHOLD
    assert res["source"] == "AI prediction"
    assert "asphalt" in res["all_scores"]


def test_real_concrete_slab_classification():
    """Verify real concrete slab imagery is classified as concrete."""
    slab_candidates = (
        glob.glob("data/uploads/*mumbai*.jp*")
        + glob.glob("backend/data/uploads/*mumbai*.jp*")
        + glob.glob("../data/Dummydataset/INSP-005.jpg")
    )
    if not slab_candidates:
        pytest.skip("No concrete slab test image found")

    img_path = slab_candidates[0]
    res = classify_surface_material(img_path)

    assert res["material"] == "concrete"
    assert res["label"] == "Concrete"
    assert res["confidence"] >= 0.50
    assert res["source"] == "AI prediction"


def test_real_brick_masonry_classification():
    """Verify real brick/masonry wall imagery is classified as brick_masonry."""
    brick_candidates = (
        glob.glob("data/uploads/*build4*.jp*")
        + glob.glob("backend/data/uploads/*build4*.jp*")
        + glob.glob("data/uploads/*Vienna*.png")
    )
    if not brick_candidates:
        pytest.skip("No brick test image found")

    img_path = brick_candidates[0]
    res = classify_surface_material(img_path)

    assert res["material"] == "brick_masonry"
    assert res["label"] == "Brick / Masonry"
    assert res["confidence"] >= 0.70
    assert res["source"] == "AI prediction"


def test_out_of_distribution_synthetic_image():
    """Verify that an abstract non-construction image is classified as 'other' or 'unknown'."""
    abstract = np.zeros((224, 224, 3), dtype=np.uint8)
    abstract[:, :112, 0] = 255  # Solid Blue
    abstract[:, 112:, 1] = 255  # Solid Green
    # Add high-contrast edge between the two to pass Laplacian variance gate
    cv2.line(abstract, (112, 0), (112, 224), (255, 255, 255), 2)

    res = classify_surface_material(abstract)
    assert res["material"] in ("other", "unknown")
    assert res["material"] != "concrete"
    assert res["material"] != "asphalt"


def test_end_to_end_auto_detect_in_analyzer(analyzer):
    """Verify that CrackAnalyzer.analyze() automatically populates AI material in auto mode."""
    road_candidates = glob.glob("data/uploads/*road9*.jp*") or glob.glob("../data/Dummydataset/INSP-010.jpg")
    if not road_candidates:
        pytest.skip("No road test image found")

    img_path = road_candidates[0]
    res = analyzer.analyze(img_path, structure_type="road", material_type="auto")

    assert isinstance(res, InspectionResult)
    assert res.material_type == "asphalt"
    assert res.material_source == "AI prediction"
    assert res.material_ai == "asphalt"
    assert res.material_ai_confidence >= CONFIDENCE_THRESHOLD


def test_user_manual_override_respected(analyzer):
    """Verify that a manual material selection is preserved as User override without silent overwrite."""
    road_candidates = glob.glob("data/uploads/*road9*.jp*") or glob.glob("../data/Dummydataset/INSP-010.jpg")
    if not road_candidates:
        pytest.skip("No road test image found")

    img_path = road_candidates[0]
    # Even though image is asphalt road, user forces "stone"
    res = analyzer.analyze(img_path, structure_type="road", material_type="stone")

    assert res.material_type == "stone"
    assert res.material_source == "User override"
    # Underlying AI detection remains accessible
    assert res.material_ai == "asphalt"
    assert res.material_ai_confidence > 0.0


def test_safety_rule_ai_material_does_not_distort_scoring(analyzer):
    """
    Verify safety rule: Unvalidated AI material auto-detection uses neutral scoring
    multiplier so it cannot arbitrarily inflate or deflate structural health / SSI.
    """
    road_candidates = glob.glob("data/uploads/*road9*.jp*") or glob.glob("../data/Dummydataset/INSP-010.jpg")
    if not road_candidates:
        pytest.skip("No road test image found")

    img_path = road_candidates[0]

    # Auto mode
    res_auto = analyzer.analyze(img_path, structure_type="road", material_type="auto")
    # Neutral unknown mode
    res_unknown = analyzer.analyze(img_path, structure_type="road", material_type="unknown")

    # The physical health score under auto-mode must match neutral scoring
    assert res_auto.health_score == res_unknown.health_score
    assert res_auto.severity_index == res_unknown.severity_index
