"""
Automatic Surface Material Classifier for AEGIS-3D.

Uses OpenAI CLIP (ViT-B/32, MIT Licence) for zero-shot visual surface
material recognition. Compares patch-based visual embeddings against
candidate structural and architectural material representations in multimodal space.

Supported Target Labels:
- concrete       : Concrete (slabs, beams, precast panels, columns)
- brick_masonry  : Brick / Masonry (fired clay units, mortar joints)
- asphalt        : Asphalt (road surface, flexible pavement)
- plaster        : Plaster / Stucco (rendered walls, gypsum, mortar skim)
- stone          : Stone (natural rock, dressed stone, ashlar)
- tile           : Tile / Ceramic (ceramic tiles, glazed surfaces)
- other          : Other (non-structural materials, vegetation, foreign objects)
- unknown        : Unknown / Uncertain (low confidence, ambiguous, or unsuitable image)

Quality & Uncertainty Safeguards:
- Laplacian variance check: flags severely blurred, solid, or underexposed images as unsuitable.
- Minimum confidence threshold (0.35): ambiguous distributions return "Unknown / Uncertain".
- Explicit engineering disclaimer: surface appearance cannot establish concealed core materials.
"""

import logging
from typing import Dict, Any, Optional, Tuple, Union
import numpy as np
import cv2
from PIL import Image

logger = logging.getLogger(__name__)

# Model identifier
CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"

# Candidate class definitions with descriptive prompts
MATERIAL_CLASSES = [
    ("concrete", "Concrete", "a photo of a concrete structural surface or concrete slab"),
    ("brick_masonry", "Brick / Masonry", "a photo of a brick wall or masonry surface"),
    ("asphalt", "Asphalt", "a photo of an asphalt road surface or asphalt pavement"),
    ("plaster", "Plaster / Stucco", "a photo of a plaster, stucco, or render wall surface"),
    ("stone", "Stone", "a photo of a natural stone or rock surface"),
    ("tile", "Tile / Ceramic", "a photo of a ceramic tile or tiled wall surface"),
    ("other", "Other", "a photo of other non-construction materials or background"),
]

DISPLAY_LABELS = {k: label for k, label, _ in MATERIAL_CLASSES}
DISPLAY_LABELS["unknown"] = "Unknown / Uncertain"

# Confidence threshold for positive assertion
CONFIDENCE_THRESHOLD = 0.35

# Image suitability thresholds
MIN_LAPLACIAN_VARIANCE = 10.0  # Images below this are featureless / completely blurry
MIN_IMAGE_DIM = 32

# Singleton model cache
_processor = None
_model = None
_is_available = None


def is_classifier_available() -> bool:
    """Check if transformers and torch are available to run the classifier."""
    global _is_available
    if _is_available is not None:
        return _is_available
    try:
        import torch
        from transformers import CLIPProcessor, CLIPModel
        _is_available = True
    except Exception as exc:
        logger.warning("Material classifier dependencies unavailable: %s", exc)
        _is_available = False
    return _is_available


def get_clip_pipeline():
    """Lazily load and cache the CLIP processor and model singleton."""
    global _processor, _model
    if not is_classifier_available():
        return None, None

    if _model is None or _processor is None:
        try:
            from transformers import CLIPProcessor, CLIPModel
            logger.info("Loading CLIP model: %s", CLIP_MODEL_NAME)
            _processor = CLIPProcessor.from_pretrained(CLIP_MODEL_NAME)
            _model = CLIPModel.from_pretrained(CLIP_MODEL_NAME)
            _model.eval()
            logger.info("CLIP material classifier ready.")
        except Exception as exc:
            logger.error("Failed to load CLIP material model: %s", exc)
            return None, None

    return _processor, _model


def check_image_suitability(image_bgr: np.ndarray) -> Tuple[bool, str]:
    """
    Check if the input image is sharp and detailed enough for material assessment.
    Returns (is_suitable, reason).
    """
    if image_bgr is None or image_bgr.size == 0:
        return False, "Empty image data."

    h, w = image_bgr.shape[:2]
    if h < MIN_IMAGE_DIM or w < MIN_IMAGE_DIM:
        return False, f"Image resolution ({w}x{h}) is too low for texture analysis."

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if lap_var < MIN_LAPLACIAN_VARIANCE:
        return False, f"Insufficient sharpness or contrast (Laplacian variance {lap_var:.1f} < {MIN_LAPLACIAN_VARIANCE})."

    return True, "OK"


