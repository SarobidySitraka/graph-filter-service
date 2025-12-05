"""
Main filter service orchestrating query building and execution
Complete implementation with all methods
"""

from typing import List, Any
from app.core.models import (
    GraphFilterRequest,
    NodeResponse,
    RelationshipResponse,
    FilterResponse
)
from app.services.neo4j_service import neo4j_service
from app.services.query_builder import CypherQueryBuilder
from app.core.exceptions import QueryExecutionException, InvalidFilterException
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def _validate_filter_request(filter_request: GraphFilterRequest) -> None:
    """Validate filter request parameters
    Args:
        filter_request: Filter specifications
    Raises:
        InvalidFilterException: If validation fails
    """
    # Check that at least one filter is provided
    has_node_filter = (
            filter_request.node_filter is not None and (
            filter_request.node_filter.node_types or
            filter_request.node_filter.property_filters
    )
    )
    has_relationship_filter = (
            filter_request.relationship_filter is not None and (
            filter_request.relationship_filter.relationship_types or
            filter_request.relationship_filter.property_filters
    )
    )
    has_search = (
            filter_request.search_query is not None and
            filter_request.search_query.strip()
    )

    if not (has_node_filter or has_relationship_filter or has_search):
        raise InvalidFilterException(
            message="At least one filter criterion must be provided",
            filter_type="request"
        )

    # Validate pagination
    if filter_request.limit < 1:
        raise InvalidFilterException(
            message="Limit must be at least 1",
            filter_type="pagination",
            invalid_field="limit",
            invalid_value=filter_request.limit
        )

    if filter_request.skip < 0:
        raise InvalidFilterException(
            message="Skip must be non-negative",
            filter_type="pagination",
            invalid_field="skip",
            invalid_value=filter_request.skip
        )


