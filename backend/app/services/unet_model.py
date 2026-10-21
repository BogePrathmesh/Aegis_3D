"""
U-Net segmentation model for pixel-level crack detection.

Architecture reconstructed from checkpoint keys in deepcrack_unet_best.pth:
  - Architecture tag  : UNet-base24
  - Input size        : 320 x 320
  - Normalisation     : ImageNet (mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225])
  - Encoder           : 4 double-conv blocks  (24 -> 48 -> 96 -> 192 channels)
  - Bottleneck        : 384-channel double-conv
  - Decoder           : 4 ConvTranspose2d upsamples + skip-concat + double-conv
  - Output            : 1x1 conv -> sigmoid -> binary mask

Checkpoint structure (dict):
  {
    'model'        : OrderedDict  (state_dict with e1, e2, ..., b, d4.., u4.., out keys)
    'epoch'        : int
    'best_val_dice': float
    'image_size'   : int   (320)
    'architecture' : str   ('UNet-base24')
    'normalization': str   ('ImageNet')
  }

Loading is done once at first call to get_unet_model() and cached as a module-level singleton.
Supports CUDA when available, falls back to CPU.

Limitations
-----------
* Trained on DeepCrack dataset (0.7174 Dice) and evaluated on 240 masonry image-mask pairs
  (Dice 0.6564, IoU 0.5326). Not validated on all structure types in AEGIS. Treat mask
  outputs as supporting evidence, not ground truth.
* Sigmoid threshold is 0.5 by default; override via UNET_THRESHOLD env var.
"""

import os
import logging
from typing import Optional, Tuple

import cv2
import numpy as np

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INPUT_SIZE    = 320
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD  = [0.229, 0.224, 0.225]

# Default checkpoint path; override via UNET_WEIGHTS_PATH env var
_DEFAULT_WEIGHTS = os.path.normpath(os.path.join(
    os.path.dirname(__file__),   # …/backend/app/services/
    "..", "..", "..",            # …/backend/ -> …/AEGIS - Final/
    "..",                        # …/Aegis_3D-Sattyam/
    "deepcrack_unet", "deepcrack_unet_best.pth"
))

_model_singleton  = None
_device_singleton = None


# ---------------------------------------------------------------------------
# Architecture
# ---------------------------------------------------------------------------

class _DoubleConv(nn.Module):
    """Two (Conv2d -> BN -> ReLU) blocks matching keys *.net.0/.1/.3/.4 in checkpoint."""

    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.net(x)


class UNetBase24(nn.Module):
    """
    U-Net with base width 24.  Attribute names match checkpoint state-dict keys exactly:
      e1, e2, e3, e4  - encoder blocks
      b               - bottleneck
      u4, u3, u2, u1  - ConvTranspose2d upsamples  (e.g. u4.weight shape (384,192,2,2))
      d4, d3, d2, d1  - decoder double-conv blocks
      out             - final 1x1 conv (out.weight shape (1,24,1,1))
    """

    def __init__(self):
        super().__init__()
        b = 24  # base channel width

        # Encoder
        self.e1 = _DoubleConv(3,      b)       # 24
        self.e2 = _DoubleConv(b,      b * 2)   # 48
        self.e3 = _DoubleConv(b * 2,  b * 4)   # 96
        self.e4 = _DoubleConv(b * 4,  b * 8)   # 192

        # Bottleneck
        self.b  = _DoubleConv(b * 8,  b * 16)  # 384

        # Decoder upsamples (ConvTranspose2d kernel 2x2, matches checkpoint shapes)
        self.u4 = nn.ConvTranspose2d(b * 16, b * 8, 2, stride=2)   # 384->192
        self.u3 = nn.ConvTranspose2d(b * 8,  b * 4, 2, stride=2)   # 192->96
        self.u2 = nn.ConvTranspose2d(b * 4,  b * 2, 2, stride=2)   # 96->48
        self.u1 = nn.ConvTranspose2d(b * 2,  b,     2, stride=2)   # 48->24

        # Decoder double-conv after skip-concat (in_ch doubled by concat)
        self.d4 = _DoubleConv(b * 16, b * 8)   # 384->192
        self.d3 = _DoubleConv(b * 8,  b * 4)   # 192->96
        self.d2 = _DoubleConv(b * 4,  b * 2)   # 96->48
        self.d1 = _DoubleConv(b * 2,  b)       # 48->24

        # Output
        self.out  = nn.Conv2d(b, 1, kernel_size=1)
        self.pool = nn.MaxPool2d(2)

    def forward(self, x):
        # Encode + save skip connections
        s1 = self.e1(x)
        s2 = self.e2(self.pool(s1))
        s3 = self.e3(self.pool(s2))
        s4 = self.e4(self.pool(s3))

        # Bottleneck
        bt = self.b(self.pool(s4))

        # Decode with skip connections
        x = self.d4(torch.cat([self.u4(bt), s4], dim=1))
        x = self.d3(torch.cat([self.u3(x),  s3], dim=1))
        x = self.d2(torch.cat([self.u2(x),  s2], dim=1))
        x = self.d1(torch.cat([self.u1(x),  s1], dim=1))

        return torch.sigmoid(self.out(x))