def classify_surface_material(
    image: Union[np.ndarray, Image.Image, str],
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
) -> Dict[str, Any]:
    """
    Automatically classify the visible surface material from an image.

    Args:
        image: OpenCV BGR image (ndarray), PIL Image, or file path (str).
        confidence_threshold: Minimum probability required to assert a specific material.

    Returns:
        dict with keys:
            material: canonical key ('concrete', 'brick_masonry', 'asphalt', etc.)
            label: formatted display label
            confidence: float (0.0 to 1.0)
            source: 'AI prediction' or 'Unknown'
            all_scores: dict mapping class keys to softmax probabilities
            is_uncertain: bool
            note: explanatory detail
            disclaimer: engineering qualification
    """
    disclaimer = "Surface appearance does not establish concealed, internal, or load-bearing structural materials."

    # Standardize image to BGR ndarray and PIL Image
    if isinstance(image, str):
        bgr = cv2.imread(image)
        if bgr is None:
            return {
                "material": "unknown",
                "label": DISPLAY_LABELS["unknown"],
                "confidence": 0.0,
                "source": "Unknown",
                "all_scores": {},
                "is_uncertain": True,
                "note": f"Could not read image file from path: {image}",
                "disclaimer": disclaimer,
            }
        rgb_pil = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    elif isinstance(image, np.ndarray):
        bgr = image
        rgb_pil = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    elif isinstance(image, Image.Image):
        rgb_pil = image.convert("RGB")
        bgr = cv2.cvtColor(np.array(rgb_pil), cv2.COLOR_RGB2BGR)
    else:
        return {
            "material": "unknown",
            "label": DISPLAY_LABELS["unknown"],
            "confidence": 0.0,
            "source": "Unknown",
            "all_scores": {},
            "is_uncertain": True,
            "note": "Unsupported image format provided.",
            "disclaimer": disclaimer,
        }

    # Suitability check
    is_suitable, reason = check_image_suitability(bgr)
    if not is_suitable:
        return {
            "material": "unknown",
            "label": DISPLAY_LABELS["unknown"],
            "confidence": 0.0,
            "source": "Unknown",
            "all_scores": {},
            "is_uncertain": True,
            "note": f"Image unsuitable: {reason}",
            "disclaimer": disclaimer,
        }

    # Load model
    processor, model = get_clip_pipeline()
    if processor is None or model is None:
        return {
            "material": "unknown",
            "label": DISPLAY_LABELS["unknown"],
            "confidence": 0.0,
            "source": "Unknown",
            "all_scores": {},
            "is_uncertain": True,
            "note": "Material classifier dependencies or weights unavailable.",
            "disclaimer": disclaimer,
        }

    try:
        import torch

        prompts = [p[2] for p in MATERIAL_CLASSES]
        inputs = processor(text=prompts, images=rgb_pil, return_tensors="pt", padding=True)

        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits_per_image
            probs = logits.softmax(dim=1)[0].cpu().numpy()

        all_scores = {
            cls_key: round(float(prob), 4)
            for (cls_key, _, _), prob in zip(MATERIAL_CLASSES, probs)
        }

        top_idx = int(np.argmax(probs))
        top_key, top_label, _ = MATERIAL_CLASSES[top_idx]
        top_conf = round(float(probs[top_idx]), 4)

        # Check for ambiguity: if top two classes are within 4% of each other
        sorted_probs = np.sort(probs)[::-1]
        is_close_tie = len(sorted_probs) > 1 and (sorted_probs[0] - sorted_probs[1]) < 0.05

        if top_conf < confidence_threshold:
            return {
                "material": "unknown",
                "label": DISPLAY_LABELS["unknown"],
                "confidence": top_conf,
                "source": "Unknown",
                "all_scores": all_scores,
                "is_uncertain": True,
                "note": f"Insufficient confidence ({top_conf:.1%} < {confidence_threshold:.0%}); surface features are ambiguous.",
                "disclaimer": disclaimer,
            }

        if top_key == "other":
            return {
                "material": "other",
                "label": DISPLAY_LABELS["other"],
                "confidence": top_conf,
                "source": "AI prediction",
                "all_scores": all_scores,
                "is_uncertain": False,
                "note": "Surface features do not correspond to typical structural civil materials.",
                "disclaimer": disclaimer,
            }

        note = f"Classified with {top_conf:.1%} visual confidence."
        if is_close_tie:
            second_key = MATERIAL_CLASSES[int(np.argsort(probs)[::-1][1])][1]
            note += f" Close secondary match: {second_key} ({sorted_probs[1]:.1%})."

        return {
            "material": top_key,
            "label": top_label,
            "confidence": top_conf,
            "source": "AI prediction",
            "all_scores": all_scores,
            "is_uncertain": False,
            "note": note,
            "disclaimer": disclaimer,
        }

    except Exception as exc:
        logger.error("Inference error in material classifier: %s", exc, exc_info=True)
        return {
            "material": "unknown",
            "label": DISPLAY_LABELS["unknown"],
            "confidence": 0.0,
            "source": "Unknown",
            "all_scores": {},
            "is_uncertain": True,
            "note": f"Inference error: {str(exc)}",
            "disclaimer": disclaimer,
        }
