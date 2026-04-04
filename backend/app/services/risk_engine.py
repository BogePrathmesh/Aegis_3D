"""
Ignisia Insurance Risk Engine — Rule-Based MVP
================================================
Scoring formula:
  raw = Σ weighted_component_scores × infra_multiplier × temporal_multiplier
  final_score = clamp(raw, 0, 100)

Weight table (total = 100 pts before multipliers):
  Severity score (1-5)        → 0-30 pts
  Crack depth                 → 0-20 pts
  Historical growth %         → 0-15 pts
  Defect count                → 0-10 pts
  Structure age               → 0-10 pts
  Traffic load                → 0-10 pts
  Defect area / length        → 0-5  pts (bonus)
  (subtotal max ≈ 100)

Multipliers (applied post-subtotal):
  Infrastructure type:  bridge × 1.25 | dam × 1.30 | flyover × 1.20 | others × 1.0
  Temporal trend:       growth > 50% → ×1.20 | > 25% → ×1.10 | else × 1.0
"""

from __future__ import annotations
import math
from typing import List, Tuple

from app.models.schemas import (
    InspectionInput, DefectInput, DefectOutput,
    RiskOutput, RiskCategory, ActionCode, RecommendedAction,
    ScoreBreakdown, StructureType, TrafficLevel,
)


# ─── Component weight functions ──────────────────────────────────────────────

def _severity_points(score: int) -> float:
    """Maps severity 1-5 → 0-30 pts (non-linear)."""
    mapping = {1: 5, 2: 10, 3: 17, 4: 24, 5: 30}
    return float(mapping.get(score, 5))


def _depth_points(depth_mm: float) -> float:
    """Crack depth contribution → max 20 pts.
    
    Thresholds (structural engineering standards):
    < 2mm   → surface crack (hairline): 2 pts
    2-5mm   → minor:  6 pts
    5-10mm  → moderate: 11 pts
    10-20mm → severe: 16 pts
    > 20mm  → critical: 20 pts
    """
    if depth_mm < 2:
        return 2.0
    elif depth_mm < 5:
        return 6.0
    elif depth_mm < 10:
        return 11.0
    elif depth_mm < 20:
        return 16.0
    else:
        return 20.0


def _growth_points(growth_pct: float | None) -> float:
    """Historical crack growth → max 15 pts.
    
    No data → neutral 5 pts
    < 10%   → stable: 2 pts
    10-25%  → slow growth: 6 pts
    25-50%  → moderate growth: 10 pts
    > 50%   → rapid deterioration: 15 pts
    """
    if growth_pct is None:
        return 5.0
    if growth_pct < 10:
        return 2.0
    elif growth_pct < 25:
        return 6.0
    elif growth_pct < 50:
        return 10.0
    else:
        return 15.0


def _count_points(num_defects: int) -> float:
    """Number of defects → max 10 pts.
    
    Multiple defects indicate systemic deterioration.
    """
    if num_defects == 1:
        return 2.0
    elif num_defects <= 3:
        return 4.0
    elif num_defects <= 6:
        return 6.0
    elif num_defects <= 10:
        return 8.0
    else:
        return 10.0


def _age_points(age_years: int) -> float:
    """Structure age → max 10 pts.
    
    Older structures lose material strength, corrosion increases.
    Design life of most bridges: 50-75 years.
    """
    if age_years < 10:
        return 1.0
    elif age_years < 25:
        return 3.0
    elif age_years < 40:
        return 5.0
    elif age_years < 60:
        return 7.5
    else:
        return 10.0


def _traffic_points(level: TrafficLevel) -> float:
    """Traffic load → max 10 pts.
    
    Dynamic loading accelerates fatigue crack growth.
    Overloaded vehicles cause stress beyond design limits.
    """
    mapping = {
        TrafficLevel.low: 2.0,
        TrafficLevel.medium: 4.0,
        TrafficLevel.high: 7.0,
        TrafficLevel.overloaded: 10.0,
    }
    return mapping.get(level, 4.0)


def _area_length_bonus(defects: List[DefectInput]) -> float:
    """Bonus points from defect area / crack length → max 5 pts."""
    max_area = max((d.area_cm2 or 0) for d in defects)
    max_len  = max((d.length_mm or 0) for d in defects)
    pts = 0.0
    if max_area > 100:
        pts += 2.5
    elif max_area > 30:
        pts += 1.0
    if max_len > 500:
        pts += 2.5
    elif max_len > 150:
        pts += 1.0
    return min(pts, 5.0)