# ---------------------------------------------------------------------------
# Singleton loader
# ---------------------------------------------------------------------------

def get_unet_model():
    """
    Load and return (model, device).  Weights are loaded only once.

    Returns (None, None) if torch is unavailable or checkpoint missing.
    Call sites must handle None gracefully (fall back to OpenCV pipeline).
    """
    global _model_singleton, _device_singleton

    if _model_singleton is not None:
        return _model_singleton, _device_singleton

    if not TORCH_AVAILABLE:
        logger.warning("PyTorch not installed — U-Net segmentation disabled.")
        return None, None

    weights_path = os.path.normpath(
        os.environ.get("UNET_WEIGHTS_PATH", _DEFAULT_WEIGHTS)
    )

    if not os.path.exists(weights_path):
        logger.warning(
            "U-Net checkpoint not found at %s. "
            "Set env var UNET_WEIGHTS_PATH to the absolute path of deepcrack_unet_best.pth. "
            "U-Net segmentation will be disabled.",
            weights_path,
        )
        return None, None

    try:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info("Loading U-Net weights from %s on %s ...", weights_path, device)

        checkpoint = torch.load(weights_path, map_location=device, weights_only=False)

        if not isinstance(checkpoint, dict) or "model" not in checkpoint:
            raise ValueError(
                "Unexpected checkpoint format — expected dict with 'model' key, "
                "got: %s" % type(checkpoint)
            )

        arch = checkpoint.get("architecture", "unknown")
        if arch != "UNet-base24":
            logger.warning(
                "Checkpoint architecture tag is '%s'; loader expects 'UNet-base24'. "
                "Proceeding — mismatch will cause an error if weights do not fit.",
                arch,
            )

        model = UNetBase24()
        missing, unexpected = model.load_state_dict(checkpoint["model"], strict=True)

        if missing:
            raise RuntimeError("Missing keys in checkpoint: %s" % missing)
        if unexpected:
            raise RuntimeError("Unexpected keys in checkpoint: %s" % unexpected)

        model.to(device).eval()

        _model_singleton  = model
        _device_singleton = device

        logger.info(
            "U-Net loaded OK — epoch=%s  best_val_dice=%.4f  image_size=%s  device=%s",
            checkpoint.get("epoch"),
            checkpoint.get("best_val_dice", float("nan")),
            checkpoint.get("image_size"),
            device,
        )
        return model, device

    except Exception as exc:
        logger.error("Failed to load U-Net model: %s", exc, exc_info=True)
        return None, None


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------

def _preprocess(bgr_image: np.ndarray):
    """Preprocess BGR image for U-Net inference (resize, RGB, normalize, batch dim)."""
    resized = cv2.resize(bgr_image, (INPUT_SIZE, INPUT_SIZE), interpolation=cv2.INTER_LINEAR)
    rgb     = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0

    mean = np.array(IMAGENET_MEAN, dtype=np.float32)
    std  = np.array(IMAGENET_STD,  dtype=np.float32)
    rgb  = (rgb - mean) / std              # (H, W, 3)

    tensor = torch.from_numpy(rgb.transpose(2, 0, 1)).unsqueeze(0)  # (1, 3, H, W)
    return tensor


