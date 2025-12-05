"""FastAPI exception handlers for custom exceptions"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from neo4j.exceptions import (
    Neo4jError,
    ServiceUnavailable,
    AuthError,
    CypherSyntaxError,
    TransientError
)
from app.core.exceptions import Neo4jFilterException
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


async def neo4j_filter_exception_handler(
        request: Request,
        exc: Neo4jFilterException
) -> JSONResponse:
    """
    Handler for custom Neo4j filter exceptions
    Args:
        request: FastAPI request
        exc: Custom exception
    Returns:
        JSON response with error details
    """
    logger.error(
        f"{exc.__class__.__name__}: {exc.message}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "details": exc.details
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


async def neo4j_error_handler(request: Request, exc: Neo4jError) -> JSONResponse:
    """
    Handler for Neo4j driver exceptions
    Args:
        request: FastAPI request
        exc: Neo4j exception
    Returns:
        JSON response with error details
    """
    logger.error(
        f"Neo4j Error: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__
        }
    )

    # Map Neo4j exceptions to appropriate HTTP status codes
    if isinstance(exc, ServiceUnavailable):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        message = "Neo4j database is unavailable"
    elif isinstance(exc, AuthError):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        message = "Neo4j authentication failed"
    elif isinstance(exc, CypherSyntaxError):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        message = "Query syntax error"
    elif isinstance(exc, TransientError):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        message = "Temporary database error, please retry"
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        message = "Database error occurred"

    return JSONResponse(
        status_code=status_code,
        content={
            "error": "Neo4jError",
            "message": message,
            "details": {
                "neo4j_error_type": type(exc).__name__,
                "neo4j_error_message": str(exc)
            }
        }
    )


async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError
) -> JSONResponse:
    """
    Handler for Pydantic validation errors
    Args:
        request: FastAPI request
        exc: Validation error
    Returns:
        JSON response with validation error details
    """
    errors = exc.errors()

    logger.warning(
        f"Validation error on {request.url.path}",
        extra={
            "method": request.method,
            "errors": errors
        }
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "message": "Request validation failed",
            "details": {
                "validation_errors": [
                    {
                        "field": ".".join(str(loc) for loc in error["loc"]),
                        "message": error["msg"],
                        "type": error["type"]
                    }
                    for error in errors
                ]
            }
        }
    )


async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException
) -> JSONResponse:
    """
    Handler for standard HTTP exceptions
    Args:
        request: FastAPI request
        exc: HTTP exception
    Returns:
        JSON response with error details
    """
    logger.warning(
        f"HTTP {exc.status_code} on {request.url.path}",
        extra={
            "method": request.method,
            "status_code": exc.status_code
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTPError",
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler for uncaught exceptions
    Args:
        request: FastAPI request
        exc: Uncaught exception
    Returns:
        JSON response with generic error message
    """
    logger.exception(
        f"Unhandled exception on {request.url.path}",
        extra={
            "method": request.method,
            "exception_type": type(exc).__name__
        },
        exc_info=exc
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "details": {
                "exception_type": type(exc).__name__
            }
        }
    )

def register_exception_handlers(app):
    """
    Register all exception handlers with FastAPI app
    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(Neo4jFilterException, neo4j_filter_exception_handler)
    app.add_exception_handler(Neo4jError, neo4j_error_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)