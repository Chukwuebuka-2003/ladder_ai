import logging
import json
from typing import Dict, Any

from prompts.prompt_utils import get_prompt
from ai_providers.gemini_service import gemini_model

logger = logging.getLogger(__name__)


def parse_message(message: str) -> Dict[str, Any]:
    """
    Parses a user's natural language message to extract intent and entities using an AI model.

    This function takes a raw string from the user, uses a specialized prompt to ask the AI
    to analyze it, and then parses the AI's response to find a structured JSON object
    containing the user's likely intent and any relevant details (entities).

    Args:
        message: The user's message string (e.g., "I spent $15 on lunch").

    Returns:
        A dictionary containing the parsed 'intent' and 'entities'. If parsing fails or the
        AI's response is unclear, it returns a default intent like 'clarification_needed'
        or 'unknown' along with an error message.
    """
    prompt = get_prompt("natural_language_understanding", user_message=message)
    if not prompt:
        logger.error("Failed to retrieve the 'natural_language_understanding' prompt.")
        return {"intent": "unknown", "entities": {"error": "NLU prompt template is missing."}}

    try:
        #generate content using the AI model
        response = gemini_model.generate_content(prompt)
        raw_response = response.text.strip()
        logger.info(f"NLU raw response from AI: {raw_response}")

        #find the start and end of the JSON object in the response
        start_json = raw_response.find('{')
        end_json = raw_response.rfind('}') + 1

        if start_json == -1 or end_json == 0:
            logger.error(f"No JSON object was found in the NLU response. Response: {raw_response}")
            return {"intent": "clarification_needed", "entities": {"original_message": message}}

        #extract and parse the JSON string
        json_str = raw_response[start_json:end_json]
        parsed_data = json.loads(json_str)

        #basic validation to ensure the JSON has the keys we expect
        if "intent" not in parsed_data or "entities" not in parsed_data:
            logger.error(f"Parsed NLU JSON is missing required 'intent' or 'entities' keys. Parsed: {parsed_data}")
            return {"intent": "clarification_needed", "entities": {"original_message": message}}

        logger.info(f"Successfully parsed NLU data: {parsed_data}")
        return parsed_data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON from NLU response: {e}. Raw response: {raw_response}")
        return {"intent": "clarification_needed", "entities": {"error": "Invalid JSON response from AI."}}
    except Exception as e:
        logger.error(f"An unexpected error occurred during NLU processing: {e}")
        return {"intent": "unknown", "entities": {"error": "An unexpected error occurred."}}
