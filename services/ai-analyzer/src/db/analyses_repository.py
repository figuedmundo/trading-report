"""
Repository for analyses database operations.

Handles storing and retrieving analysis results from PostgreSQL.
"""

import uuid
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncpg
from src.db.connection import get_db_connection
from src.utils.logger import get_logger
from src.utils.exceptions import DatabaseError
from src.config import Config

logger = get_logger(__name__)


class AnalysesRepository:
    """Repository for analysis data persistence."""

    async def create_analysis(
        self,
        report_id: str,
        ai_provider: str,
        raw_response: Optional[str] = None,
        thinking_budget_tokens: Optional[int] = None,
        thinking_tokens_used: Optional[int] = None,
        thinking_content: Optional[str] = None,
        operations_found: bool = False,
        model_used: Optional[str] = None,
        prompt_type: Optional[str] = None,
        title: Optional[str] = None,
        extracted_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create and store analysis in database.

        Args:
            report_id: UUID of the report
            ai_provider: Name of AI provider used
            raw_response: Raw markdown response from LLM
            thinking_budget_tokens: Token budget allocated for thinking
            thinking_tokens_used: Actual tokens consumed by thinking
            thinking_content: Full reasoning trace from thinking
            operations_found: Boolean indicating if trading operations were extracted
            model_used: Specific AI model used
            prompt_type: Type of prompt template used
            title: Title of the report
            extracted_text: Raw text content extracted from the report

        Returns:
            Created analysis record as dict

        Raises:
            DatabaseError: If insertion fails
        """
        logger.info(
            "Storing analysis in database",
            extra={
                "report_id": report_id,
                "provider": ai_provider,
                "operations_found": operations_found,
                "model_used": model_used,
                "prompt_type": prompt_type,
                "title": title,
            }
        )

        try:
            async with get_db_connection() as conn:
                now = datetime.utcnow()

                # Generate UUID from report_id URL using SHA-256 hash (deterministic and consistent)
                report_uuid = uuid.UUID(hashlib.sha256(report_id.encode()).hexdigest()[:32])

                # Ensure report exists (create if doesn't exist)
                check_report_query = "SELECT id FROM reports WHERE id = $1"
                report_exists = await conn.fetchrow(check_report_query, report_uuid)

                if not report_exists:
                    create_report_query = """
                        INSERT INTO reports (id, report_url, email_received_at, status, extracted_text)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (id) DO UPDATE 
                        SET extracted_text = COALESCE(EXCLUDED.extracted_text, reports.extracted_text),
                            updated_at = NOW()
                    """
                    await conn.execute(
                        create_report_query,
                        report_uuid,
                        report_id,
                        now,
                        'pending',
                        extracted_text
                    )
                elif extracted_text:
                    # Update existing report with extracted text if provided
                    update_report_query = """
                        UPDATE reports 
                        SET extracted_text = $1, updated_at = NOW()
                        WHERE id = $2
                    """
                    await conn.execute(update_report_query, extracted_text, report_uuid)

                # Insert analysis linked to report
                query = """
                    INSERT INTO analyses (
                        report_id, ai_provider, raw_analysis_response, 
                        model_used, prompt_type, created_at,
                        thinking_budget_tokens, thinking_tokens_used, thinking_content, operations_found, title
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    RETURNING id, report_id, ai_provider, raw_analysis_response, 
                              model_used, prompt_type, created_at, title
                """

                config = Config()
                # Use provided model_used or fall back to config
                effective_model = model_used or config.llm_model or "unknown"
                effective_prompt = prompt_type or "default"

                row = await conn.fetchrow(
                    query,
                    report_uuid,
                    ai_provider,
                    raw_response or "",
                    effective_model,
                    effective_prompt,
                    now,
                    thinking_budget_tokens or 5000,
                    thinking_tokens_used,
                    thinking_content,
                    operations_found,
                    title,
                )

                if not row:
                    raise DatabaseError(
                        "Failed to insert analysis",
                        context={"report_id": report_id}
                    )

                # Convert row to dict
                result = {
                    "id": str(row["id"]),
                    "report_id": str(row["report_id"]),
                    "ai_provider": row["ai_provider"],
                    "raw_analysis_response": row["raw_analysis_response"],
                    "model_used": row["model_used"],
                    "prompt_type": row["prompt_type"],
                    "created_at": row["created_at"].isoformat(),
                    "title": row["title"],
                }

                logger.info(
                    "Analysis stored successfully",
                    extra={
                        "report_id": report_id,
                        "analysis_id": result["id"],
                        "provider": ai_provider,
                    }
                )

                return result

        except Exception as e:
            logger.error(
                f"Database operation failed: {str(e)}",
                extra={
                    "report_id": report_id,
                    "error": str(e),
                }
            )
            raise DatabaseError(
                f"Failed to create analysis: {str(e)}",
                context={"report_id": report_id, "error": str(e)}
            )

    async def get_analysis_by_report_id(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve analysis for a specific report.

        Args:
            report_id: UUID of the report

        Returns:
            Analysis record as dict, or None if not found

        Raises:
            DatabaseError: If query fails
        """
        logger.info("Retrieving analysis from database", extra={"report_id": report_id})

        try:
            async with get_db_connection() as conn:
                query = """
                    SELECT id, report_id, ai_provider,
                           thinking_budget_tokens, thinking_tokens_used, thinking_content,
                           operations_found, raw_analysis_response, created_at, title
                    FROM analyses
                    WHERE report_id = $1
                    ORDER BY created_at DESC
                    LIMIT 1
                """

                row = await conn.fetchrow(query, report_id)

                if not row:
                    logger.info("No analysis found for report", extra={"report_id": report_id})
                    return None

                result = {
                    "id": str(row["id"]),
                    "report_id": str(row["report_id"]),
                    "ai_provider": row["ai_provider"],
                    "thinking_budget_tokens": row["thinking_budget_tokens"],
                    "thinking_tokens_used": row["thinking_tokens_used"],
                    "thinking_content": row["thinking_content"],
                    "operations_found": row["operations_found"],
                    "raw_analysis_response": row["raw_analysis_response"],
                    "created_at": row["created_at"].isoformat(),
                    "title": row["title"],
                }

                logger.info(
                    "Analysis retrieved successfully",
                    extra={
                        "report_id": report_id,
                        "analysis_id": result["id"],
                    }
                )

                return result

        except Exception as e:
            logger.error(
                f"Database query failed: {str(e)}",
                extra={
                    "report_id": report_id,
                    "error": str(e),
                }
            )
            raise DatabaseError(
                f"Failed to retrieve analysis: {str(e)}",
                context={"report_id": report_id, "error": str(e)}
            )

    async def get_analyses_by_provider(self, ai_provider: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve analyses by provider.

        Args:
            ai_provider: Name of AI provider
            limit: Maximum number of records to return

        Returns:
            List of analysis records

        Raises:
            DatabaseError: If query fails
        """
        try:
            async with get_db_connection() as conn:
                query = """
                    SELECT id, report_id, ai_provider,
                           thinking_budget_tokens, thinking_tokens_used, thinking_content,
                           operations_found, created_at
                    FROM analyses
                    WHERE ai_provider = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                """

                rows = await conn.fetch(query, ai_provider, limit)

                results = []
                for row in rows:
                    results.append({
                        "id": str(row["id"]),
                        "report_id": str(row["report_id"]),
                        "ai_provider": row["ai_provider"],
                        "thinking_budget_tokens": row["thinking_budget_tokens"],
                        "thinking_tokens_used": row["thinking_tokens_used"],
                        "thinking_content": row["thinking_content"],
                        "operations_found": row["operations_found"],
                        "created_at": row["created_at"].isoformat(),
                    })

                return results

        except Exception as e:
            logger.error(
                f"Database query failed: {str(e)}",
                extra={"error": str(e)}
            )
            raise DatabaseError(
                f"Failed to retrieve analyses: {str(e)}",
                context={"error": str(e)}
            )

    async def get_analyses_by_operations_found(self, operations_found: bool, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve analyses by operations_found flag.

        Useful for analyzing extraction success rates and statistics.

        Args:
            operations_found: Boolean flag for operations extraction
            limit: Maximum number of records to return

        Returns:
            List of analysis records with operations_found matching filter

        Raises:
            DatabaseError: If query fails
        """
        try:
            async with get_db_connection() as conn:
                query = """
                    SELECT id, report_id, ai_provider,
                           thinking_budget_tokens, thinking_tokens_used, thinking_content,
                           operations_found, created_at
                    FROM analyses
                    WHERE operations_found = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                """

                rows = await conn.fetch(query, operations_found, limit)

                results = []
                for row in rows:
                    results.append({
                        "id": str(row["id"]),
                        "report_id": str(row["report_id"]),
                        "ai_provider": row["ai_provider"],
                        "thinking_budget_tokens": row["thinking_budget_tokens"],
                        "thinking_tokens_used": row["thinking_tokens_used"],
                        "thinking_content": row["thinking_content"],
                        "operations_found": row["operations_found"],
                        "created_at": row["created_at"].isoformat(),
                    })

                return results

        except Exception as e:
            logger.error(
                f"Database query failed: {str(e)}",
                extra={"error": str(e), "operations_found": operations_found}
            )
            raise DatabaseError(
                f"Failed to retrieve analyses: {str(e)}",
                context={"error": str(e)}
            )
