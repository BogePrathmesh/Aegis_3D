"""
/api/structures routes
"""
from fastapi import APIRouter, HTTPException
from typing import List
from app.utils.data_loader import load_all_structures, load_structure
from app.models.schemas import InspectionInput

router = APIRouter()


@router.get("/", response_model=List[dict])
def list_structures():
    """Return summary list of all structures."""
    structures = load_all_structures()
    result = []
    for insp in structures:
        s = insp.structure
        result.append({
            "structure_id":   s.structure_id,
            "structure_name": s.structure_name,
            "structure_type": s.structure_type.value,
            "location":       s.location,
            "state":          s.state,
            "latitude":       s.latitude,
            "longitude":      s.longitude,
            "age_years":      s.age_years,
            "traffic_level":  s.traffic_level.value,
            "defect_count":   len(insp.defects),
            "max_severity":   max(d.severity_score for d in insp.defects),
            "inspection_date": insp.inspection_date,
        })
    return result


@router.get("/{structure_id}", response_model=InspectionInput)
def get_structure(structure_id: str):
    insp = load_structure(structure_id)
    if not insp:
        raise HTTPException(status_code=404, detail=f"Structure '{structure_id}' not found.")
    return insp
