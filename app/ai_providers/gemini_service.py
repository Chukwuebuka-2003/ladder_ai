import google.generativeai as genai
import os
from dotenv import load_dotenv
import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from prompts.prompt_utils import get_prompt

load_dotenv()
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY not found in environment variables.")
    raise ValueError("GEMINI_API_KEY must be set.")

try:
    # ✅ Use the correct model name — verify this matches what's available in your Google Cloud project
    gemini_model = genai.GenerativeModel('gemini-2.5-flash')  # ← Recommended: stable, reliable
    logger.info("Gemini 2.5 Flash model initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Gemini model: {e}")
    raise


def get_gemini_category(description: str, amount: float = None, date: datetime = None) -> str:
    """
    Classify an expense description into a single category using the Gemini model.
    
    Builds a prompt (template "categorize_expense") from the provided expense description, optional amount, and optional date, sends it to the Gemini model, and returns the model's predicted category as a stripped string. If prompt generation fails or the model call raises an error, returns the fallback category "Miscellaneous".
    
    Parameters:
        description (str): Short free-text description of the expense.
        amount (float | None): Optional expense amount; used to provide context to the prompt.
        date (datetime | None): Optional expense date; used to provide context to the prompt.
    
    Returns:
        str: Predicted category name, or "Miscellaneous" on prompt/model errors.
    """
    prompt_template = get_prompt("categorize_expense", description=description, amount=amount, date=date)
    if not prompt_template:
        logger.error("Failed to get categorization prompt.")
        return "Miscellaneous"

    try:
        response = gemini_model.generate_content(prompt_template)
        predicted_category = response.text.strip()
        logger.info(f"Gemini predicted category for '{description}': {predicted_category}")
        return predicted_category
    except Exception as e:
        logger.error(f"Error calling Gemini API for description '{description}': {e}")
        return "Miscellaneous"


def get_gemini_insights(
    user_id: int,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    expenses_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generate structured insights from a user's expense data using Gemini (Gemini 2.5 Flash).
    
    This function requests a JSON-formatted insights response from the Gemini model and returns a validated
    dictionary that always contains the keys: "total_spent", "top_categories", and "anomalies".
    start_date and end_date are accepted as datetimes and converted to ISO strings for the prompt; if either
    is None it will be represented as "N/A" in the prompt.
    
    Parameters:
        user_id (int): Internal identifier for the user whose expenses are being analyzed.
        start_date (Optional[datetime]): Start of the analysis window; None means "N/A" for the prompt.
        end_date (Optional[datetime]): End of the analysis window; None means "N/A" for the prompt.
        expenses_data (List[Dict[str, Any]]): List of expense records to include in the prompt. Each record
            should be a mapping describing an expense (e.g., with keys such as "description", "amount",
            "date", "category" — exact fields are consumed by the prompt template).
    
    Returns:
        Dict[str, Any]: A validated insights object with the schema:
            - total_spent (float): Non-negative total amount spent.
            - top_categories (List[Dict[str, Any]]): Each item is an object containing at minimum:
                - "category" (str)
                - "amount" (number)
            - anomalies (List[Dict[str, Any]]): Each anomaly is an object containing at minimum:
                - "description" (str)
                - "amount" (number)
                - "category" (str)
                - "reason" (str)
    
    On any failure to generate, parse, or validate the model output the function returns a safe default insights
    dictionary (total_spent = 0.0, empty top_categories) and includes a single anomaly with category "system_error"
    and a short reason explaining the failure mode. The function does not raise for model or parse failures.
    """

    # Format dates safely
    start_date_str = start_date.isoformat() if start_date else "N/A"
    end_date_str = end_date.isoformat() if end_date else "N/A"

    # Get prompt template
    prompt_template = get_prompt(
        "generate_insights",
        user_id=user_id,
        start_date=start_date_str,
        end_date=end_date_str,
        expenses_data=expenses_data
    )

    if not prompt_template:
        logger.error("Failed to get insights prompt.")
        return {
            "total_spent": 0.0,
            "top_categories": [],
            "anomalies": [
                {
                    "description": "System error: Prompt generation failed.",
                    "amount": 0.0,
                    "category": "system_error",
                    "reason": "Prompt template could not be retrieved."
                }
            ]
        }

    try:
        # ✅ Generate content
        response = gemini_model.generate_content(prompt_template)
        raw_response = response.text.strip()
        logger.info(f"Gemini raw response for user {user_id}: {raw_response[:300]}...")

        # ✅ STEP 1: Extract ONLY the JSON block between first { and last }
        start_json = raw_response.find('{')
        end_json = raw_response.rfind('}') + 1

        if start_json == -1 or end_json == -1:
            raise ValueError("No JSON object found in Gemini response.")

        json_str = raw_response[start_json:end_json]

        # ✅ STEP 2: Parse JSON
        insights = json.loads(json_str)

        # ✅ STEP 3: Validate structure before returning
        required_keys = {"total_spent", "top_categories", "anomalies"}
        if not isinstance(insights, dict) or not required_keys.issubset(insights.keys()):
            raise ValueError(f"Missing required keys. Got: {list(insights.keys())}")

        # ✅ Validate types
        if not isinstance(insights["total_spent"], (int, float)) or insights["total_spent"] < 0:
            raise ValueError("total_spent must be a non-negative number.")

        if not isinstance(insights["top_categories"], list):
            raise ValueError("top_categories must be a list.")

        if not isinstance(insights["anomalies"], list):
            raise ValueError("anomalies must be a list.")

        # ✅ Optional: Enforce structure of each item in top_categories
        for item in insights["top_categories"]:
            if not isinstance(item, dict) or not all(k in item for k in ("category", "amount")):
                raise ValueError("Each top_category item must have 'category' and 'amount' keys.")

        # ✅ Optional: Enforce structure of each anomaly
        for item in insights["anomalies"]:
            if not isinstance(item, dict) or not all(k in item for k in ("description", "amount", "category", "reason")):
                raise ValueError("Each anomaly item must have 'description', 'amount', 'category', and 'reason' keys.")

        logger.info(f"Gemini insights successfully parsed for user {user_id}.")
        return insights

    except json.JSONDecodeError as e:
        logger.error(f"Gemini response is not valid JSON: {e}. Raw response: {raw_response}")
        return {
            "total_spent": 0.0,
            "top_categories": [],
            "anomalies": [
                {
                    "description": "AI response could not be parsed as valid JSON.",
                    "amount": 0.0,
                    "category": "system_error",
                    "reason": f"JSON decode error: {str(e)[:150]}"
                }
            ]
        }

    except ValueError as e:
        logger.error(f"Invalid structure in Gemini response: {e}")
        return {
            "total_spent": 0.0,
            "top_categories": [],
            "anomalies": [
                {
                    "description": "AI returned malformed data structure.",
                    "amount": 0.0,
                    "category": "system_error",
                    "reason": f"Structure validation failed: {str(e)[:150]}"
                }
            ]
        }

    except Exception as e:
        logger.error(f"Unexpected error in Gemini insights for user {user_id}: {e}")
        return {
            "total_spent": 0.0,
            "top_categories": [],
            "anomalies": [
                {
                    "description": "AI service encountered an unexpected error.",
                    "amount": 0.0,
                    "category": "system_error",
                    "reason": f"General error: {str(e)[:150]}"
                }
            ]
        }