# ─── Multipliers ─────────────────────────────────────────────────────────────

def _infra_multiplier(stype: StructureType) -> float:
    table = {
        StructureType.bridge:        1.25,
        StructureType.dam:           1.30,
        StructureType.flyover:       1.20,
        StructureType.tunnel:        1.15,
        StructureType.retaining_wall: 1.05,
        StructureType.culvert:       1.00,
    }
    return table.get(stype, 1.0)


def _temporal_multiplier(max_growth: float | None) -> float:
    if max_growth is None:
        return 1.0
    if max_growth > 50:
        return 1.20
    elif max_growth > 25:
        return 1.10
    return 1.0


def _environment_multiplier(env_list: List[str]) -> float:
    """Location-based risk adjusted for seismic and maritime factors."""
    mult = 1.0
    if "seismic_zone" in env_list:
        mult += 0.15
    if "maritime_corrosion" in env_list:
        mult += 0.10
    return round(mult, 2)


# ─── Derived outputs ─────────────────────────────────────────────────────────

def _failure_probability(score: float) -> float:
    """
    Logistic-style approximation: P(failure) = 100 / (1 + e^(-k*(score-50)))
    Calibrated so score=50 → ~50%, score=80 → ~88%, score=30 → ~12%.
    """
    k = 0.10
    p = 100.0 / (1.0 + math.exp(-k * (score - 50)))
    return round(p, 1)


def _claim_probability(failure_p: float, score: float) -> float:
    """
    Insurance claim probability is typically ~70-80% of failure probability
    (not all failures result in claims; some are caught early).
    """
    return round(min(failure_p * 0.78, 99.9), 1)


def _premium_multiplier(score: float) -> float:
    """
    Base premium multiplier for underwriters.
    Score < 30  → 1.0x (standard)
    Score 30-50 → 1.0-1.5x (elevated)
    Score 50-70 → 1.5-2.0x (high)
    Score 70-85 → 2.0-2.8x (very high)
    Score > 85  → 2.8-4.0x (extreme)
    """
    if score < 30:
        return round(1.0, 2)
    elif score < 50:
        return round(1.0 + (score - 30) / 20 * 0.5, 2)
    elif score < 70:
        return round(1.5 + (score - 50) / 20 * 0.5, 2)
    elif score < 85:
        return round(2.0 + (score - 70) / 15 * 0.8, 2)
    else:
        return round(2.8 + (score - 85) / 15 * 1.2, 2)


def _risk_category(score: float) -> RiskCategory:
    if score < 30:
        return RiskCategory.low
    elif score < 55:
        return RiskCategory.moderate
    elif score < 75:
        return RiskCategory.high
    else:
        return RiskCategory.critical


def _recommended_action(score: float, failure_p: float) -> RecommendedAction:
    if score < 30:
        return RecommendedAction(
            code=ActionCode.routine,
            label="Routine Monitoring",
            urgency_days=365,
            detail="Structure is in acceptable condition. Schedule standard annual inspection.",
        )
    elif score < 55:
        return RecommendedAction(
            code=ActionCode.monitor,
            label="Enhanced Monitoring",
            urgency_days=90,
            detail="Elevated risk detected. Install sensors and re-inspect within 90 days.",
        )
    elif score < 70:
        return RecommendedAction(
            code=ActionCode.repair_required,
            label="Repair Required",
            urgency_days=30,
            detail="Structural deterioration confirmed. Commission repair works within 30 days.",
        )
    elif score < 85:
        return RecommendedAction(
            code=ActionCode.emergency,
            label="Emergency Inspection",
            urgency_days=7,
            detail="High failure probability. Conduct emergency structural audit within 7 days. Prepare load restriction.",
        )
    else:
        return RecommendedAction(
            code=ActionCode.close_immediately,
            label="Immediate Closure",
            urgency_days=0,
            detail="Critical risk. Structure must be closed to traffic immediately pending emergency repair.",
        )


def _per_defect_risk(d: DefectInput) -> Tuple[float, str, RiskCategory]:
    """Quick per-defect score and classification."""
    pts  = _severity_points(d.severity_score)
    pts += _depth_points(d.depth_mm)
    pts += _growth_points(d.growth_pct)
    pts  = min(pts, 65)  # single defect cap
    rc   = _risk_category(pts)
    if d.severity_score >= 4 or d.depth_mm >= 15:
        action = "CLOSE_IMMEDIATELY" if d.severity_score == 5 else "REPAIR_REQUIRED"
    elif d.severity_score == 3 or d.depth_mm >= 7:
        action = "MONITOR"
    else:
        action = "ROUTINE"
    return pts, action, rc


