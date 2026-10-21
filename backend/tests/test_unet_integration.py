"""
Tests for the AEGIS U-Net integration.

Run from the backend/ directory:
    python -m pytest tests/test_unet_integration.py -v

Requirements:
    pip install pytest
    torch must be installed and deepcrack_unet_best.pth accessible.
"""

import os
import sys
import importlib
import numpy as np
import pytest

# Make sure the app package is on the path when running from backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

CHECKPOINT_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        "..", "..", "..",
        "deepcrack_unet", "deepcrack_unet_best.pth",
    )
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bgr(h=480, w=640):
    """Create a synthetic BGR image (random uint8)."""
    rng = np.random.default_rng(seed=0)
    return (rng.integers(0, 256, (h, w, 3), dtype=np.uint8))


# ---------------------------------------------------------------------------
# 1. Torch availability
# ---------------------------------------------------------------------------

def test_torch_importable():
    """torch must be importable (required for U-Net inference)."""
    import torch  # noqa: F401


# ---------------------------------------------------------------------------
# 2. Architecture instantiation
# ---------------------------------------------------------------------------

def test_unet_instantiation():
    """UNetBase24 can be instantiated without a checkpoint."""
    from app.services.unet_model import UNetBase24
    model = UNetBase24()
    assert model is not None


def test_unet_architecture_output_shape():
    """Forward pass on a batch-1 input (1,3,320,320) must produce (1,1,320,320)."""
    import torch
    from app.services.unet_model import UNetBase24
    model = UNetBase24().eval()
    dummy = torch.zeros(1, 3, 320, 320)
    with torch.no_grad():
        out = model(dummy)
    assert out.shape == (1, 1, 320, 320), f"Expected (1,1,320,320), got {out.shape}"
    # sigmoid output must be in [0, 1]
    assert float(out.min()) >= 0.0
    assert float(out.max()) <= 1.0


# ---------------------------------------------------------------------------
# 3. Checkpoint loading
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.path.exists(CHECKPOINT_PATH),
    reason="deepcrack_unet_best.pth not found — copy checkpoint first"
)
def test_checkpoint_keys():
    """Checkpoint must contain expected top-level keys."""
    import torch
    ckpt = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=False)
    assert isinstance(ckpt, dict), "Checkpoint must be a dict"
    for key in ("model", "epoch", "image_size", "architecture"):
        assert key in ckpt, f"Missing key: {key}"
    assert ckpt["architecture"] == "UNet-base24"
    assert ckpt["image_size"] == 320


@pytest.mark.skipif(
    not os.path.exists(CHECKPOINT_PATH),
    reason="deepcrack_unet_best.pth not found"
)
def test_model_loading_singleton():
    """get_unet_model() loads weights and returns non-None model on first and second call."""
    # Reset singleton first (in case a previous test loaded it)
    import app.services.unet_model as um
    um._model_singleton  = None
    um._device_singleton = None

    os.environ["UNET_WEIGHTS_PATH"] = CHECKPOINT_PATH
    model, device = um.get_unet_model()
    assert model is not None, "Model should load successfully"
    assert device is not None

    # Second call must return the same object (singleton)
    model2, _ = um.get_unet_model()
    assert model is model2, "get_unet_model() must return the same cached instance"


# ---------------------------------------------------------------------------
# 4. Preprocessing
# ---------------------------------------------------------------------------

def test_preprocess_output_shape():
    """_preprocess() must return a (1,3,320,320) float32 tensor."""
    import torch
    from app.services.unet_model import _preprocess, INPUT_SIZE
    img = _make_bgr(480, 640)
    t = _preprocess(img)
    assert t.shape == (1, 3, INPUT_SIZE, INPUT_SIZE), f"Unexpected shape: {t.shape}"
    assert t.dtype == torch.float32


def test_preprocess_normalisation():
    """After preprocessing a uniform white image the tensor values are approximately -2.1 to -1.8."""
    from app.services.unet_model import _preprocess, IMAGENET_MEAN, IMAGENET_STD
    white = np.ones((10, 10, 3), dtype=np.uint8) * 255
    t = _preprocess(white).squeeze().numpy()   # (3, 320, 320)
    # For a white pixel: (1.0 - mean) / std — should be well below 0 for all channels
    for c, (m, s) in enumerate(zip(IMAGENET_MEAN, IMAGENET_STD)):
        expected = round((1.0 - m) / s, 2)
        actual   = round(float(t[c].mean()), 2)
        assert abs(actual - expected) < 0.05, (
            f"Channel {c}: expected ~{expected}, got {actual}"
        )


