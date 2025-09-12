from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date

from models import Expense, User
from schemas import ExpenseCreate, ExpenseUpdate
from services.ai_service import categorize_expense_with_ai

import logging

logger = logging.getLogger(__name__)


def _parse_date(raw_date) -> Optional[date]:
    """Helper to safely parse raw date input into a date object."""
    if isinstance(raw_date, datetime):
        return raw_date.date()
    elif isinstance(raw_date, date):
        return raw_date
    elif isinstance(raw_date, str):
        try:
            return datetime.strptime(raw_date, "%Y-%m-%d").date()
        except ValueError:
            logger.warning(f"Failed to parse date string '{raw_date}'.")
            return None
    return None


def create_expense(db: Session, expense_create: ExpenseCreate, user_id: int) -> Expense:
    """
    Creates a new expense entry, performs AI-based categorization if needed,
    and ensures date is correctly formatted before saving.
    """
    expense_date = _parse_date(expense_create.date) or date.today()

    db_expense = Expense(
        amount=expense_create.amount,
        description=expense_create.description,
        category=expense_create.category,
        date=expense_date,
        user_id=user_id,
    )

    # AI Categorization if category is missing
    if not db_expense.category and db_expense.date:
        try:
            db_expense.category = categorize_expense_with_ai(
                description=db_expense.description,
                amount=db_expense.amount,
                date=db_expense.date
            )
        except Exception as e:
            logger.error(f"AI categorization failed: {e}")
            db_expense.category = "Miscellaneous"

    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense


def get_expenses(db: Session, skip: int = 0, limit: int = 10, user_id: Optional[int] = None) -> List[Expense]:
    """Fetches paginated list of expenses, optionally filtered by user."""
    query = db.query(Expense)
    if user_id is not None:
        query = query.filter(Expense.user_id == user_id)
    return query.offset(skip).limit(limit).all()


def get_expense_by_id(db: Session, expense_id: int, user_id: Optional[int] = None) -> Optional[Expense]:
    """Fetches an expense by ID, optionally filtered by user."""
    query = db.query(Expense).filter(Expense.id == expense_id)
    if user_id is not None:
        query = query.filter(Expense.user_id == user_id)
    return query.first()


def update_expense(db: Session, expense_id: int, expense_update: ExpenseUpdate, user_id: Optional[int] = None) -> Optional[Expense]:
    """Updates an existing expense, applying AI categorization when appropriate."""
    query = db.query(Expense).filter(Expense.id == expense_id)
    if user_id is not None:
        query = query.filter(Expense.user_id == user_id)
    db_expense = query.first()

    if not db_expense:
        return None

    update_data = expense_update.dict(exclude_unset=True)

    # Handle date update
    expense_date_for_ai = db_expense.date
    if "date" in update_data:
        parsed_date = _parse_date(update_data["date"])
        if parsed_date is not None:
            db_expense.date = parsed_date
            expense_date_for_ai = parsed_date
        else:
            db_expense.date = None
            expense_date_for_ai = None

    # Trigger AI categorization only if no category is provided and one is needed
    if "category" not in update_data and db_expense.category is None and expense_date_for_ai:
        try:
            db_expense.category = categorize_expense_with_ai(
                description=update_data.get("description", db_expense.description),
                amount=update_data.get("amount", db_expense.amount),
                date=expense_date_for_ai
            )
        except Exception as e:
            logger.error(f"AI categorization failed during update: {e}")

    # Apply remaining updates
    for key, value in update_data.items():
        if key not in ["category", "date"]:
            setattr(db_expense, key, value)

    # Explicitly set category if provided
    if "category" in update_data:
        db_expense.category = update_data["category"]

    db.commit()
    db.refresh(db_expense)
    return db_expense


def delete_expense(db: Session, expense_id: int, user_id: int) -> bool:
    """Deletes an expense by ID, ensuring it belongs to the given user."""
    db_expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.user_id == user_id
    ).first()

    if db_expense:
        db.delete(db_expense)
        db.commit()
        return True
    return False
