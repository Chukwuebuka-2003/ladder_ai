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


@router.post("/ai/categorize/", response_model=str)
async def categorize_expense_endpoint(
    request: CategorizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Categorize an expense using the requested AI provider and return the predicted category.
    
    Parameters:
        request (CategorizeRequest): Contains `expense_details` (description, amount, date) and `ai_provider`.
        
    Returns:
        str: Predicted category label produced by the AI provider.
    
    Raises:
        HTTPException: Propagates HTTPException from downstream calls; raises a 500 HTTPException if AI categorization fails.
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


@router.post("/ai/insights/", response_model=InsightsResponse)
async def get_insights_endpoint(
    request: InsightsRequestWithProvider,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Return AI-generated insights for the authenticated user over a given date range.
    
    Retrieves the current user's expenses between request.start_date and request.end_date, formats them for the AI service, and returns the insights produced by the specified AI provider.
    
    Parameters:
        request (InsightsRequestWithProvider): Request body containing `start_date`, `end_date`, and `ai_provider`. Only `request` is documented here; dependencies (db, current_user) are injected by the framework.
    
    Returns:
        InsightsResponse: Parsed AI-generated insights for the user and date range.
    
    Raises:
        HTTPException: Raised with status 500 if expense retrieval or AI insights generation fails. Any HTTPException raised by downstream calls is re-raised.
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


@router.put("/expenses/{expense_id}/override_category/", status_code=status.HTTP_200_OK)
async def override_expense_category(
    expense_id: int,
    new_category: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Override the category for a specific expense belonging to the authenticated user.
    
    Performs a partial update that replaces the expense's category with `new_category`. Raises
    HTTPException with:
    - 404 if the expense does not exist,
    - 403 if the expense is not owned by the current user,
    - 500 if the update operation fails.
    
    Parameters:
        expense_id (int): ID of the expense to update.
        new_category (str): New category value to set on the expense.
    
    Returns:
        dict: A confirmation object with a human-readable detail message on success.
    """
    # Validate expense ownership
    db_expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not db_expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found.")
    if db_expense.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to update this expense.")

    # Use existing service to update category
    update_schema = ExpenseUpdate(category=new_category)
    updated_expense = update_expense(
        db=db,
        expense_id=expense_id,
        expense_update=update_schema,
        user_id=current_user.id
    )

    if not updated_expense:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update expense category."
        )

    return {"detail": f"Expense category updated to '{new_category}' successfully."}
