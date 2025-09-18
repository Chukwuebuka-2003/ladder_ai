from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from models import Budget
from schemas import BudgetCreate, BudgetUpdate

import logging

logger = logging.getLogger(__name__)

def create_budget(db: Session, budget_create: BudgetCreate, user_id: int) -> Budget:
    """
    Creates a new budget for a specific user.
    """
    db_budget = Budget(
        **budget_create.dict(),
        user_id=user_id
    )
    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)
    logger.info(f"Created budget for user {user_id} in category '{db_budget.category}'.")
    return db_budget

def get_budgets(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Budget]:
    """
    Retrieves all budgets for a specific user.
    """
    return db.query(Budget).filter(Budget.user_id == user_id).offset(skip).limit(limit).all()

def get_budget_by_id(db: Session, budget_id: int, user_id: int) -> Optional[Budget]:
    """
    Retrieves a single budget by its ID, ensuring it belongs to the user.
    """
    return db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == user_id).first()

def update_budget(db: Session, budget_id: int, budget_update: BudgetUpdate, user_id: int) -> Optional[Budget]:
    """
    Updates an existing budget for a user.
    """
    db_budget = get_budget_by_id(db=db, budget_id=budget_id, user_id=user_id)
    if not db_budget:
        return None

    update_data = budget_update.dict(exclude_unset=True)

    if "amount" in update_data and update_data["amount"] <= 0:
        raise ValueError("Budget amount must be positive.")

    # Date validation
    start_date = update_data.get("start_date", db_budget.start_date)
    end_date = update_data.get("end_date", db_budget.end_date)
    if start_date and end_date and start_date >= end_date:
        raise ValueError("Start date must be before end date.")

    for key, value in update_data.items():
        setattr(db_budget, key, value)

    db.commit()
    db.refresh(db_budget)
    logger.info(f"Updated budget {budget_id} for user {user_id}.")
    return db_budget

def delete_budget(db: Session, budget_id: int, user_id: int) -> bool:
    """
    Deletes a budget for a user. Returns True if successful, False otherwise.
    """
    db_budget = get_budget_by_id(db=db, budget_id=budget_id, user_id=user_id)
    if db_budget:
        db.delete(db_budget)
        db.commit()
        logger.info(f"Deleted budget {budget_id} for user {user_id}.")
        return True
    return False
