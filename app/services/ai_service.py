# /home/type-shit/expense_tracker/app/services/ai_service.py
import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from schemas import ExpenseDetails, AIProvider
from ai_providers.gemini_service import get_gemini_category as gemini_categorize, get_gemini_insights as gemini_insights_provider
from ai_providers.groq_service import get_groq_category as groq_categorize, get_groq_insights as groq_insights_provider

logger = logging.getLogger(__name__)


def categorize_expense_with_ai(
    description: str,
    amount: Optional[float] = None,
    date: Optional[datetime] = None,
    ai_provider: AIProvider = AIProvider.GEMINI
) -> str:
    """
    Categorizes an expense using the specified AI provider.
    Falls back to Gemini if an unsupported provider is given or if AI fails.
    """
    try:
        if ai_provider == AIProvider.GEMINI:
            return gemini_categorize(description=description, amount=amount, date=date)
        elif ai_provider == AIProvider.GROQ:
            return groq_categorize(description=description, amount=amount, date=date)
        else:
            logger.warning(f"Unsupported AI provider '{ai_provider}' for categorization. Falling back to Gemini.")
            return gemini_categorize(description=description, amount=amount, date=date)
    except Exception as e:
        logger.error(f"AI categorization failed for description '{description}' with provider '{ai_provider}': {e}")
        return "Miscellaneous"


def get_insights_using_ai(
    user_id: int,
    start_date: datetime,
    end_date: datetime,
    expenses_data: List[Dict[str, Any]],
    ai_provider: AIProvider
) -> Dict[str, Any]:
    """
    Generates insights using the specified AI provider.
    Includes robust handling for empty data and potential JSON parsing errors.
    """
    # Handle empty data early
    if not expenses_data:
        logger.warning(f"No expense data provided for insights generation for user {user_id}.")
        return {
            "total_spent": 0.0,
            "top_categories": [],
            "anomalies": ["No expense data available for the selected period."]
        }

    try:
        # Get raw response from AI provider
        raw_response = _get_ai_insights_response(
            ai_provider, user_id, start_date, end_date, expenses_data
        )

        # Process and normalize the response
        return _process_insights_response(raw_response, ai_provider, user_id)

    except Exception as e:
        logger.error(f"General error during AI insights generation for user {user_id} with provider '{ai_provider}': {e}")
        return {
            "total_spent": 0.0,
            "top_categories": [],
            "anomalies": [{"error_message": f"An error occurred while generating insights with {ai_provider}: {e}"}]
        }


def _get_ai_insights_response(ai_provider: AIProvider, user_id: int, start_date: datetime,
                            end_date: datetime, expenses_data: List[Dict[str, Any]]) -> Any:
    """Helper function to get raw response from AI providers."""
    if ai_provider == AIProvider.GEMINI:
        return gemini_insights_provider(user_id=user_id, start_date=start_date,
                                      end_date=end_date, expenses_data=expenses_data)
    elif ai_provider == AIProvider.GROQ:
        return groq_insights_provider(user_id=user_id, start_date=start_date,
                                    end_date=end_date, expenses_data=expenses_data)
    else:
        logger.warning(f"Unsupported AI provider '{ai_provider}' for insights. Falling back to Gemini.")
        return gemini_insights_provider(user_id=user_id, start_date=start_date,
                                      end_date=end_date, expenses_data=expenses_data)


def _process_insights_response(raw_response: Any, ai_provider: AIProvider, user_id: int) -> Dict[str, Any]:
    """Process and normalize AI response into structured insights."""

    # Handle dictionary responses directly
    if isinstance(raw_response, dict):
        logger.info(f"AI provider '{ai_provider}' returned a dictionary directly.")
        insights_data = raw_response
    # Handle string responses that need parsing
    elif isinstance(raw_response, str):
        if not raw_response:
            logger.warning(f"AI provider '{ai_provider}' returned an empty string response for user {user_id}.")
            return _get_empty_insights_response(ai_provider)

        insights_data = _parse_json_response(raw_response, ai_provider, user_id)
        if insights_data is None:
            return _get_error_insights_response(ai_provider, "Invalid response format")
    else:
        logger.error(f"AI provider '{ai_provider}' returned unexpected type: {type(raw_response)}")
        return _get_error_insights_response(ai_provider, f"Unexpected data type: {type(raw_response)}")

    # Validate and process structured data
    return _validate_insights_data(insights_data)


def _parse_json_response(raw_response: str, ai_provider: AIProvider, user_id: int) -> Optional[Dict[str, Any]]:
    """Extract and parse JSON from AI response string."""
    try:
        json_start = raw_response.find('{')
        json_end = raw_response.rfind('}') + 1

        if json_start != -1 and json_end != -1:
            insights_json_str = raw_response[json_start:json_end]
            return json.loads(insights_json_str)
        else:
            logger.error(f"AI response string did not contain valid JSON. Raw: {raw_response}")
            return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode AI JSON response: {e}. Raw: {raw_response}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing AI response: {e}. Raw: {raw_response}")
        return None


def _validate_insights_data(insights_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and clean the insights data structure."""
    processed_insights = {
        "total_spent": float(insights_data.get("total_spent", 0.0)),
        "top_categories": _ensure_list(insights_data.get("top_categories", []), "top_categories"),
        "anomalies": _process_anomalies(insights_data.get("anomalies", []))
    }
    return processed_insights


def _ensure_list(data: Any, field_name: str) -> List[Any]:
    """Ensure data is a list, converting if necessary."""
    if isinstance(data, list):
        return data
    logger.warning(f"AI returned '{field_name}' as non-list type: {type(data)}. Converting to empty list.")
    return []


def _process_anomalies(anomalies: Any) -> List[Dict[str, str]]:
    """Process anomalies into list of dictionaries."""
    if not isinstance(anomalies, list):
        if isinstance(anomalies, str):
            return [{"error_message": anomalies}]
        logger.warning(f"AI returned 'anomalies' as unexpected type: {type(anomalies)}. Converting to empty list.")
        return []

    return [
        item if isinstance(item, dict) else {"error_message": str(item)}
        for item in anomalies
    ]


def _get_empty_insights_response(ai_provider: AIProvider) -> Dict[str, Any]:
    """Return response for empty AI responses."""
    return {
        "total_spent": 0.0,
        "top_categories": [],
        "anomalies": [f"AI provider '{ai_provider}' returned no data."]
    }


def _get_error_insights_response(ai_provider: AIProvider, error_msg: str) -> Dict[str, Any]:
    """Return response for error conditions."""
    return {
        "total_spent": 0.0,
        "top_categories": [],
        "anomalies": [{"error_message": f"Error processing AI insights: {error_msg}"}]
    }
