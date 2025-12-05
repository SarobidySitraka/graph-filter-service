"""
Main filter service orchestrating query building and execution
Updated for Multi-Criteria (Lists)
"""

from typing import List, Any
from app.core.models import (
    GraphFilterRequest,
    NodeResponse,
    RelationshipResponse,
    FilterResponse,
    NodeCriteria,
    RelationshipCriteria
)
from app.services.neo4j_service import neo4j_service
from app.services.query_builder import CypherQueryBuilder
from app.core.exceptions import QueryExecutionException, InvalidFilterException
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def _validate_filter_request(filter_request: GraphFilterRequest) -> None:
    """Validate filter request parameters for lists"""
    
    # Check if we have ANY criteria active
    has_source = len(filter_request.source_nodes) > 0
    has_rels = len(filter_request.relationships) > 0
    has_target = len(filter_request.target_nodes) > 0
    
    has_search = (
            filter_request.search_query is not None and
            filter_request.search_query.strip() != ""
    )

    if not (has_source or has_rels or has_target or has_search):
        raise InvalidFilterException(
            message="At least one filter criterion (Source, Relationship, Target, or Search) must be provided",
            filter_type="request"
        )

    # Validate pagination
    if filter_request.limit < 1:
        raise InvalidFilterException(message="Limit must be at least 1", filter_type="pagination")


class FilterService:
    """Main service for filtering Neo4j graphs"""

    def __init__(self):
        """Initialize filter service with query builder"""
        self.query_builder = CypherQueryBuilder()

    def filter_nodes(self, filter_request: GraphFilterRequest) -> List[NodeResponse]:
        """
        Filter nodes. 
        Note: logic depends on intent. Usually returns 'Source' nodes that match the criteria,
        or nodes matching the full path if relationships are provided.
        """
        _validate_filter_request(filter_request)

        # NOTE: You must update your QueryBuilder to handle the new request structure
        query, params = self.query_builder.build_node_query(filter_request)

        try:
            with neo4j_service.get_session() as session:
                logger.debug(f"Cypher Query:\n{query}")
                result = session.run(query, params)
                nodes = []
                for record in result:
                    # Robust extraction handling different return aliases (n, m, target, etc.)
                    # Defaulting to 'n' as primary node
                    node_obj = record.get("n") or record.get("source") or record[0]
                    
                    nodes.append(NodeResponse(
                        id=node_obj.id, # Neo4j driver native ID access
                        labels=list(node_obj.labels),
                        properties=dict(node_obj)
                    ))

                logger.info(f"Found {len(nodes)} nodes matching criteria")
                return nodes

        except Exception as e:
            logger.error(f"Node query execution failed: {str(e)}")
            raise QueryExecutionException(
                message="Failed to execute node query",
                query=query,
                cypher_error=str(e)
            )

    def filter_relationships(self, filter_request: GraphFilterRequest) -> List[RelationshipResponse]:
        """Filter relationships based on request criteria"""
        _validate_filter_request(filter_request)

        query, params = self.query_builder.build_relationship_query(filter_request)

        try:
            with neo4j_service.get_session() as session:
                result = session.run(query, params)
                relationships = []
                
                for record in result:
                    # Expecting return of r, n (source), m (target)
                    rel = record["r"]
                    source = record["n"]
                    target = record["m"]

                    relationships.append(RelationshipResponse(
                        id=rel.id,
                        type=rel.type,
                        source=NodeResponse(id=source.id, labels=list(source.labels), properties=dict(source)),
                        target=NodeResponse(id=target.id, labels=list(target.labels), properties=dict(target)),
                        properties=dict(rel)
                    ))

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
        Generate human-readable summary dealing with Lists of filters
        """
        active_filters = []

        # 1. Summarize Source Nodes
        for idx, node_filter in enumerate(filter_request.source_nodes):
            prefix = f"Source #{idx+1}"
            if node_filter.node_types:
                active_filters.append(f"{prefix} Types: {', '.join(node_filter.node_types)}")
            
            for pf in node_filter.property_filters:
                active_filters.append(f"{prefix} {pf.property_name} {pf.operator.value} {self._format_value(pf.value)}")

        # 2. Summarize Relationships
        for idx, rel_filter in enumerate(filter_request.relationships):
            prefix = f"Rel #{idx+1}"
            if rel_filter.relationship_types:
                active_filters.append(f"{prefix} Types: {', '.join(rel_filter.relationship_types)}")
            
            if rel_filter.direction:
                active_filters.append(f"{prefix} Dir: {rel_filter.direction.value}")

            for pf in rel_filter.property_filters:
                active_filters.append(f"{prefix} Prop: {pf.property_name} {pf.operator.value} {self._format_value(pf.value)}")

        # 3. Summarize Target Nodes
        for idx, node_filter in enumerate(filter_request.target_nodes):
            prefix = f"Target #{idx+1}"
            if node_filter.node_types:
                active_filters.append(f"{prefix} Types: {', '.join(node_filter.node_types)}")

        # 4. Global Search
        if filter_request.search_query:
            active_filters.append(f"Global Search: {filter_request.search_query}")

        return active_filters

    def filter_nodes_with_count(self, filter_request: GraphFilterRequest) -> FilterResponse:
        nodes = self.filter_nodes(filter_request)
        return FilterResponse(
            total=len(nodes),
            limit=filter_request.limit,
            skip=filter_request.skip,
            data=nodes,
            active_filters=self.get_active_filters_summary(filter_request)
        )

    def filter_relationships_with_count(self, filter_request: GraphFilterRequest) -> FilterResponse:
        relationships = self.filter_relationships(filter_request)
        return FilterResponse(
            total=len(relationships),
            limit=filter_request.limit,
            skip=filter_request.skip,
            data=relationships,
            active_filters=self.get_active_filters_summary(filter_request)
        )

    @staticmethod
    def _format_value(value: Any) -> str:
        if isinstance(value, str) and len(value) > 20:
            return f'"{value[:17]}..."'
        return str(value)

filter_service = FilterService()