"""
Prompt template loader from files.

Loads trading analysis prompts from markdown files in the prompts/ directory.
Supports custom prompts - just add a new .md file and reference it by filename (without .md).
"""

from pathlib import Path
from typing import Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PromptLoader:
    """Load and manage prompt templates from files."""

    PROMPTS_DIR = Path(__file__).parent / "prompts"

    @staticmethod
    def load_prompt(prompt_name: str) -> str:
        """
        Load a prompt template from a markdown file.

        Args:
            prompt_name: Name of the prompt (without .md extension)
                        E.g., "default", "detailed", "conservative"

        Returns:
            Prompt template content

        Raises:
            FileNotFoundError: If prompt file doesn't exist
            ValueError: If prompt_name is invalid
        """
        if not prompt_name or not isinstance(prompt_name, str):
            raise ValueError(f"Invalid prompt name: {prompt_name}")

        # Sanitize prompt name to prevent path traversal
        prompt_name = prompt_name.strip().lower()
        if "/" in prompt_name or "\\" in prompt_name or prompt_name.startswith("."):
            raise ValueError(f"Invalid prompt name (path characters not allowed): {prompt_name}")

        prompt_file = PromptLoader.PROMPTS_DIR / f"{prompt_name}.md"

        if not prompt_file.exists():
            available_prompts = PromptLoader.list_available_prompts()
            raise FileNotFoundError(
                f"Prompt '{prompt_name}' not found. "
                f"Available prompts: {', '.join(available_prompts)}. "
                f"Location: {PromptLoader.PROMPTS_DIR}"
            )

        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                content = f.read()
            logger.info(f"Loaded prompt from file", extra={"prompt": prompt_name, "file": str(prompt_file)})
            return content
        except Exception as e:
            logger.error(
                f"Failed to load prompt file",
                extra={"prompt": prompt_name, "file": str(prompt_file), "error": str(e)}
            )
            raise

    @staticmethod
    def list_available_prompts() -> list[str]:
        """
        List all available prompt templates.

        Returns:
            List of prompt names (without .md extension)
        """
        if not PromptLoader.PROMPTS_DIR.exists():
            return []

        prompts = [
            f.stem for f in PromptLoader.PROMPTS_DIR.glob("*.md")
            if f.is_file() and not f.name.startswith(".")
        ]
        return sorted(prompts)

    @staticmethod
    def get_prompt(content: str, prompt_type: Optional[str] = None) -> str:
        """
        Get a prompt template and format with content.

        Args:
            content: Report content to analyze
            prompt_type: Name of the prompt template to use
                        If None, defaults to "default"

        Returns:
            Formatted prompt ready for LLM
        """
        if prompt_type is None:
            prompt_type = "default"

        try:
            template = PromptLoader.load_prompt(prompt_type)
        except FileNotFoundError:
            logger.warning(
                f"Prompt '{prompt_type}' not found, falling back to 'default'",
                extra={"requested_prompt": prompt_type}
            )
            template = PromptLoader.load_prompt("default")

        # Format template with content
        try:
            formatted_prompt = template.format(content=content)
            return formatted_prompt
        except KeyError as e:
            logger.error(
                f"Prompt template missing {{content}} placeholder",
                extra={"prompt": prompt_type, "error": str(e)}
            )
            # Fallback: just append content if {content} not found
            return f"{template}\n\nREPORT CONTENT:\n{content}"


def get_prompt(content: str, prompt_type: Optional[str] = None) -> str:
    """
    Convenience function to get a formatted prompt.

    Args:
        content: Report content to analyze
        prompt_type: Name of the prompt template (optional, defaults to "default")

    Returns:
        Formatted prompt ready for LLM
    """
    return PromptLoader.get_prompt(content, prompt_type)


def list_prompts() -> list[str]:
    """
    Get list of available prompts.

    Returns:
        List of prompt template names
    """
    return PromptLoader.list_available_prompts()
