
import yaml
import os
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

PROMPTS_FILE_PATH = os.path.join(os.path.dirname(__file__), 'prompts.yaml')

_prompts_cache = {} # Simple in-memory cache for prompts

def load_prompts():
    """
    Loads prompts from the prompts.yaml file.
    Uses a cache to avoid re-reading the file on every call.
    """
    global _prompts_cache
    if not _prompts_cache:
        try:
            with open(PROMPTS_FILE_PATH, 'r') as f:
                _prompts_cache = yaml.safe_load(f)
            logger.info(f"Successfully loaded prompts from {PROMPTS_FILE_PATH}")
        except FileNotFoundError:
            logger.error(f"Prompts file not found at {PROMPTS_FILE_PATH}. Please ensure it exists.")
            _prompts_cache = {} # Ensure it's empty if file not found
        except yaml.YAMLError as e:
            logger.error(f"Error parsing prompts file {PROMPTS_FILE_PATH}: {e}")
            _prompts_cache = {}
    return _prompts_cache

def get_prompt(key: str, **kwargs) -> str:
    """
    Retrieves a prompt template by key from the loaded prompts and formats it
    with provided keyword arguments.

    Args:
        key: The key of the prompt template (e.g., 'categorize_expense').
        **kwargs: Keyword arguments to format the prompt string.

    Returns:
        The formatted prompt string, or an empty string if the prompt key is not found,
        the prompts file could not be loaded, or if there was an error during formatting.
    """
    prompts_data = load_prompts()
    if not prompts_data or 'prompts' not in prompts_data:
        logger.error("Prompts data not loaded or missing 'prompts' root key.")
        return ""

    template = prompts_data['prompts'].get(key)
    if not template:
        logger.warning(f"Prompt key '{key}' not found in prompts.yaml.")
        return ""

    try:
        # Use str.format for easy placeholder replacement.
        # Convert datetime objects to ISO format strings for consistency if they appear in kwargs.
        formatted_kwargs = {}
        for k, v in kwargs.items():
            if isinstance(v, datetime):
                formatted_kwargs[k] = v.isoformat()
            else:
                formatted_kwargs[k] = v

        return template.format(**formatted_kwargs)
    except KeyError as e:
     
        try:
            missing_key_info = f"Unknown (check template for required keys)"
            if '{' in template:
                potential_keys = template.split('{')[1].split('}')[0]
                missing_key_info = f"Expected '{potential_keys}' but missing."
            logger.error(f"Missing keyword argument for prompt '{key}': {e}. {missing_key_info}")
        except Exception: # Fallback if template parsing fails
             logger.error(f"Missing keyword argument for prompt '{key}': {e}.")
        return ""
    except Exception as e:
        logger.error(f"Error formatting prompt '{key}': {e}")
        return ""
