"""FastAPI dependency injection functions"""

from typing import Annotated
from fastapi import Depends, HTTPException, status, Header
from app.services.neo4j_service import neo4j_service
from app.services.filter_service import filter_service, FilterService
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

async def get_filter_service() -> FilterService:
    """Dependency for injecting filter service
    Returns:
        FilterService instance
    Example:
        ```python
        @router.post("/filter")
        async def filter_endpoint(
            service: FilterService = Depends(get_filter_service)
        ):
            return service.filter_nodes(request)
        ```
    """
    return filter_service

async def verify_neo4j_connection() -> None:
    """
    Dependency to verify Neo4j connection before processing requests
    Raises:
        HTTPException: If Neo4j connection is not available
    Example:
        ```python
        @router.post("/filter")
        async def filter_endpoint(
            _: None = Depends(verify_neo4j_connection)
        ):
            # Connection verified, proceed with logic
            pass
        ```
    """
    try:
        if not neo4j_service.verify_connection():
            logger.error("Neo4j connection verification failed")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "Service Unavailable",
                    "message": "Neo4j database is not available",
                    "service": "neo4j"
                }
            )
    except Exception as e:
        logger.error(f"Error during Neo4j connection check: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Service Unavailable",
                "message": "Failed to verify Neo4j connection",
                "service": "neo4j"
            }
        )


async def get_api_key(x_api_key: Annotated[str | None, Header()] = None) -> str | None:
    """
    Optional dependency for API key authentication
    Args:
        x_api_key: API key from request header
    Returns:
        API key if present, None otherwise
    Note:
        This is a placeholder for future authentication implementation
    """
    return x_api_key


async def validate_pagination(skip: int = 0, limit: int = 100) -> tuple[int, int]:
    """
    Dependency to validate pagination parameters
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
    Returns:
        Tuple of validated (skip, limit)
    Raises:
        HTTPException: If pagination parameters are invalid
    Example:
        ```python
        @router.get("/items")
        async def get_items(
            pagination: tuple[int, int] = Depends(validate_pagination)
        ):
            skip, limit = pagination
            return {"skip": skip, "limit": limit}
        ```
    """
    if skip < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid Parameter",
                "message": "Skip parameter must be non-negative",
                "parameter": "skip",
                "value": skip
            }
        )

    if limit < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid Parameter",
                "message": "Limit parameter must be at least 1",
                "parameter": "limit",
                "value": limit
            }
        )

    if limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid Parameter",
                "message": "Limit parameter cannot exceed 1000",
                "parameter": "limit",
                "value": limit,
                "max_allowed": 1000
            }
        )

    return skip, limit

# Type aliases for cleaner dependency injection
FilterServiceDep = Annotated[FilterService, Depends(get_filter_service)]
Neo4jConnectionDep = Annotated[None, Depends(verify_neo4j_connection)]
PaginationDep = Annotated[tuple[int, int], Depends(validate_pagination)]