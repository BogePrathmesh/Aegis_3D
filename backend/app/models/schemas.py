from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class StructureType(str, Enum):
    bridge       = "bridge"
    dam          = "dam"
    flyover      = "flyover"
    retaining_wall = "retaining_wall"
    tunnel       = "tunnel"
    culvert      = "culvert"


class TrafficLevel(str, Enum):
    low        = "low"
    medium     = "medium"
    high       = "high"
    overloaded = "overloaded"


class RiskCategory(str, Enum):
    low      = "Low"
    moderate = "Moderate"
    high     = "High"
    critical = "Critical"


class ActionCode(str, Enum):
    routine            = "ROUTINE"
    monitor            = "MONITOR"
    repair_required    = "REPAIR_REQUIRED"
    emergency          = "EMERGENCY_INSPECTION"
    close_immediately  = "CLOSE_IMMEDIATELY"


# ── Defect ────────────────────────────────────────────────────────────
class DefectInput(BaseModel):
    defect_id:         str
    defect_type:       str = Field(..., example="crack")
    severity_score:    int = Field(..., ge=1, le=5)
    depth_mm:          float = Field(..., ge=0)
    area_cm2:          Optional[float] = None
    length_mm:         Optional[float] = None
    growth_pct:        Optional[float] = Field(None, description="% growth vs previous inspection")
    zone:              str  = Field(..., example="Span 2, Soffit")
    original_image:    Optional[str] = None
    annotated_image:   Optional[str] = None
    mask_image:        Optional[str] = None
    confidence:        Optional[float] = Field(None, ge=0, le=1)


class DefectOutput(DefectInput):
    risk_category:       RiskCategory
    defect_risk_score:   float
    suggested_action:    str


# ── Structure / Inspection ────────────────────────────────────────────
class StructureMeta(BaseModel):
    structure_id:    str
    structure_name:  str
    structure_type:  StructureType = StructureType.bridge
    location:        str
    state:           str = "Uttar Pradesh"
    latitude:        Optional[float] = None
    longitude:       Optional[float] = None
    year_built:      int
    age_years:       int
    traffic_level:   TrafficLevel = TrafficLevel.medium
    environment:     List[str] = []
    jurisdiction:    str = "PWD"
    client_name:     str = "State Infrastructure Authority"


class InspectionInput(BaseModel):
    report_id:               Optional[str] = None
    structure:               StructureMeta
    inspection_date:         str
    previous_inspection_date: Optional[str] = None
    previous_risk_score:     Optional[float] = None
    reviewed_by:             str = "Ignisia AI + Engineer Review"
    defects:                 List[DefectInput]


# ── Risk Model Output ─────────────────────────────────────────────────
class ScoreBreakdown(BaseModel):
    severity:  float
    depth:     float
    growth:    float
    count:     float
    age:       float
    traffic:   float
    subtotal:  float
    infra_multiplier:   float
    temporal_multiplier: float
    final_raw:   float


class RecommendedAction(BaseModel):
    code:         ActionCode
    label:        str
    urgency_days: int
    detail:       str


class RiskOutput(BaseModel):
    structure_id:         str
    insurance_risk_score: float = Field(..., ge=0, le=100)
    risk_category:        RiskCategory
    failure_probability:  float = Field(..., ge=0, le=100)
    claim_probability:    float = Field(..., ge=0, le=100)
    premium_multiplier:   float
    repair_priority_rank: int
    score_breakdown:      ScoreBreakdown
    recommended_action:   RecommendedAction
    risk_reasons:         List[str]
    defects:              List[DefectOutput]


# ── PDF Request ───────────────────────────────────────────────────────
class ReportRequest(BaseModel):
    inspection: InspectionInput
    risk:       RiskOutput


class ReportResponse(BaseModel):
    report_id:   str
    pdf_url:     str
    message:     str
