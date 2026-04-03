"""
/api/risk routes — Insurance Risk Model endpoints
"""
from fastapi import APIRouter, HTTPException, Body
from typing import List
from app.models.schemas import InspectionInput, RiskOutput
from app.services.risk_engine import compute_risk
from app.utils.data_loader import load_all_structures, load_structure

router = APIRouter()


@router.post("/score", response_model=RiskOutput)
def score_structure(inspection: InspectionInput):
    """Compute insurance risk score for a given inspection payload."""
    try:
        return compute_risk(inspection, priority_rank=1)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/score/{structure_id}", response_model=RiskOutput)
def score_by_id(structure_id: str):
    """Compute insurance risk for a pre-loaded structure by ID."""
    insp = load_structure(structure_id)
    if not insp:
        raise HTTPException(status_code=404, detail=f"Structure '{structure_id}' not found.")
    try:
        return compute_risk(insp, priority_rank=1)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/rankings", response_model=List[dict])
def get_risk_rankings():
    """
    Score all structures and return them ranked by insurance risk score (highest first).
    This is the core 'Google Maps for Infrastructure Risk' endpoint.
    """
    inspections = load_all_structures()
    scores = []
    for insp in inspections:
        try:
            r = compute_risk(insp, priority_rank=0)
            scores.append({
                "structure_id":         insp.structure.structure_id,
                "structure_name":       insp.structure.structure_name,
                "structure_type":       insp.structure.structure_type.value,
                "location":             insp.structure.location,
                "state":                insp.structure.state,
                "latitude":             insp.structure.latitude,
                "longitude":            insp.structure.longitude,
                "insurance_risk_score": r.insurance_risk_score,
                "risk_category":        r.risk_category.value,
                "failure_probability":  r.failure_probability,
                "premium_multiplier":   r.premium_multiplier,
                "recommended_action":   r.recommended_action.label,
                "action_code":          r.recommended_action.code.value,
                "urgency_days":         r.recommended_action.urgency_days,
                "defect_count":         len(insp.defects),
                "max_severity":         max(d.severity_score for d in insp.defects),
                "age_years":            insp.structure.age_years,
                "risk_reasons":         r.risk_reasons,
            })
        except Exception as e:
            print(f"[risk/rankings] skipping {insp.structure.structure_id}: {e}")

    # Sort by risk score descending, assign real rank
    scores.sort(key=lambda x: x["insurance_risk_score"], reverse=True)
    for rank, item in enumerate(scores, start=1):
        item["repair_priority_rank"] = rank

    return scores


@router.get("/dashboard/stats", response_model=dict)
def get_dashboard_stats():
    """Aggregate statistics for the dashboard KPI panel."""
    rankings = get_risk_rankings()
    total    = len(rankings)
    critical = sum(1 for r in rankings if r["risk_category"] == "Critical")
    high     = sum(1 for r in rankings if r["risk_category"] == "High")
    moderate = sum(1 for r in rankings if r["risk_category"] == "Moderate")
    low      = sum(1 for r in rankings if r["risk_category"] == "Low")
    avg_score = round(sum(r["insurance_risk_score"] for r in rankings) / total, 1) if total else 0

    return {
        "total_structures":    total,
        "critical_count":      critical,
        "high_risk_count":     high,
        "moderate_count":      moderate,
        "low_count":           low,
        "average_risk_score":  avg_score,
        "requiring_action":    critical + high,
        "top_danger":          rankings[0] if rankings else None,
        "risk_distribution":   {"Critical": critical, "High": high,
                                "Moderate": moderate, "Low": low},
    }
