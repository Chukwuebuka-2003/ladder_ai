from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from database import get_db
from models import User, Expense
from schemas import AIProvider, InsightsResponse, CategorizeRequest, InsightsRequestWithProvider, ExpenseUpdate
from services.ai_service import categorize_expense_with_ai, get_insights_using_ai
from services.deps import get_current_user
from services.expense_service import update_expense

router = APIRouter()

# Configure logger once at module level
logger = logging.getLogger(__name__)


@router.post("/categorize", response_model=str)
async def categorize_expense_endpoint(
    request: CategorizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Takes expense details and AI provider, returns AI-predicted category.
    Requires authentication.
    """
    try:
        expense_details = request.expense_details
        predicted_category = categorize_expense_with_ai(
            description=expense_details.description,
            amount=expense_details.amount,
            date=expense_details.date,
            ai_provider=request.ai_provider,
        )
        return predicted_category

    except HTTPException:
        raise  # Re-raise known HTTP exceptions
    except Exception as e:
        logger.error(f"AI categorization failed for provider {request.ai_provider}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI categorization failed. Please try again later."
        )


@router.post("/insights", response_model=InsightsResponse)
async def get_insights_endpoint(
    request: InsightsRequestWithProvider,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Takes date range and AI provider, returns AI-generated insights for the current user.
    Requires authentication.
    """
    user_id = current_user.id
    start_date = request.start_date
    end_date = request.end_date

    # Fetch expenses from DB
    try:
        expenses = db.query(Expense).filter(
            Expense.user_id == user_id,
            Expense.date.between(start_date, end_date)
        ).all()
    except Exception as e:
        logger.error(f"Database error fetching expenses for insights (user={user_id}): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve expense data."
        )

    # Format expenses for AI service
    expenses_data_for_ai = [
        {
            "amount": expense.amount,
            "description": expense.description,
            "category": expense.category,
            "date": expense.date.isoformat() if expense.date else None,
        }
        for expense in expenses
    ]

    # Call AI service with provider
    try:
        insights = get_insights_using_ai(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            expenses_data=expenses_data_for_ai,
            ai_provider=request.ai_provider,
        )
        return InsightsResponse(**insights)

    except HTTPException:
        raise
    except Exception as e:
        provider_name = getattr(request, 'ai_provider', 'unknown')
        logger.error(f"AI insights generation failed for provider {provider_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate AI insights. Please try again later."
        )