def run_unet_inference(
    bgr_image: np.ndarray,
    threshold: Optional[float] = None,
) -> Optional[np.ndarray]:
    """
    Run U-Net on bgr_image and return a binary uint8 mask (0/255) at the original image size.

    Parameters
    ----------
    bgr_image : np.ndarray  BGR image as returned by cv2.imread
    threshold : float       Sigmoid threshold (default: UNET_THRESHOLD env var or 0.5)

    Returns None on failure (torch unavailable, checkpoint missing, or inference error).
    """
    if threshold is None:
        try:
            threshold = float(os.environ.get("UNET_THRESHOLD", "0.5"))
        except ValueError:
            threshold = 0.5

    model, device = get_unet_model()
    if model is None:
        return None

    orig_h, orig_w = bgr_image.shape[:2]

    try:
        tensor = _preprocess(bgr_image).to(device)

        with torch.no_grad():
            prob = model(tensor)          # (1, 1, 320, 320) float32

        prob_np   = prob.squeeze().cpu().numpy()   # (320, 320)
        prob_resz = cv2.resize(prob_np, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
        binary    = (prob_resz >= threshold).astype(np.uint8) * 255
        return binary

    except Exception as exc:
        logger.error("U-Net inference error: %s", exc, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Overlay helper
# ---------------------------------------------------------------------------

def overlay_unet_mask(
    bgr_image: np.ndarray,
    mask: np.ndarray,
    color: tuple = (0, 220, 255),   # bright cyan-yellow in BGR
    alpha: float = 0.45,
) -> np.ndarray:
    """Return a copy of bgr_image with the binary mask blended as a semi-transparent overlay."""
    overlay  = bgr_image.copy()
    coloured = np.zeros_like(bgr_image)
    coloured[mask > 0] = color
    cv2.addWeighted(coloured, alpha, overlay, 1.0 - alpha, 0, overlay)
    return overlay


# ---------------------------------------------------------------------------
# Agreement metric
# ---------------------------------------------------------------------------

def compute_agreement(
    unet_mask: np.ndarray,
    yolo_boxes: list,
    img_shape: tuple,
) -> dict:
    """
    Compute agreement between U-Net pixel mask and YOLO bounding boxes via IoU.

    Limitation: YOLO boxes are axis-aligned rectangles; they include non-crack background
    pixels inside the box.  Low IoU can reflect thin/diagonal cracks, not true disagreement.
    Always inspect both outputs visually before drawing engineering conclusions.

    Parameters
    ----------
    unet_mask  : np.ndarray  Binary mask (0/255) from run_unet_inference
    yolo_boxes : list        List of [x1, y1, x2, y2, ...] from YOLO detections
    img_shape  : tuple       (H, W) or (H, W, C) of the original image

    Returns
    -------
    dict with keys: agreement, agreement_iou, unet_crack_px, yolo_box_px, note
    """
    h, w = img_shape[:2]

    yolo_mask = np.zeros((h, w), dtype=np.uint8)
    for box in yolo_boxes:
        x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
        yolo_mask[max(0, y1):min(h, y2), max(0, x1):min(w, x2)] = 255

    unet_bin = (unet_mask > 0)
    yolo_bin = (yolo_mask > 0)

    intersection = int(np.logical_and(unet_bin, yolo_bin).sum())
    union        = int(np.logical_or(unet_bin,  yolo_bin).sum())
    iou          = intersection / union if union > 0 else 0.0

    if iou >= 0.40:
        level = "agree"
        note  = "U-Net mask and YOLO boxes overlap substantially (IoU >= 0.40)."
    elif iou >= 0.10:
        level = "partial"
        note  = (
            "U-Net and YOLO partially agree (0.10 <= IoU < 0.40). "
            "This may reflect thin or diagonal cracks inside wide YOLO boxes. "
            "Inspect both outputs before drawing conclusions."
        )
    else:
        level = "disagree"
        note  = (
            "U-Net and YOLO disagree (IoU < 0.10). "
            "Possible causes: YOLO missed a crack detected by U-Net, or U-Net produced "
            "false positives on surface texture. Manual inspection required."
        )

    return {
        "agreement"     : level,
        "agreement_iou" : round(iou, 4),
        "unet_crack_px" : int(unet_bin.sum()),
        "yolo_box_px"   : int(yolo_bin.sum()),
        "note"          : note,
    }
