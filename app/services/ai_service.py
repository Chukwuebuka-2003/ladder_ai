import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from schemas import AIProvider
from ai_providers.gemini_service import (
    get_gemini_category as gemini_categorize,
    get_gemini_insights as gemini_insights_provider,
    extract_text_from_receipt as gemini_extract_text,
    get_gemini_suggestions as gemini_suggestions_provider
)
from ai_providers.groq_service import (
    get_groq_category as groq_categorize,
    get_groq_insights as groq_insights_provider
)

logger = logging.getLogger(__name__)

def get_suggestions_using_ai(
    current_period_expenses: List[Dict[str, Any]],
    previous_period_expenses: List[Dict[str, Any]],
    current_start_date: str,
    current_end_date: str,
    previous_start_date: str,
    previous_end_date: str,
    ai_provider: AIProvider = AIProvider.GEMINI
) -> str:
    """Generates spending suggestions using the specified AI provider."""
    if ai_provider == AIProvider.GEMINI:
        return gemini_suggestions_provider(
            current_period_expenses,
            previous_period_expenses,
            current_start_date,
            current_end_date,
            previous_start_date,
            previous_end_date
        )
    else:
        logger.warning(f"Unsupported AI provider '{ai_provider}' for suggestions. Falling back to a default message.")
        return "I am currently unable to provide suggestions with the selected AI provider."

def extract_text_from_receipt_with_ai(image_data: bytes, ai_provider: AIProvider = AIProvider.GEMINI) -> Dict[str, Any]:
    """Extracts text from a receipt image using the specified AI provider."""
    if ai_provider == AIProvider.GEMINI:
        return gemini_extract_text(image_data=image_data)
    else:
        logger.warning(f"Unsupported AI provider '{ai_provider}' for receipt extraction. Falling back to Gemini.")
        return gemini_extract_text(image_data=image_data)

def categorize_expense_with_ai(description: str, amount: Optional[float] = None, date: Optional[datetime] = None, ai_provider: AIProvider = AIProvider.GEMINI) -> str:
    """Categorizes an expense using the specified AI provider."""
    if ai_provider == AIProvider.GEMINI:
        return gemini_categorize(description=description, amount=amount, date=date)
    elif ai_provider == AIProvider.GROQ:
        return groq_categorize(description=description, amount=amount, date=date)
    else:
        logger.warning(f"Unsupported AI provider '{ai_provider}'. Falling back to Gemini.")
        return gemini_categorize(description=description, amount=amount, date=date)

def get_insights_using_ai(user_id: int, start_date: datetime, end_date: datetime, expenses_data: List[Dict[str, Any]], ai_provider: AIProvider) -> Dict[str, Any]:
    """Generates insights using the specified AI provider."""
    if not expenses_data:
        return {"total_spent": 0.0, "top_categories": [], "anomalies": ["No expense data available."]}

    if ai_provider == AIProvider.GEMINI:
        return gemini_insights_provider(user_id=user_id, start_date=start_date, end_date=end_date, expenses_data=expenses_data)
    elif ai_provider == AIProvider.GROQ:
        return groq_insights_provider(user_id=user_id, start_date=start_date, end_date=end_date, expenses_data=expenses_data)
    else:
        logger.warning(f"Unsupported AI provider '{ai_provider}'. Falling back to Gemini.")
        return gemini_insights_provider(user_id=user_id, start_date=start_date, end_date=end_date, expenses_data=expenses_data)