class FilterService:
    """Main service for filtering Neo4j graphs"""

    def __init__(self):
        """Initialize filter service with query builder"""
        self.query_builder = CypherQueryBuilder()

    def filter_nodes(self, filter_request: GraphFilterRequest) -> List[NodeResponse]:
        """Filter nodes based on request criteria
        Args:
            filter_request: Filter specifications
        Returns:
            List of matching nodes
        Raises:
            QueryExecutionException: If query execution fails
            InvalidFilterException: If filter parameters are invalid
        """
    # Validate request
        _validate_filter_request(filter_request)

        # Build and execute query
        query, params = self.query_builder.build_node_query(filter_request)

        try:
            with neo4j_service.get_session() as session:
                logger.debug(f"Cypher Query:\n{query}")
                print(f"Cypher query: {query}")
                result = session.run(query, params)
                nodes = []
                print(f"Nodes results: {result}")
                for record in result:
                    node_data = dict(record["n"])
                    nodes.append(NodeResponse(
                        id=record["node_id"],
                        labels=record["node_labels"],
                        properties=node_data
                    ))

                print(f"Nodes list: {nodes}")
                logger.info(f"Found {len(nodes)} nodes matching criteria")
                return nodes

        except Exception as e:
            logger.error(f"Node query execution failed: {str(e)}")
            raise QueryExecutionException(
                message="Failed to execute node query",
                query=query,
                cypher_error=str(e)
            )


    def filter_relationships(
        self,
        filter_request: GraphFilterRequest
    ) -> List[RelationshipResponse]:
        """Filter relationships based on request criteria
        Args:
            filter_request: Filter specifications
        Returns:
            List of matching relationships
        Raises:
            QueryExecutionException: If query execution fails
            InvalidFilterException: If filter parameters are invalid
        """
        # Validate request
        _validate_filter_request(filter_request)

        # Build and execute query
        query, params = self.query_builder.build_relationship_query(filter_request)

        try:
            with neo4j_service.get_session() as session:
                print(f"Cypher Query: {query}")
                print(f"Params: {params}")
                result = session.run(query, params)
                relationships = []
                print(f"Relationship result: {result}")
                for record in result:
                    source_data = dict(record["n"])
                    target_data = dict(record["m"])
                    rel_data = dict(record["r"])

                    relationships.append(RelationshipResponse(
                        id=record["rel_id"],
                        type=record["rel_type"],
                        source=NodeResponse(
                            id=record["n"].id,
                            labels=list(record["n"].labels),
                            properties=source_data
                        ),
                        target=NodeResponse(
                            id=record["m"].id,
                            labels=list(record["m"].labels),
                            properties=target_data
                        ),
                        properties=rel_data
                    ))
                print(f"Relationship list: {relationships}")

                logger.info(f"Found {len(relationships)} relationships matching criteria")
                return relationships

        except Exception as e:
            logger.error(f"Relationship query execution failed: {str(e)}")
            raise QueryExecutionException(
                message="Failed to execute relationship query",
                query=query,
                cypher_error=str(e)
            )


    def get_active_filters_summary(self, filter_request: GraphFilterRequest) -> List[str]:
        """
        Generate human-readable summary of active filters
        Args:
            filter_request: Filter specifications
        Returns:
            List of human-readable filter descriptions
        Examples:
            >>> request = GraphFilterRequest(
                    ...
                    node_filter = NodeFilter(node_types=["Person"]),
                    ...
                    limit = 100
                    ... )
            >>> service.get_active_filters_summary(request)
        ['Type: Person']
        """
        active_filters = []

        # Node type filters
        if filter_request.node_filter is not None:
            if filter_request.node_filter.node_types:
                types_str = ", ".join(filter_request.node_filter.node_types)
                active_filters.append(f"Type: {types_str}")

            # Property filters
            if filter_request.node_filter.property_filters:
                for prop_filter in filter_request.node_filter.property_filters:
                    filter_str = (
                        f"{prop_filter.property_name} "
                        f"{prop_filter.operator.value} "
                        f"{self._format_value(prop_filter.value)}"
                    )
                    active_filters.append(filter_str)

        # Relationship filters
        if filter_request.relationship_filter is not None:
            if filter_request.relationship_filter.relationship_types:
                types_str = ", ".join(filter_request.relationship_filter.relationship_types)
                active_filters.append(f"Rel: {types_str}")

            # Relationship direction
            if filter_request.relationship_filter.direction is not None:
                direction = filter_request.relationship_filter.direction.value
                active_filters.append(f"Direction: {direction}")

            # Relationship depth
            min_depth = filter_request.relationship_filter.min_depth
            max_depth = filter_request.relationship_filter.max_depth
            if min_depth != 1 or max_depth != 1:
                if min_depth == max_depth:
                    active_filters.append(f"Depth: {min_depth}")
                else:
                    active_filters.append(f"Depth: {min_depth}-{max_depth}")

            # Relationship property filters
            if filter_request.relationship_filter.property_filters:
                for prop_filter in filter_request.relationship_filter.property_filters:
                    filter_str = (
                        f"Rel.{prop_filter.property_name} "
                        f"{prop_filter.operator.value} "
                        f"{self._format_value(prop_filter.value)}"
                    )
                    active_filters.append(filter_str)

        # Search query
        if filter_request.search_query is not None and filter_request.search_query.strip():
            active_filters.append(f"Search: {filter_request.search_query}")

        return active_filters


    def filter_nodes_with_count(
        self,
        filter_request: GraphFilterRequest
    ) -> FilterResponse:
        """Filter nodes and return complete response with metadata
        Args:
            filter_request: Filter specifications
        Returns:
            FilterResponse with nodes and metadata
        """
        nodes = self.filter_nodes(filter_request)
        active_filters = self.get_active_filters_summary(filter_request)

        return FilterResponse(
            total=len(nodes),
            limit=filter_request.limit,
            skip=filter_request.skip,
            data=nodes,
            active_filters=active_filters
        )


    def filter_relationships_with_count(
        self,
        filter_request: GraphFilterRequest
    ) -> FilterResponse:
        """Filter relationships and return complete response with metadata
        Args:
            filter_request: Filter specifications
        Returns:
            FilterResponse with relationships and metadata
        """
        relationships = self.filter_relationships(filter_request)
        active_filters = self.get_active_filters_summary(filter_request)

        return FilterResponse(
            total=len(relationships),
            limit=filter_request.limit,
            skip=filter_request.skip,
            data=relationships,
            active_filters=active_filters
        )

    @staticmethod
    def _format_value(value: Any) -> str:
        """Format filter value for display
        Args:
            value: Value to format
        Returns:
            Formatted string representation
        """
        if isinstance(value, str):
            # Truncate long strings
            if len(value) > 50:
                return f'"{value[:47]}..."'
            return f'"{value}"'
        elif isinstance(value, (list, tuple)):
            # Format lists
            if len(value) > 3:
                items = ", ".join(str(v) for v in value[:3])
                return f"[{items}, ... ({len(value)} items)]"
            items = ", ".join(str(v) for v in value)
            return f"[{items}]"
        else:
            return str(value)

