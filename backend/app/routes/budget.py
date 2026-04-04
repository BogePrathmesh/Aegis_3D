from fastapi import APIRouter, Request
from pydantic import BaseModel
import app.services.budget_db as budget_db

router = APIRouter()

class BudgetRequest(BaseModel):
    budget: float = 50.0

@router.get("/")
def get_structures():
    return budget_db.get_all_structures()

@router.post("/optimize")
def optimize_budget_endpoint(req: BudgetRequest):
    result = budget_db.optimize_budget(req.budget)
    return result
