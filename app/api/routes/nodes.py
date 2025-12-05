"""Node filtering endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.core.models import GraphFilterRequest, FilterResponse
from app.services.filter_service import FilterService
from app.api.dependencies import get_filter_service, verify_neo4j_connection
from app.core.exceptions import QueryExecutionException, InvalidFilterException
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/nodes", tags=["Nodes"])

@router.post("/filter", response_model=FilterResponse)
async def filter_nodes(
    filter_request: GraphFilterRequest,
    service: FilterService = Depends(get_filter_service),
    _: None = Depends(verify_neo4j_connection)
):
    """Filter graph nodes based on specified criteria
    Filter nodes by:
        - Node types(labels)
        - Property values with various operators
        - Text search across labels and properties
        - Combination of multiple filters
    Args:
        filter_request: Filter specifications including:
            - node_filter: Node type and property filters
            - search_query: Text search query
            - limit: Maximum results(1 - 1000)
            - skip: Results to skip for pagination
        service: Filter service
        _: Extra dependencies
    Returns:
        FilterResponse containing:
            - total: Number of results found
            - limit: Applied limit
            - skip: Applied skip
            - data: List of matching nodes
            - active_filters: Summary of applied filters
    Raises:
        HTTPException
            400: Invalid filter parameters HTTPException
            500: Query execution failed HTTPException
            503: Neo4j unavailable
    Examples:
        Filter persons over 25 years old:
        ```json
        {
            "node_filter": {
                "node_types": ["Person"],
                "property_filters": [
                    {
                        "property_name": "age",
                        "operator": ">",
                        "value": 25
                    }
                ]
            },
            "limit": 100
        }
        ```
    Text search:
        ```json
        {
            "search_query": "John",
            "limit": 50
        }
        ```
    """
    try:
        logger.info(f"Filtering nodes with request: {filter_request.model_dump()}")

        # Use the complete method that includes count and summary
        response = service.filter_nodes_with_count(filter_request)

        logger.info(f"Returning {response.total} nodes with {len(response.active_filters)} active filters")
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
        logger.exception(f"Unexpected error during node filtering: {str(e)}")
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
    """Get example filter request with explanations
    Returns:
        Example filter request with documentation
    """
    return {
        "description": "Example node filter request",
        "example": {
            "node_filter": {
                "node_types": ["OFFICE", "TRANSIT"],
                "property_filters": [
                    {
                        "property_name": "OFFICE",
                        "operator": "=",
                        "value": "21TO",
                        "description": "The customs office is at Toamasina (21TO)"
                    },
                    {
                        "property_name": "TRANSIT",
                        "operator": "=",
                        "value": "MU",
                        "description": "The transit is at Maurice (MU)"
                    }
                ],
                "logical_operator": "AND"
            },
            "search_query": "engineer",
            "limit": 100,
            "skip": 0
        },
        "supported_operators": [
            "=", "!=", ">", ">=", "<", "<=",
            "CONTAINS", "STARTS WITH", "ENDS WITH",
            "IN", "NOT IN", "=~"
        ],
        "logical_operators": ["AND", "OR", "NOT"]
    }


# @router.post("/filter", response_model=FilterResponse)
# async def filter_nodes(
#     filter_request: GraphFilterRequest,
#     service: FilterService = Depends(get_filter_service),
#     _: None = Depends(verify_neo4j_connection)
# ):
#     """Filter graph nodes based on specified criteria
#     Args:
#         filter_request: Filter specifications including node types, properties, and search
#         service: Filter service
#         _: Extra dependencies
#     Returns:
#         FilterResponse with matching nodes and metadata
#     Raises:
#         HTTPException: If query execution fails
#     """
#     try:
#         logger.info(f"Filtering nodes with request: {filter_request.model_dump()}")
#
#         nodes = service.filter_nodes(filter_request)
#         # active_filters = service.get_active_filters_summary(filter_request)
#
#         return FilterResponse(
#             total=len(nodes),
#             limit=filter_request.limit,
#             skip=filter_request.skip,
#             data=nodes,
#         )
#
#     except (QueryExecutionException, InvalidFilterException) as e:
#         logger.error(f"Node filtering failed: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=str(e)
#         )
#     except Exception as e:
#         logger.error(f"Unexpected error during node filtering: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Internal server error"
#         )

