import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import List
from datetime import datetime, timedelta

from models import Expense
from schemas import MonthlyTrendDataPoint

logger = logging.getLogger(__name__)

def get_monthly_spending_trend(db: Session, user_id: int) -> List[MonthlyTrendDataPoint]:
    """
    Calculates the total spending for each of the last 12 months for a given user.

    This function queries the database to:
    - Filter expenses for the specified user within the last 365 days.
    - Group the expenses by year and month.
    - Sum the amounts for each group.
    - Order the results chronologically.

    Returns:
        A list of MonthlyTrendDataPoint objects representing the spending trend.
    """
    # Calculate the date 12 months ago from today
    twelve_months_ago = datetime.utcnow() - timedelta(days=365)

    # Perform the aggregation query
    try:
        monthly_totals = (
            db.query(
                extract("year", Expense.date).label("year"),
                extract("month", Expense.date).label("month"),
                func.sum(Expense.amount).label("total_spent"),
            )
            .filter(Expense.user_id == user_id, Expense.date >= twelve_months_ago)
            .group_by(extract("year", Expense.date), extract("month", Expense.date))
            .order_by(extract("year", Expense.date), extract("month", Expense.date))
            .all()
        )

        # Format the raw database result into our Pydantic schema
        trend_data = [
            MonthlyTrendDataPoint(
                year=row.year,
                month=row.month,
                total_spent=row.total_spent
            )
            for row in monthly_totals
        ]

        logger.info(f"Successfully generated monthly trend data for user {user_id}.")
        return trend_data

    except Exception as e:
        logger.error(f"Error generating monthly trend data for user {user_id}: {e}")
        # In case of an error, return an empty list to prevent the API from crashing
        return []
