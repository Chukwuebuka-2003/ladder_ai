import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from schemas import BudgetCreate, BudgetUpdate, BudgetResponse
from services import budget_service
from services.deps import get_current_user
from models import User

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget_endpoint(
    budget: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new budget for the authenticated user.
    """
    return budget_service.create_budget(db=db, budget_create=budget, user_id=current_user.id)

@router.get("/", response_model=List[BudgetResponse])
def get_all_budgets_for_user_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve all budgets for the authenticated user.
    """
    return budget_service.get_budgets(db=db, user_id=current_user.id)

@router.get("/{budget_id}", response_model=BudgetResponse)
def get_single_budget_endpoint(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve a specific budget by its ID.
    """
    db_budget = budget_service.get_budget_by_id(db=db, budget_id=budget_id, user_id=current_user.id)
    if db_budget is None:
        raise HTTPException(status_code=404, detail="Budget not found")
    return db_budget

@router.put("/{budget_id}", response_model=BudgetResponse)
def update_budget_endpoint(
    budget_id: int,
    budget_update: BudgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a budget.
    """
    updated_budget = budget_service.update_budget(
        db=db, budget_id=budget_id, budget_update=budget_update, user_id=current_user.id
    )
    if updated_budget is None:
        raise HTTPException(status_code=404, detail="Budget not found")
    return updated_budget

@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget_endpoint(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a user's budget.
    """
    success = budget_service.delete_budget(db=db, budget_id=budget_id, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Budget not found")
    return {"ok": True}
