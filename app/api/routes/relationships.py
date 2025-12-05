"""Relationship filtering endpoints - Updated to use complete filter service"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.core.models import GraphFilterRequest, FilterResponse
from app.services.filter_service import FilterService
from app.api.dependencies import get_filter_service, verify_neo4j_connection
from app.core.exceptions import QueryExecutionException, InvalidFilterException
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/relationships", tags=["Relationships"])


@router.post("/filter", response_model=FilterResponse)
async def filter_relationships(
    filter_request: GraphFilterRequest,
    service: FilterService = Depends(get_filter_service),
    _: None = Depends(verify_neo4j_connection)
):
    """
    Filter graph relationships based on specified criteria
    Filter relationships by:
        - Relationship types
        - Direction(incoming, outgoing, both)
        - Depth(single or multi - hop)
        - Source node types
        - Property values
    Args:
        filter_request: Filter specifications including:
            - relationship_filter: Relationship type, direction, depth
            - node_filter: Source node type filters
            - limit: Maximum results(1 - 1000)
            - skip: Results to skip for pagination
        service: Filter service
        _: Extra dependencies
    Returns:
        FilterResponse containing:
            - total: Number of results found
            - limit: Applied limit
            - skip: Applied skip
            - data: List of matching relationships
            - active_filters: Summary of applied filters
    Raises:
        HTTPException
            400: Invalid filter parameters HTTPException
            500: Query execution failed HTTPException
            503: Neo4j unavailable
    Examples:
        Filter outgoing SEND_TO relationships:
        ```json
        {
            "node_filter": {
                "node_types": ["TRANSIT"]
            },
            "relationship_filter": {
                "relationship_types": ["SEND_TO"],
                "direction": "outgoing",
                "min_depth": 1,
                "max_depth": 2
            },
            "limit": 50
        }
        ```
    """
    try:
        logger.info(f"Filtering relationships with request: {filter_request.model_dump()}")

        # Use the complete method that includes count and summary
        response = service.filter_relationships_with_count(filter_request)

        logger.info(f"Returning {response.total} relationships with {len(response.active_filters)} active filters")
        return response

    except InvalidFilterException as e:
        logger.warning(f"Invalid filter request: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict()
        )
    except QueryExecutionException as e:
        logger.error(f"Query execution failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.exception(f"Unexpected error during relationship filtering: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "An unexpected error occurred",
                "details": {"exception": str(e)}
            }
        )


@router.get("/filter/summary")
async def get_filter_summary_example():
    """
    Get example relationship filter request with explanations
    Returns:
        Example filter request with documentation
    """
    return {
        "description": "Example relationship filter request",
        "example": {
            "node_filter": {
                "node_types": ["OFFICE"]
            },
            "relationship_filter": {
                "relationship_types": ["MANAGE", "PROCESSED_BY"],
                "direction": "outgoing",
                "min_depth": 1,
                "max_depth": 3,
                "property_filters": [
                    {
                        "property_name": "ID",
                        "operator": "=",
                        "value": "INSP0001"
                    }
                ]
            },
            "limit": 100
        },
        "directions": ["incoming", "outgoing", "both"],
        "depth_range": "1-10 (default: 1)"
    }


# """Relationship filtering endpoints"""
#
# from fastapi import APIRouter, Depends, HTTPException, status
# from app.core.models import GraphFilterRequest, FilterResponse, RelationshipResponse
# from app.services.filter_service import FilterService
# from app.api.dependencies import get_filter_service, verify_neo4j_connection
# from app.core.exceptions import QueryExecutionException, InvalidFilterException
# from app.utils.logger import setup_logger
#
# logger = setup_logger(__name__)
# router = APIRouter(prefix="/relationships", tags=["Relationships"])
#
# @router.post("/filter", response_model=FilterResponse)
# async def filter_relationships(
#     filter_request: GraphFilterRequest,
#     service: FilterService = Depends(get_filter_service),
#     _: None = Depends(verify_neo4j_connection)
# ):
#     """Filter graph relationships based on specified criteria
#     Args:
#         filter_request: Filter specifications including relationship types, direction, depth
#     Returns:
#         FilterResponse with matching relationships and metadata
#     Raises:
#         HTTPException: If query execution fails
#     """
#     try:
#         logger.info(f"Filtering relationships with request: {filter_request.model_dump()}")
#
#         relationships = service.filter_relationships(filter_request)
#         active_filters = service.get_active_filters_summary(filter_request)
#
#         return FilterResponse(
#             total=len(relationships),
#             limit=filter_request.limit,
#             skip=filter_request.skip,
#             data=relationships,
#             active_filters=active_filters
#         )
#
#     except (QueryExecutionException, InvalidFilterException) as e:
#         logger.error(f"Relationship filtering failed: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=str(e)
#         )
#     except Exception as e:
#         logger.error(f"Unexpected error during relationship filtering: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Internal server error"
#         )