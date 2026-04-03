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
) -> HealthReport:
    """
    Compute structural health score from summary metrics.

    Args:
        total_crack_area_pct: sum of all crack areas as % of image
        max_crack_width_px:   widest crack in pixels
        crack_count:          number of detected cracks
        worst_crack_type:     most severe type found

    Returns:
        HealthReport with score, level, and sub-scores
    """
    area_score = max(0, 100 - total_crack_area_pct * 8)
    width_score = max(0, 100 - max_crack_width_px * 1.5)
    density_score = max(0, 100 - crack_count * 10)

    type_weights = {
        "hairline":     0.1,
        "longitudinal": 0.3,
        "transverse":   0.4,
        "structural":   0.6,
        "alligator":    0.8,
    }
    tw = type_weights.get(worst_crack_type, 0.5)
    type_score = 100 * (1 - tw)

    score = (
        area_score    * 0.40
        + width_score * 0.30
        + density_score * 0.20
        + type_score  * 0.10
    )
    score = round(max(0, min(100, score)), 1)

    # Risk level
    if score >= 85:
        level = "Safe"
    elif score >= 70:
        level = "Low"
    elif score >= 50:
        level = "Medium"
    elif score >= 30:
        level = "High"
    else:
        level = "Critical"

    return HealthReport(
        health_score=score,
        risk_level=level,
        area_score=round(area_score, 1),
        width_score=round(width_score, 1),
        density_score=round(density_score, 1),
        type_score=round(type_score, 1),
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
