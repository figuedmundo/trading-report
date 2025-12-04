"""
Repository for analyses database operations.

Handles storing and retrieving analysis results from PostgreSQL.
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncpg
from src.db.connection import get_db_connection
from src.utils.logger import get_logger
from src.utils.exceptions import DatabaseError

logger = get_logger(__name__)


class AnalysesRepository:
    """Repository for analysis data persistence."""

    async def create_analysis(
        self,
        report_id: str,
        summary: str,
        trading_signals: List[Dict[str, Any]],
        ai_provider: str,
        thinking_budget_tokens: Optional[int] = None,
        thinking_tokens_used: Optional[int] = None,
        thinking_content: Optional[str] = None,
        operations_found: bool = False,
    ) -> Dict[str, Any]:
        """
        Create and store analysis in database.

        Args:
            report_id: UUID of the report
            summary: Executive summary text
            trading_signals: List of trading signal dicts
            ai_provider: Name of AI provider used
            thinking_budget_tokens: Token budget allocated for thinking
            thinking_tokens_used: Actual tokens consumed by thinking
            thinking_content: Full reasoning trace from thinking
            operations_found: Boolean indicating if trading operations were extracted

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
                "signal_count": len(trading_signals),
                "operations_found": operations_found,
                "thinking_tokens_used": thinking_tokens_used,
            }
        )

        try:
            async with get_db_connection() as conn:
                # Prepare query with parameterized values to prevent SQL injection
                query = """
                    INSERT INTO analyses (
                        report_id, summary, trading_signals, ai_provider,
                        thinking_budget_tokens, thinking_tokens_used, thinking_content,
                        operations_found, created_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    RETURNING id, report_id, summary, trading_signals, ai_provider,
                              thinking_budget_tokens, thinking_tokens_used, thinking_content,
                              operations_found, created_at
                """

                # Convert trading signals to JSON
                signals_json = json.dumps(trading_signals)
                now = datetime.utcnow()

                # Use provided thinking budget or default
                budget_tokens = thinking_budget_tokens or 5000

                # Execute query
                row = await conn.fetchrow(
                    query,
                    report_id,
                    summary,
                    signals_json,
                    ai_provider,
                    budget_tokens,
                    thinking_tokens_used,
                    thinking_content,
                    operations_found,
                    now,
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
                    "summary": row["summary"],
                    "trading_signals": json.loads(row["trading_signals"]),
                    "ai_provider": row["ai_provider"],
                    "thinking_budget_tokens": row["thinking_budget_tokens"],
                    "thinking_tokens_used": row["thinking_tokens_used"],
                    "thinking_content": row["thinking_content"],
                    "operations_found": row["operations_found"],
                    "created_at": row["created_at"].isoformat(),
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

        except asyncpg.IntegrityError as e:
            logger.error(
                f"Database integrity error: {str(e)}",
                extra={
                    "report_id": report_id,
                    "error": str(e),
                }
            )
            raise DatabaseError(
                f"Database integrity error: {str(e)}",
                context={"report_id": report_id, "error": str(e)}
            )

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
                    SELECT id, report_id, summary, trading_signals, ai_provider,
                           thinking_budget_tokens, thinking_tokens_used, thinking_content,
                           operations_found, created_at
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
                    "summary": row["summary"],
                    "trading_signals": json.loads(row["trading_signals"]),
                    "ai_provider": row["ai_provider"],
                    "thinking_budget_tokens": row["thinking_budget_tokens"],
                    "thinking_tokens_used": row["thinking_tokens_used"],
                    "thinking_content": row["thinking_content"],
                    "operations_found": row["operations_found"],
                    "created_at": row["created_at"].isoformat(),
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
                    SELECT id, report_id, summary, trading_signals, ai_provider,
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
                        "summary": row["summary"],
                        "trading_signals": json.loads(row["trading_signals"]),
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
                    SELECT id, report_id, summary, trading_signals, ai_provider,
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
                        "summary": row["summary"],
                        "trading_signals": json.loads(row["trading_signals"]),
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
