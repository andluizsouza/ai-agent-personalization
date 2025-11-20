"""
Utility functions for loading prompts and schemas from the prompts/ directory.

This module provides helper functions to load external prompt files,
keeping prompts separate from code for better maintainability.
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def load_prompt(filename: str, prompts_dir: Optional[Path] = None) -> str:
    """
    Load prompt content from a file in the prompts/ directory.

    Args:
        filename: Name of the file to load (e.g., 'sql_generation.txt')
        prompts_dir: Optional custom path to prompts directory.
                    If not provided, uses default '../prompts' relative to this file.

    Returns:
        Content of the prompt file as a string

    Raises:
        FileNotFoundError: If the prompt file doesn't exist
        Exception: For other I/O errors

    Example:
        >>> schema = load_prompt("customers_schema.txt")
        >>> prompt = load_prompt("sql_generation.txt")
    """
    if prompts_dir is None:
        # Default: prompts/ at project root
        prompts_dir = Path(__file__).parent.parent / "prompts"

    prompt_path = prompts_dir / filename

    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            content = f.read()
        logger.debug(f"Successfully loaded prompt from: {prompt_path}")
        return content
    except FileNotFoundError:
        logger.error(f"Prompt file not found: {prompt_path}")
        raise FileNotFoundError(f"Prompt file '{filename}' not found at {prompt_path}")
    except Exception as e:
        logger.error(f"Error loading prompt file {filename}: {e}")
        raise
