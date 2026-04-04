import os
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from app.services.report_generator import ReportGenerator

router = APIRouter(prefix="/generate-report", tags=["Reports"])

class DefectData(BaseModel):
    id: str
    type: str
    severity: int
    depth: float
    length: float
    growth: float
    image: Optional[str] = None
    heatmap: Optional[str] = None

class StructureData(BaseModel):
    structure_name: str
    location: str
    risk_score: int
    risk_level: str
    failure_probability: float
    insurance_score: int
    defects: List[DefectData] = []

def remove_file(path: str):
    try:
        os.remove(path)
    except Exception:
        pass

@router.post("/", response_class=FileResponse)
@router.post("/{structure_id}", response_class=FileResponse)
async def generate_report_endpoint(data: StructureData, background_tasks: BackgroundTasks, structure_id: str = None):
    try:
        generator = ReportGenerator(output_dir="reports")
        pdf_path = generator.generate_report(data.dict())
        
        # Optionally schedule file deletion after response
        # background_tasks.add_task(remove_file, pdf_path)
        
        return FileResponse(
            path=pdf_path,
            media_type='application/pdf',
            filename=os.path.basename(pdf_path)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")
