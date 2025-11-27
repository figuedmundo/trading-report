"""
Jinja2 template rendering engine.

Handles template loading, validation, and rendering with custom filters.
"""

import os
from typing import Dict, Any
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, TemplateError as Jinja2TemplateError
from src.utils.logger import get_logger
from src.utils.exceptions import TemplateError

logger = get_logger(__name__)


class TemplateEngine:
    """Jinja2 template rendering engine."""

    def __init__(self, template_dir: str = None):
        """
        Initialize template engine.

        Args:
            template_dir: Path to templates directory
        """
        if template_dir is None:
            # Default to templates in service directory
            template_dir = os.path.join(os.path.dirname(__file__), "..", "..", "templates")

        self.template_dir = template_dir
        self.env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)

        # Add custom filters
        self._add_filters()

    def _add_filters(self):
        """Add custom Jinja2 filters."""
        self.env.filters["title"] = lambda x: x.title() if isinstance(x, str) else str(x).title()
        self.env.filters["round"] = self._round_filter
        self.env.filters["datetimeformat"] = self._datetimeformat_filter

    @staticmethod
    def _round_filter(value, precision=2):
        """Custom round filter for numbers."""
        if value is None:
            return None
        try:
            return round(float(value), precision)
        except (ValueError, TypeError):
            return value

    @staticmethod
    def _datetimeformat_filter(value, format="%Y-%m-%d %H:%M:%S"):
        """Custom datetime format filter."""
        if not isinstance(value, datetime):
            return str(value)
        return value.strftime(format)

    async def render(self, template_path: str, context: Dict[str, Any]) -> str:
        """
        Render template with context.

        Args:
            template_path: Path to template relative to template dir
            context: Template variables

        Returns:
            Rendered template string

        Raises:
            TemplateError: If template not found or rendering fails
        """
        try:
            template = self.env.get_template(template_path)
            return template.render(context)
        except TemplateNotFound as e:
            logger.error(f"Template not found: {template_path}")
            raise TemplateError(f"Template not found: {template_path}")
        except Jinja2TemplateError as e:
            logger.error(f"Template rendering error: {str(e)}")
            raise TemplateError(f"Template rendering error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected template error: {str(e)}")
            raise TemplateError(f"Unexpected template error: {str(e)}")

    async def validate_templates_at_startup(self) -> bool:
        """
        Validate all required templates exist.

        Returns:
            True if all templates valid

        Raises:
            TemplateError: If required templates missing
        """
        required_templates = [
            "email/summary.jinja2",
            "email/alert.jinja2",
            "email/detailed_report.jinja2",
            "telegram/summary.jinja2",
            "telegram/alert.jinja2",
            "telegram/detailed_report.jinja2",
        ]

        missing = []
        for template_path in required_templates:
            full_path = os.path.join(self.template_dir, template_path)
            if not os.path.exists(full_path):
                missing.append(template_path)

        if missing:
            error_msg = f"Missing required templates: {', '.join(missing)}"
            logger.error(error_msg)
            raise TemplateError(error_msg)

        logger.info("All required templates validated")
        return True
