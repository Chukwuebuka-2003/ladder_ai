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
    Categorize an expense using an AI provider, returning the chosen category.
    
    If ai_provider is AIProvider.GEMINI or AIProvider.GROQ the corresponding provider is used; unsupported providers fall back to Gemini. On internal failure the function returns the string "Miscellaneous".
    
    Parameters:
        description (str): Short text describing the expense.
        amount (Optional[float]): Expense amount, if available.
        date (Optional[datetime]): Expense date, if available.
        ai_provider (AIProvider): AI provider to use (supported: GEMINI, GROQ).
    
    Returns:
        str: The category determined for the expense, or "Miscellaneous" on error.
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
    Generate structured spending insights for a user over a date range using the specified AI provider.
    
    If expenses_data is empty the function returns a default "empty" insights structure. Otherwise it delegates to the configured AI provider to obtain a raw response and normalizes that response into a dict with three keys: `total_spent` (float), `top_categories` (list), and `anomalies` (list). On any unexpected error the function returns a standardized error insights dict containing an `anomalies` entry with an `error_message`.
    
    Parameters:
        user_id (int): Identifier of the user for whom insights are generated.
        start_date (datetime): Start of the analysis range.
        end_date (datetime): End of the analysis range.
        expenses_data (List[Dict[str, Any]]): List of expense records to analyze (each record is a dict).
        ai_provider (AIProvider): Provider to use for generating insights (e.g., GEMINI or GROQ).
    
    Returns:
        Dict[str, Any]: Normalized insights structure with keys:
            - total_spent (float): Sum of expenditures (or 0.0 when empty/error).
            - top_categories (list): List of top spending categories (empty on empty/error).
            - anomalies (list): List of anomaly dicts or messages; contains error information when failures occur.
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
    """
                            Return the raw insights response from the selected AI provider.
                            
                            Delegates to the provider-specific insights function (Gemini or Groq) using the supplied user and date range data. If an unsupported provider is passed, logs a warning and falls back to the Gemini provider.
                            
                            Parameters:
                                ai_provider: Selected AI provider enum; controls which provider function is called.
                                user_id: ID of the user for whom insights are requested.
                                start_date, end_date: Date range for the requested insights.
                                expenses_data: List of expense records passed through to the provider.
                            
                            Returns:
                                The raw response returned by the provider (typically a dict or string).
                            """
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
    """
    Normalize an AI provider response into the application's structured insights dict.
    
    Accepts raw AI output (either a dict produced by the provider or a JSON-containing string), parses and validates it, and returns a sanitized insights dictionary with keys: `total_spent` (float), `top_categories` (list), and `anomalies` (list).
    
    Parameters:
        raw_response: The raw response from an AI provider — may be a dict or a string containing JSON.
        ai_provider: The AI provider enum used to produce the response (used to select sensible fallback messages).
        user_id: The numeric ID of the user for whom the insights were requested (used to contextualize parsing/fallbacks).
    
    Returns:
        A normalized insights dict. On empty or unparsable string responses, returns a default "empty" insights structure. On unexpected types or parsing failures, returns a standardized error insights structure indicating the failure.
    """

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
    """
    Extract a JSON object from an AI response string and parse it into a dictionary.
    
    Searches the input string for the first '{' and the last '}', attempts to parse the substring between them with json.loads, and returns the resulting dict on success. Returns None if no JSON object is found or if parsing fails.
    
    Parameters:
        raw_response: The raw text returned by the AI provider.
        ai_provider: AIProvider enum value used to identify the source (included for context in logs).
        user_id: ID of the user for whom the response was requested (included for context in logs).
    
    Returns:
        A dictionary parsed from the JSON contained in raw_response, or None if extraction or parsing failed.
    """
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
    """
    Validate and normalize an insights dictionary into the canonical insights shape.
    
    This function accepts a dict (typically from an AI provider) and returns a sanitized
    insights dict with three keys:
    - total_spent (float): coerced from insights_data["total_spent"] or 0.0 when missing.
    - top_categories (list): guaranteed to be a list; non-list inputs become an empty list.
    - anomalies (list[dict]): normalized list of anomaly objects; strings and non-dict items
      are converted into dicts with an "error_message" key.
    
    Parameters:
        insights_data (dict): Raw insights mapping; missing or invalid fields are replaced
        with safe defaults.
    
    Returns:
        dict: Normalized insights with keys "total_spent", "top_categories", and "anomalies".
    """
    processed_insights = {
        "total_spent": float(insights_data.get("total_spent", 0.0)),
        "top_categories": _ensure_list(insights_data.get("top_categories", []), "top_categories"),
        "anomalies": _process_anomalies(insights_data.get("anomalies", []))
    }
    return processed_insights


def _ensure_list(data: Any, field_name: str) -> List[Any]:
    """
    Ensure the provided value is a list.
    
    If `data` is already a list, it is returned unchanged. If `data` is any other type, an empty list is returned instead (the function does not attempt to wrap or coerce non-list values).
    
    Parameters:
        data: The value expected to be a list.
        field_name (str): Name of the field used for contextual logging when `data` is not a list.
    
    Returns:
        List[Any]: `data` when it's a list, otherwise an empty list.
    """
    if isinstance(data, list):
        return data
    logger.warning(f"AI returned '{field_name}' as non-list type: {type(data)}. Converting to empty list.")
    return []


def _process_anomalies(anomalies: Any) -> List[Dict[str, str]]:
    """
    Normalize the `anomalies` value into a list of dictionaries with an "error_message" key.
    
    Accepts a value that may be a list, a string, or other types:
    - If `anomalies` is a list, returns a new list where each element is kept if it's a dict, otherwise converted to {"error_message": str(item)}.
    - If `anomalies` is a string, returns [{"error_message": anomalies}].
    - For any other type, returns an empty list.
    
    Returns:
        List[Dict[str, str]]: A list of anomaly dictionaries suitable for downstream consumers.
    """
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
    """
    Return a default insights dictionary used when an AI provider returns no data.
    
    This produces a standardized insights shape with total_spent set to 0.0, an empty top_categories list,
    and a single anomaly message that includes the ai_provider identifier.
    
    Parameters:
        ai_provider (AIProvider): The AI provider that returned no data (included in the anomaly message).
    
    Returns:
        Dict[str, Any]: Insights structure indicating an empty response from the provider.
    """
    return {
        "total_spent": 0.0,
        "top_categories": [],
        "anomalies": [f"AI provider '{ai_provider}' returned no data."]
    }


def _get_error_insights_response(ai_provider: AIProvider, error_msg: str) -> Dict[str, Any]:
    """
    Return a standardized insights dictionary for AI error conditions.
    
    Parameters:
        ai_provider (AIProvider): AI provider that encountered the error (kept for interface/context).
        error_msg (str): Error message to include in the anomalies list.
    
    Returns:
        Dict[str, Any]: Insights structure with `total_spent` set to 0.0, an empty `top_categories` list,
        and `anomalies` containing a single dict with `error_message` describing the error.
    """
    return {
        "total_spent": 0.0,
        "top_categories": [],
        "anomalies": [{"error_message": f"Error processing AI insights: {error_msg}"}]
    }
