import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from schemas import MonthlyTrendResponse
from services import trends_service
from services.deps import get_current_user
from models import User

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/monthly", response_model=MonthlyTrendResponse)
def get_monthly_trends_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the user's total spending for each of the last 12 months.
    This data can be used to power line charts for visualizing spending trends.
    """
    trend_data = trends_service.get_monthly_spending_trend(db=db, user_id=current_user.id)
    return MonthlyTrendResponse(data=trend_data)