def _build_risk_reasons(
    inspection: InspectionInput,
    breakdown: ScoreBreakdown,
) -> List[str]:
    reasons: List[str] = []
    s = inspection.structure
    top = max(inspection.defects, key=lambda d: d.severity_score)

    if top.severity_score >= 4:
        reasons.append(f"Severity {top.severity_score}/5 crack detected — structural capacity compromised")
    if top.depth_mm >= 10:
        reasons.append(f"Deep crack detected ({top.depth_mm:.1f} mm) — risk of section failure")
    growths = [d.growth_pct for d in inspection.defects if d.growth_pct]
    if growths and max(growths) > 25:
        reasons.append(f"Rapid crack growth ({max(growths):.0f}%) since last inspection")
    if len(inspection.defects) > 5:
        reasons.append(f"{len(inspection.defects)} active defects — systemic deterioration")
    if s.age_years >= 50:
        reasons.append(f"Structure is {s.age_years} years old — approaching design life limit")
    if s.traffic_level in (TrafficLevel.high, TrafficLevel.overloaded):
        reasons.append(f"Heavy traffic load ({s.traffic_level.value}) accelerating fatigue damage")
    if not reasons:
        reasons.append("Routine inspection — no critical risks identified")
    return reasons


# ─── Main entry point ─────────────────────────────────────────────────────────

def compute_risk(inspection: InspectionInput, priority_rank: int = 1) -> RiskOutput:
    """
    Compute full insurance risk for a structure.
    priority_rank is set by the caller after ranking multiple structures.
    """
    defects   = inspection.defects
    structure = inspection.structure

    if not defects:
        raise ValueError("At least one defect is required for risk computation.")

    # ── Component scores ──
    max_severity = max(d.severity_score for d in defects)
    max_depth    = max(d.depth_mm for d in defects)
    max_growth   = max((d.growth_pct for d in defects if d.growth_pct is not None), default=None)
    num_defects  = len(defects)

    sev_pts   = _severity_points(max_severity)
    depth_pts = _depth_points(max_depth)
    grow_pts  = _growth_points(max_growth)
    cnt_pts   = _count_points(num_defects)
    age_pts   = _age_points(structure.age_years)
    traf_pts  = _traffic_points(structure.traffic_level)
    area_pts  = _area_length_bonus(defects)

    subtotal  = sev_pts + depth_pts + grow_pts + cnt_pts + age_pts + traf_pts + area_pts

    infra_mult    = _infra_multiplier(structure.structure_type)
    temporal_mult = _temporal_multiplier(max_growth)
    env_mult      = _environment_multiplier(structure.environment)

    raw_score = subtotal * infra_mult * temporal_mult * env_mult
    final_score = min(round(raw_score, 1), 100.0)

    breakdown = ScoreBreakdown(
        severity=sev_pts,
        depth=depth_pts,
        growth=grow_pts,
        count=cnt_pts,
        age=age_pts,
        traffic=traf_pts,
        subtotal=round(subtotal, 1),
        infra_multiplier=infra_mult,
        temporal_multiplier=temporal_mult,
        final_raw=round(raw_score, 1),
    )

    failure_p = _failure_probability(final_score)
    claim_p   = _claim_probability(failure_p, final_score)
    premium   = _premium_multiplier(final_score)
    category  = _risk_category(final_score)
    action    = _recommended_action(final_score, failure_p)
    reasons   = _build_risk_reasons(inspection, breakdown)

    # ── Per-defect enrichment ──
    defect_outputs: List[DefectOutput] = []
    for d in defects:
        d_score, d_action, d_rc = _per_defect_risk(d)
        defect_outputs.append(DefectOutput(
            **d.model_dump(),
            risk_category=d_rc,
            defect_risk_score=round(d_score, 1),
            suggested_action=d_action,
        ))

    return RiskOutput(
        structure_id=structure.structure_id,
        insurance_risk_score=final_score,
        risk_category=category,
        failure_probability=failure_p,
        claim_probability=claim_p,
        premium_multiplier=premium,
        repair_priority_rank=priority_rank,
        score_breakdown=breakdown,
        recommended_action=action,
        risk_reasons=reasons,
        defects=defect_outputs,
    )
