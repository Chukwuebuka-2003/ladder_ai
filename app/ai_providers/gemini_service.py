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
    gemini_model = genai.GenerativeModel('gemini-2.5-flash')
    logger.info("Gemini 2.5 Flash model initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Gemini model: {e}")
    raise

def get_gemini_suggestions(
    current_period_expenses: List[Dict[str, Any]],
    previous_period_expenses: List[Dict[str, Any]],
    current_start_date: str,
    current_end_date: str,
    previous_start_date: str,
    previous_end_date: str
) -> str:
    """Uses Gemini to generate spending suggestions based on comparative data."""
    prompt = get_prompt(
        "generate_suggestions",
        current_period_expenses=json.dumps(current_period_expenses),
        previous_period_expenses=json.dumps(previous_period_expenses),
        current_start_date=current_start_date,
        current_end_date=current_end_date,
        previous_start_date=previous_start_date,
        previous_end_date=previous_end_date
    )
    if not prompt:
        logger.error("Failed to get suggestion generation prompt.")
        return "I'm currently unable to generate suggestions. Please try again later."

    try:
        response = gemini_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error calling Gemini API for suggestions: {e}")
        return "I encountered an error while thinking of suggestions. Please try again."

def extract_text_from_receipt(image_data: bytes) -> Dict[str, Any]:
    """Uses Gemini 2.5 Flash to extract text from a receipt image."""
    prompt = get_prompt("extract_receipt_data")
    if not prompt:
        logger.error("Failed to get receipt extraction prompt.")
        return {}

    try:
        response = gemini_model.generate_content([prompt, {"inline_data": {"data": image_data, "mime_type": "image/jpeg"}}])
        json_str = response.text.strip()
        start_json = json_str.find('{')
        end_json = json_str.rfind('}') + 1

        if start_json == -1 or end_json == -1:
            raise ValueError("No JSON object found in Gemini response.")

        json_str = json_str[start_json:end_json]
        expense_details = json.loads(json_str)

        if "items" not in expense_details or not isinstance(expense_details["items"], list):
            raise ValueError(f"Missing or invalid 'items' key in response. Got: {expense_details}")

        return expense_details

    except Exception as e:
        logger.error(f"Error calling Gemini API for receipt extraction: {e}")
        return {}


def get_gemini_category(description: str, amount: float = None, date: datetime = None) -> str:
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
    Uses Gemini 2.5 Flash to generate insights based on expense data.
    """
    start_date_str = start_date.isoformat() if start_date else "N/A"
    end_date_str = end_date.isoformat() if end_date else "N/A"

    prompt_template = get_prompt(
        "generate_insights",
        user_id=user_id,
        start_date=start_date_str,
        end_date=end_date_str,
        expenses_data=expenses_data
    )

    if not prompt_template:
        logger.error("Failed to get insights prompt.")
        return {"total_spent": 0.0, "top_categories": [], "anomalies": []}

    try:
        response = gemini_model.generate_content(prompt_template)
        raw_response = response.text.strip()

        start_json = raw_response.find('{')
        end_json = raw_response.rfind('}') + 1
        if start_json == -1 or end_json == -1:
            raise ValueError("No JSON object found in Gemini response.")

        json_str = raw_response[start_json:end_json]
        insights = json.loads(json_str)

        required_keys = {"total_spent", "top_categories", "anomalies"}
        if not isinstance(insights, dict) or not required_keys.issubset(insights.keys()):
            raise ValueError(f"Missing required keys. Got: {list(insights.keys())}")

        return insights

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Invalid structure in Gemini response: {e}")
        return {"total_spent": 0.0, "top_categories": [], "anomalies": [{"description": "AI response could not be parsed.", "reason": str(e)}]}
    except Exception as e:
        logger.error(f"Unexpected error in Gemini insights: {e}")
        return {"total_spent": 0.0, "top_categories": [], "anomalies": [{"description": "An unexpected AI error occurred.", "reason": str(e)}]}