# ---------------------------------------------------------------------------
# 5. Inference
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.path.exists(CHECKPOINT_PATH),
    reason="deepcrack_unet_best.pth not found"
)
def test_inference_output_shape_and_dtype():
    """run_unet_inference() must return a uint8 binary mask at the original image size."""
    import app.services.unet_model as um
    um._model_singleton  = None
    um._device_singleton = None
    os.environ["UNET_WEIGHTS_PATH"] = CHECKPOINT_PATH

    from app.services.unet_model import run_unet_inference
    img  = _make_bgr(480, 640)
    mask = run_unet_inference(img)

    assert mask is not None, "Inference should not fail"
    assert mask.shape == (480, 640), f"Expected (480, 640), got {mask.shape}"
    assert mask.dtype == np.uint8
    unique = set(np.unique(mask).tolist())
    assert unique.issubset({0, 255}), f"Mask must be binary (0/255), got values: {unique}"


def test_inference_returns_none_without_checkpoint(tmp_path):
    """run_unet_inference() must return None when the checkpoint file does not exist."""
    import app.services.unet_model as um
    um._model_singleton  = None
    um._device_singleton = None
    os.environ["UNET_WEIGHTS_PATH"] = str(tmp_path / "nonexistent.pth")

    from app.services.unet_model import run_unet_inference
    img    = _make_bgr(100, 100)
    result = run_unet_inference(img)
    assert result is None, "Should return None when checkpoint is missing"


# ---------------------------------------------------------------------------
# 6. Overlay helper
# ---------------------------------------------------------------------------

def test_overlay_unet_mask_preserves_shape():
    """overlay_unet_mask() must return a BGR image with the same shape as the input."""
    from app.services.unet_model import overlay_unet_mask
    img  = _make_bgr(480, 640)
    mask = np.zeros((480, 640), dtype=np.uint8)
    mask[100:200, 100:200] = 255          # white square

    overlay = overlay_unet_mask(img, mask)
    assert overlay.shape == img.shape
    assert overlay.dtype == np.uint8


# ---------------------------------------------------------------------------
# 7. Agreement metric
# ---------------------------------------------------------------------------

def test_agreement_full_overlap():
    """When U-Net mask == YOLO box region, agreement should be 'agree' with IoU ~1."""
    from app.services.unet_model import compute_agreement
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[10:50, 10:50] = 255
    boxes = [[10, 10, 50, 50]]
    result = compute_agreement(mask, boxes, (100, 100))
    assert result["agreement"] == "agree"
    assert result["agreement_iou"] >= 0.90


def test_agreement_no_overlap():
    """When U-Net mask and YOLO boxes do not overlap, agreement should be 'disagree'."""
    from app.services.unet_model import compute_agreement
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[70:90, 70:90] = 255             # bottom-right
    boxes = [[5, 5, 20, 20]]             # top-left
    result = compute_agreement(mask, boxes, (100, 100))
    assert result["agreement"] == "disagree"
    assert result["agreement_iou"] < 0.10


def test_agreement_empty_mask_no_boxes():
    """With no crack pixels and no boxes, IoU is 0 and agreement is 'disagree'."""
    from app.services.unet_model import compute_agreement
    mask  = np.zeros((100, 100), dtype=np.uint8)
    result = compute_agreement(mask, [], (100, 100))
    assert result["agreement_iou"] == 0.0
    assert "unet_crack_px" in result
    assert "yolo_box_px"   in result
    assert "note"          in result


def test_agreement_returns_required_keys():
    """compute_agreement() output must contain all documented keys."""
    from app.services.unet_model import compute_agreement
    mask = np.zeros((50, 50), dtype=np.uint8)
    result = compute_agreement(mask, [], (50, 50))
    for k in ("agreement", "agreement_iou", "unet_crack_px", "yolo_box_px", "note"):
        assert k in result, f"Missing key: {k}"


# ---------------------------------------------------------------------------
# 8. InspectionResult dataclass has new fields
# ---------------------------------------------------------------------------

def test_inspection_result_has_unet_fields():
    """InspectionResult must have the new U-Net optional fields (all defaulting to None)."""
    mod = importlib.import_module("app.services.5_inference")
    InspectionResult = mod.InspectionResult
    import dataclasses
    field_names = {f.name for f in dataclasses.fields(InspectionResult)}
    for expected in (
        "unet_mask",
        "unet_overlay_image",
        "yolo_only_image",
        "unet_crack_area_pct",
        "model_agreement",
        "agreement_iou",
        "agreement_note",
    ):
        assert expected in field_names, f"InspectionResult missing field: {expected}"

