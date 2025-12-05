"""Health check endpoints"""

from fastapi import APIRouter
from app.core.models import HealthResponse
from app.services.neo4j_service import neo4j_service
from app.config import settings

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("", response_model=HealthResponse)
async def health_check():
    """Check service health and Neo4j connectivity
    Returns:
        HealthResponse with service status
    """
    neo4j_connected = neo4j_service.verify_connection()

    return HealthResponse(
        status="healthy" if neo4j_connected else "degraded",
        neo4j_connected=neo4j_connected,
        version=settings.APP_VERSION
    )