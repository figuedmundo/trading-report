"""Repository for IP allowlist database operations.

Handles CRUD operations for IP allowlist in PostgreSQL.
"""

from typing import List, Optional
from datetime import datetime
import asyncpg
from src.db.connection import get_db_connection
from src.utils.logger import get_logger
from src.utils.exceptions import DatabaseError

logger = get_logger(__name__)


class IPAllowlistRepository:
    """Repository for IP allowlist data persistence."""

    async def get_enabled_ips(self) -> List[str]:
        """Get all enabled IPs from database.

        Returns:
            List of IP addresses and CIDR ranges

        Raises:
            DatabaseError: If query fails
        """
        try:
            async with get_db_connection() as conn:
                query = """
                    SELECT ip_address FROM ip_allowlist
                    WHERE enabled = true
                    ORDER BY created_at
                """
                rows = await conn.fetch(query)
                return [row["ip_address"] for row in rows]

        except Exception as e:
            logger.error(
                f"Failed to retrieve enabled IPs from database: {str(e)}",
                extra={"error": str(e)}
            )
            raise DatabaseError(
                f"Failed to retrieve IP allowlist: {str(e)}",
                context={"error": str(e)}
            )

    async def add_ip(self, ip_address: str, description: Optional[str] = None) -> dict:
        """Add a new IP address to the allowlist.

        Args:
            ip_address: IP address or CIDR range to add
            description: Optional description of the IP

        Returns:
            Created IP allowlist record as dict

        Raises:
            DatabaseError: If insertion fails
        """
        logger.info(
            "Adding IP to allowlist",
            extra={
                "ip_address": ip_address,
                "description": description,
            }
        )

        try:
            async with get_db_connection() as conn:
                query = """
                    INSERT INTO ip_allowlist (ip_address, description, enabled, created_at, updated_at)
                    VALUES ($1, $2, true, $3, $3)
                    RETURNING id, ip_address, description, enabled, created_at, updated_at
                """
                now = datetime.now()

                row = await conn.fetchrow(
                    query,
                    ip_address,
                    description,
                    now,
                )

                if not row:
                    raise DatabaseError(
                        "Failed to insert IP address",
                        context={"ip_address": ip_address}
                    )

                result = {
                    "id": str(row["id"]),
                    "ip_address": row["ip_address"],
                    "description": row["description"],
                    "enabled": row["enabled"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                }

                logger.info(
                    "IP address added successfully",
                    extra={
                        "ip_address": ip_address,
                        "id": result["id"],
                    }
                )

                return result

        except asyncpg.IntegrityConstraintViolationError as e:
            logger.error(
                f"IP address already exists or integrity constraint violated: {str(e)}",
                extra={
                    "ip_address": ip_address,
                    "error": str(e),
                }
            )
            raise DatabaseError(
                f"IP address already exists or integrity constraint violated: {str(e)}",
                context={"ip_address": ip_address, "error": str(e)}
            )

        except Exception as e:
            logger.error(
                f"Failed to add IP address: {str(e)}",
                extra={
                    "ip_address": ip_address,
                    "error": str(e),
                }
            )
            raise DatabaseError(
                f"Failed to add IP address: {str(e)}",
                context={"ip_address": ip_address, "error": str(e)}
            )

    async def disable_ip(self, ip_address: str) -> bool:
        """Soft delete an IP address by setting enabled=false.

        Args:
            ip_address: IP address to disable

        Returns:
            True if IP was disabled, False if IP not found

        Raises:
            DatabaseError: If update fails
        """
        logger.info("Disabling IP address", extra={"ip_address": ip_address})

        try:
            async with get_db_connection() as conn:
                query = """
                    UPDATE ip_allowlist
                    SET enabled = false, updated_at = $2
                    WHERE ip_address = $1
                    RETURNING id, ip_address, enabled
                """
                now = datetime.now()

                row = await conn.fetchrow(query, ip_address, now)

                if not row:
                    logger.info("IP address not found for disabling", extra={"ip_address": ip_address})
                    return False

                logger.info(
                    "IP address disabled successfully",
                    extra={
                        "ip_address": ip_address,
                        "id": str(row["id"]),
                    }
                )
                return True

        except Exception as e:
            logger.error(
                f"Failed to disable IP address: {str(e)}",
                extra={
                    "ip_address": ip_address,
                    "error": str(e),
                }
            )
            raise DatabaseError(
                f"Failed to disable IP address: {str(e)}",
                context={"ip_address": ip_address, "error": str(e)}
            )

    async def enable_ip(self, ip_address: str) -> bool:
        """Re-enable an IP address by setting enabled=true.

        Args:
            ip_address: IP address to enable

        Returns:
            True if IP was enabled, False if IP not found

        Raises:
            DatabaseError: If update fails
        """
        logger.info("Enabling IP address", extra={"ip_address": ip_address})

        try:
            async with get_db_connection() as conn:
                query = """
                    UPDATE ip_allowlist
                    SET enabled = true, updated_at = $2
                    WHERE ip_address = $1
                    RETURNING id, ip_address, enabled
                """
                now = datetime.now()

                row = await conn.fetchrow(query, ip_address, now)

                if not row:
                    logger.info("IP address not found for enabling", extra={"ip_address": ip_address})
                    return False

                logger.info(
                    "IP address enabled successfully",
                    extra={
                        "ip_address": ip_address,
                        "id": str(row["id"]),
                    }
                )
                return True

        except Exception as e:
            logger.error(
                f"Failed to enable IP address: {str(e)}",
                extra={
                    "ip_address": ip_address,
                    "error": str(e),
                }
            )
            raise DatabaseError(
                f"Failed to enable IP address: {str(e)}",
                context={"ip_address": ip_address, "error": str(e)}
            )
