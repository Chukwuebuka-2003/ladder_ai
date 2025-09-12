# /home/type-shit/expense_tracker/app/prompt/prompt_utils.py

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
    Load prompts from the prompts.yaml file into an in-memory cache and return them.
    
    On first call this function reads PROMPTS_FILE_PATH and stores the parsed YAML in the module cache to avoid repeated file I/O. If the file is missing or cannot be parsed, the cache is set to an empty mapping and an empty dict is returned. Subsequent calls return the cached data.
    
    Returns:
        dict: The loaded prompts mapping (parsed YAML) or an empty dict on error.
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
    Return a prompt template identified by key formatted with provided keyword arguments.
    
    Looks up the template under the top-level 'prompts' mapping loaded by load_prompts(), converts any datetime kwargs to ISO 8601 strings, and formats the template using str.format(**kwargs). If the prompts file is not loaded, the 'prompts' root is missing, the key is not present, or formatting fails (including missing placeholders), the function logs the error and returns an empty string.
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
        # Attempt to show missing key, but be mindful of complex templates
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
