"""
Standalone health-score calculator.
Can be used independently of the full inference pipeline
when you already have detection results (JSON or direct values).

Formula (same as inference.py):
  40 %  total crack area
  30 %  maximum crack width
  20 %  crack density
  10 %  crack-type severity
"""

import json
from dataclasses import dataclass


@dataclass
class HealthReport:
    health_score: float
    risk_level: str
    area_score: float
    width_score: float
    density_score: float
    type_score: float


def compute_health_score(
    total_crack_area_pct: float,
    max_crack_width_px: float,
    crack_count: int,
    worst_crack_type: str = "structural",
    structure_type: str = "building",
    material_type: str = "concrete",
    img_diagonal_px: float = 1000.0,
) -> HealthReport:
    """
    Compute structural health score from summary metrics.
    Harmonized with the heuristic in 5_inference.py.

    This is a SCREENING HEURISTIC, not a validated engineering assessment.
    max_crack_width_px is normalized to image diagonal to be scale-invariant.
    img_diagonal_px should be sqrt(img_h^2 + img_w^2) of the analyzed image.
    """
    if total_crack_area_pct <= 0.0 and max_crack_width_px <= 0.0 and crack_count == 0:
        return HealthReport(
            health_score=100.0,
            risk_level="Safe",
            area_score=0.0,
            width_score=0.0,
            density_score=0.0,
            type_score=0.0,
        )

    p_cov = min(40.0, total_crack_area_pct * 8.0)
    # Normalize width to % of image diagonal (scale-invariant)
    norm_width_pct = (max_crack_width_px / max(img_diagonal_px, 1.0)) * 100.0
    p_width = min(30.0, norm_width_pct * 6.0)
    p_count = min(15.0, crack_count * 2.5)

    type_penalties = {
        "hairline": 2.0,
        "longitudinal": 6.0,
        "transverse": 8.0,
        "structural": 12.0,
        "alligator": 15.0,
    }
    p_type = type_penalties.get(worst_crack_type.lower(), 5.0)

    p_damage = p_cov + p_width + p_count + p_type

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
        "concrete": 1.00,
        "stone": 1.10,
        "asphalt": 0.85,
        "plaster": 0.70,
        "unknown": 1.00,
    }
    mm = mat_multipliers.get(material_type.lower(), 1.00)

    total_penalty = p_damage * sm * mm
    score = round(max(0.0, min(100.0, 100.0 - total_penalty)), 1)

    # Risk level consistent with SSI/Integrity mapping
    ssi_equiv = 100.0 - score
    if ssi_equiv >= 80.0:
        level = "Critical"
    elif ssi_equiv >= 65.0:
        level = "High"
    elif ssi_equiv >= 40.0:
        level = "Medium"
    elif ssi_equiv >= 20.0:
        level = "Low"
    else:
        level = "Safe"

    return HealthReport(
        health_score=score,
        risk_level=level,
        area_score=round(p_cov, 1),
        width_score=round(p_width, 1),
        density_score=round(p_count, 1),
        type_score=round(p_type, 1),
    )


if __name__ == "__main__":
    # Quick test / demo
    report = compute_health_score(
        total_crack_area_pct=3.2,
        max_crack_width_px=25,
        crack_count=4,
        worst_crack_type="structural",
    )
    print("=== Health Score Report ===")
    print(f"  Score     : {report.health_score} / 100")
    print(f"  Risk      : {report.risk_level}")
    print(f"  Sub-scores:")
    print(f"    Area    : {report.area_score}")
    print(f"    Width   : {report.width_score}")
    print(f"    Density : {report.density_score}")
    print(f"    Type    : {report.type_score}")
