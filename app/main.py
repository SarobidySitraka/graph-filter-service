"""FastAPI application entry point with exception handling"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.api.routes import nodes, relationships, health
from app.api.error_handlers import register_exception_handlers
from app.services.neo4j_service import neo4j_service
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager
    Handles startup and shutdown events
    """
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Connecting to Neo4j at {settings.NEO4J_URI}")

    try:
        # Verify Neo4j connection on startup
        if neo4j_service.verify_connection():
            logger.info("Successfully connected to Neo4j")
        else:
            logger.warning("Neo4j connection could not be verified")
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j on startup: {str(e)}")

    yield

    logger.info(f"Shutting down {settings.APP_NAME}")
    neo4j_service.close()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    Advanced Neo4j graph filtering microservice with support for complex queries.

    ## Features
    - Filter nodes by type, properties, and labels
    - Filter relationships with direction and depth control
    - Multiple comparison operators (=, !=, >, <, CONTAINS, IN, etc.)
    - Text search across labels and properties
    - Pagination support
    - Comprehensive error handling
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Register exception handlers
register_exception_handlers(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(nodes.router, prefix=settings.API_V1_PREFIX)
app.include_router(relationships.router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
        "endpoints": {
            "nodes": f"{settings.API_V1_PREFIX}/nodes/filter",
            "relationships": f"{settings.API_V1_PREFIX}/relationships/filter"
        }
    }


@app.get("/health")
async def health_check_simple():
    """Simple health check endpoint"""
    return {"status": "ok"}