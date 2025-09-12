import logging
logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from schemas import ExpenseCreate, ExpenseUpdate, ExpenseResponse
from services.expense_service import (
    create_expense,
    get_expenses as service_get_expenses,
    get_expense_by_id,
    update_expense as service_update_expense,
    delete_expense as service_delete_expense
)

from services.deps import get_current_user
from models import User

router = APIRouter()

@router.post("/expenses/", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense_route(
    expense_create: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a new expense, associated with the current authenticated user."""
    try:
        # Pass the user_id to the service to associate the expense
        db_expense = create_expense(db=db, expense_create=expense_create, user_id=current_user.id)
        return db_expense
    except Exception as e:
        logger.error(f"Error in create_expense_route: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create expense: {e}")

@router.get("/expenses/", response_model=List[ExpenseResponse])
async def get_expenses_route(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve expenses for the current authenticated user."""
    try:
        # Filter expenses by current_user.id
        expenses = service_get_expenses(db=db, skip=skip, limit=limit, user_id=current_user.id)
        return expenses
    except Exception as e:
        logger.error(f"Error in get_expenses_route: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve expenses: {e}")

@router.get("/expenses/{expense_id}/", response_model=ExpenseResponse)
async def get_expense_route(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve a specific expense, ensuring it belongs to the current user."""
    db_expense = get_expense_by_id(db=db, expense_id=expense_id)
    if db_expense is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")

    # Ensure the expense belongs to the current user
    if db_expense.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to access this expense")

    return db_expense

@router.put("/expenses/{expense_id}/", response_model=ExpenseResponse)
async def update_expense_route(
    expense_id: int,
    expense_update: ExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an expense, ensuring it belongs to the current user."""
    # check if the expense belongs to the current user
    db_expense = get_expense_by_id(db=db, expense_id=expense_id)
    if db_expense is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    if db_expense.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to update this expense")

    # If checks pass, proceed with update
    db_expense_updated = service_update_expense(db=db, expense_id=expense_id, expense_update=expense_update)
    if db_expense_updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found or could not be updated")

    return db_expense_updated

@router.delete("/expenses/{expense_id}/")
async def delete_expense_route(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an expense, ensuring it belongs to the current user."""
    # check if the expense exists and belongs to the user
    db_expense = get_expense_by_id(db=db, expense_id=expense_id)
    if db_expense is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    if db_expense.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to delete this expense")

    # If checks pass, proceed with deletion
    deleted = service_delete_expense(db=db, expense_id=expense_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found or could not be deleted")

    return {"detail": "Expense deleted successfully"}