# Global singleton instance
filter_service = FilterService()


# """Main filter service orchestrating query building and execution"""
#
# from typing import List
# from app.core.models import GraphFilterRequest, NodeResponse, RelationshipResponse
# from app.services.neo4j_service import neo4j_service
# from app.services.query_builder import CypherQueryBuilder
# from app.core.exceptions import QueryExecutionException
# from app.utils.logger import setup_logger
#
# logger = setup_logger(__name__)
#
# def get_active_filters_summary(filter_request: GraphFilterRequest) -> List[str]:
#     """Generate summary of active filters
#     Args:
#         filter_request: Filter specifications
#     Returns:
#         List of human-readable filter descriptions
#     """
#     active = []
#
#     if filter_request.node_filter:
#         if filter_request.node_filter.node_types:
#             active.append(f"Type: {', '.join(filter_request.node_filter.node_types)}")
#
#         for pf in filter_request.node_filter.property_filters:
#             active.append(f"{pf.property_name} {pf.operator.value} {pf.value}")
#
#     if filter_request.relationship_filter:
#         if filter_request.relationship_filter.relationship_types:
#             types = ', '.join(filter_request.relationship_filter.relationship_types)
#             active.append(f"Rel: {types}")
#
#     if filter_request.search_query:
#         active.append(f"Search: {filter_request.search_query}")
#
#     return active
#
# class FilterService:
#     """Main service for filtering Neo4j graphs"""
#
#     def __init__(self):
#         self.query_builder = CypherQueryBuilder()
#
#
#
#     def filter_nodes(self, filter_request: GraphFilterRequest) -> List[NodeResponse]:
#         """Filter nodes based on request criteria
#         Args:
#             filter_request: Filter specifications
#         Returns:
#             List of matching nodes
#         """
#         query, params = self.query_builder.build_node_query(filter_request)
#
#         try:
#             with neo4j_service.get_session() as session:
#                 result = session.run(query, params)
#                 nodes = []
#
#                 for record in result:
#                     node_data = dict(record["n"])
#                     nodes.append(NodeResponse(
#                         id=record["node_id"],
#                         labels=record["node_labels"],
#                         properties=node_data
#                     ))
#
#                 logger.info(f"Found {len(nodes)} nodes matching criteria")
#                 return nodes
#
#         except Exception as e:
#             logger.error(f"Node query execution failed: {str(e)}")
#             raise QueryExecutionException(f"Failed to execute node query: {str(e)}")
#
#     def filter_relationships(
#         self,
#         filter_request: GraphFilterRequest
#     ) -> List[RelationshipResponse]:
#         """Filter relationships based on request criteria
#         Args:
#             filter_request: Filter specifications
#         Returns:
#             List of matching relationships
#         """
#         query, params = self.query_builder.build_relationship_query(filter_request)
#
#         try:
#             with neo4j_service.get_session() as session:
#                 result = session.run(query, params)
#                 relationships = []
#
#                 for record in result:
#                     source_data = dict(record["n"])
#                     target_data = dict(record["m"])
#                     rel_data = dict(record["r"])
#
#                     relationships.append(RelationshipResponse(
#                         id=record["rel_id"],
#                         type=record["rel_type"],
#                         source=NodeResponse(
#                             id=record["n"].id,
#                             labels=list(record["n"].labels),
#                             properties=source_data
#                         ),
#                         target=NodeResponse(
#                             id=record["m"].id,
#                             labels=list(record["m"].labels),
#                             properties=target_data
#                         ),
#                         properties=rel_data
#                     ))
#
#                 logger.info(f"Found {len(relationships)} relationships matching criteria")
#                 return relationships
#
#         except Exception as e:
#             logger.error(f"Relationship query execution failed: {str(e)}")
#             raise QueryExecutionException(f"Failed to execute relationship query: {str(e)}")
#
# filter_service = FilterService()