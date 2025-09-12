# /home/type-shit/expense_tracker/app/ai_providers/groq_service.py
import os
from dotenv import load_dotenv
from groq import Groq
import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional # Import Optional

from prompts.prompt_utils import get_prompt

load_dotenv()
logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY not found in environment variables.")
    raise ValueError("GROQ_API_KEY must be set.")

try:
    client = Groq(api_key=GROQ_API_KEY)
    logger.info("Groq client initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Groq client: {e}")
    raise

def get_groq_category(description: str, amount: float = None, date: datetime = None) -> str:
    """
    Predict an expense category from a description using the Groq AI chat API.
    
    Uses get_prompt("categorize_expense", ...) to build a prompt that may include optional amount and date context, then sends it to Groq (model "openai/gpt-oss-20b") and returns the assistant's trimmed response. On missing prompt or any API error the function falls back to returning "Miscellaneous".
    
    Parameters:
        description (str): Short text describing the expense.
        amount (float, optional): Numeric amount of the expense; included in the prompt when provided.
        date (datetime, optional): Date of the expense; included in the prompt when provided.
    
    Returns:
        str: Predicted expense category (or "Miscellaneous" when prompt generation fails or the API call errors).
    """
    prompt_template = get_prompt("categorize_expense", description=description, amount=amount, date=date)
    if not prompt_template:
        logger.error("Failed to get categorization prompt.")
        return "Miscellaneous"

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt_template,
                }
            ],
            model="openai/gpt-oss-20b", # choose an appropriate one from Groq's supported models
        )
        predicted_category = chat_completion.choices[0].message.content.strip()
        logger.info(f"Groq predicted category for '{description}': {predicted_category}")
        return predicted_category
    except Exception as e:
        logger.error(f"Error calling Groq API for description '{description}': {e}")
        return "Miscellaneous"

def get_groq_insights(
    user_id: int,
    start_date: Optional[datetime], # Changed to Optional[datetime]
    end_date: Optional[datetime],   # Changed to Optional[datetime]
    expenses_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generate structured expense insights for a user by calling Groq AI.
    
    Builds a prompt from the supplied user_id, optional start/end dates, and expenses_data, sends it to Groq's chat completions API, and returns the parsed JSON result as a dictionary.
    
    Parameters:
        user_id (int): ID of the user to generate insights for.
        start_date (Optional[datetime]): Inclusive start date for the expenses; treated as "N/A" when None.
        end_date (Optional[datetime]): Inclusive end date for the expenses; treated as "N/A" when None.
        expenses_data (List[Dict[str, Any]]): List of expense records used to generate insights.
    
    Returns:
        Dict[str, Any]: Parsed insights dictionary produced by the model. On failure to build a prompt, API errors, or invalid JSON responses, returns a safe default dictionary with:
          - total_spent (float): 0.0
          - top_categories (List): empty list
          - anomalies (List[str]): list containing an explanatory anomaly message
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
        return {
            "total_spent": 0.0,
            "top_categories": [],
            "anomalies": ["Error generating insights: Prompt not found"]
        }

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt_template,
                }
            ],
            model="llama3-flash-8b", # Example model, choose an appropriate one from Groq's supported models
        )
        insights_json_str = chat_completion.choices[0].message.content
        logger.info(f"Groq insights generated for user {user_id}.")

        try:
            insights = json.loads(insights_json_str)
            return insights
        except json.JSONDecodeError as json_error:
            logger.error(f"Groq response is not valid JSON: {json_error}. Raw response: {insights_json_str}")
            return {
                "total_spent": 0.0,
                "top_categories": [],
                "anomalies": ["Error generating insights: Invalid JSON response"]
            }
    except Exception as e:
        logger.error(f"Error calling Groq API for user {user_id} insights: {e}")
        return {
            "total_spent": 0.0,
            "top_categories": [],
            "anomalies": ["Error generating insights"]
        }
