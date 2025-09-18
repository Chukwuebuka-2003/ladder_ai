import yaml
import os
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

PROMPTS_FILE_PATH = os.path.join(os.path.dirname(__file__), 'prompts.yaml')

def load_prompts():
    """
    Loads prompts from the prompts.yaml file on every call.
    """
    try:
        with open(PROMPTS_FILE_PATH, 'r') as f:
            prompts_data = yaml.safe_load(f)
        logger.info(f"Successfully loaded prompts from {PROMPTS_FILE_PATH}")
        return prompts_data
    except FileNotFoundError:
        logger.error(f"Prompts file not found at {PROMPTS_FILE_PATH}. Please ensure it exists.")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"Error parsing prompts file {PROMPTS_FILE_PATH}: {e}")
        return {}

def get_prompt(key: str, **kwargs) -> str:
    """
    Retrieves a prompt template by key from the loaded prompts and formats it
    with provided keyword arguments.
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
        formatted_kwargs = {}
        for k, v in kwargs.items():
            if isinstance(v, datetime):
                formatted_kwargs[k] = v.isoformat()
            else:
                formatted_kwargs[k] = v

        return template.format(**formatted_kwargs)
    except KeyError as e:
        logger.error(f"Missing keyword argument for prompt '{key}': {e}.")
        return ""
    except Exception as e:
        logger.error(f"Error formatting prompt '{key}': {e}")
        return ""
