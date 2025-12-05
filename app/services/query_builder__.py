"""Cypher query builder for constructing Neo4j queries from filters"""

from typing import Dict, Any, Tuple, List, Optional
from app.core.models import (
    GraphFilterRequest, 
    PropertyFilter, 
    NodeCriteria, 
    RelationshipCriteria
)
from app.core.enums import ComparisonOperator, LogicalOperator, RelationshipDirection
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class CypherQueryBuilder:
    """
    Builds Cypher queries from filter objects.
    Updated to support Multi-Node and Multi-Relationship criteria (OR logic between list items).
    """

    @staticmethod
    def _build_property_condition(
        prop_filter: PropertyFilter,
        var_name: str,
        param_prefix: str
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build a Cypher condition for a property filter with unique parameter naming.
        Args:
            prop_filter: Property filter specification
            var_name: Cypher variable (n, r, m)
            param_prefix: Unique prefix to avoid collision (e.g., 's0', 'r1')
        """
        # Create unique parameter key: e.g., "s0_age_gt"
        safe_prop = prop_filter.property_name.replace(".", "_").replace("-", "_")
        param_key = f"{param_prefix}_{safe_prop}"
        
        # Determine operator suffix to ensure uniqueness if same prop is filtered twice
        # (e.g. age > 20 AND age < 50)
        param_key = f"{param_key}_{prop_filter.operator.name.lower()}"
        
        prop_ref = f"{var_name}.{prop_filter.property_name}"
        params = {}

        match prop_filter.operator:
            case ComparisonOperator.EQUAL:
                condition = f"{prop_ref} = ${param_key}"
                params[param_key] = prop_filter.value
            case ComparisonOperator.NOT_EQUAL:
                condition = f"{prop_ref} <> ${param_key}"
                params[param_key] = prop_filter.value
            case ComparisonOperator.GREATER:
                condition = f"{prop_ref} > ${param_key}"
                params[param_key] = prop_filter.value
            case ComparisonOperator.GREATER_EQUAL:
                condition = f"{prop_ref} >= ${param_key}"
                params[param_key] = prop_filter.value
            case ComparisonOperator.LESS:
                condition = f"{prop_ref} < ${param_key}"
                params[param_key] = prop_filter.value
            case ComparisonOperator.LESS_EQUAL:
                condition = f"{prop_ref} <= ${param_key}"
                params[param_key] = prop_filter.value
            case ComparisonOperator.CONTAINS:
                condition = f"{prop_ref} CONTAINS ${param_key}"
                params[param_key] = prop_filter.value
            case ComparisonOperator.STARTS_WITH:
                condition = f"{prop_ref} STARTS WITH ${param_key}"
                params[param_key] = prop_filter.value
            case ComparisonOperator.ENDS_WITH:
                condition = f"{prop_ref} ENDS WITH ${param_key}"
                params[param_key] = prop_filter.value
            case ComparisonOperator.IN:
                condition = f"{prop_ref} IN ${param_key}"
                params[param_key] = prop_filter.value
            case ComparisonOperator.NOT_IN:
                condition = f"NOT {prop_ref} IN ${param_key}"
                params[param_key] = prop_filter.value
            case ComparisonOperator.REGEX:
                condition = f"{prop_ref} =~ ${param_key}"
                params[param_key] = prop_filter.value
            case _:
                # Default fallback
                condition = f"{prop_ref} = ${param_key}"
                params[param_key] = prop_filter.value

        return condition, params

    def _build_node_criteria_block(
        self, 
        criteria: NodeCriteria, 
        var_name: str, 
        idx: int,
        prefix_char: str
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Builds a WHERE clause block for a SINGLE node criteria item.
        Ex: (n:Person AND n.age > 25)
        """
        conditions = []
        params = {}
        unique_prefix = f"{prefix_char}{idx}"

        # 1. Label check
        if criteria.node_types:
            # Cypher optimization: Using labels(n) is slower than direct matching, 
            # but needed for dynamic OR logic in WHERE clause.
            # Best practice: Check if any of the requested labels exist on node
            # labels(n) returns a list. We check intersection.
            labels_param = f"{unique_prefix}_labels"
            
            # Logic: Node must have AT LEAST one of the specified labels (OR logic)
            # OR Node must have ALL? Usually filters imply specific type.
            # Assuming "Node is Type A OR Type B" -> ANY
            
            # Optimized approach: "n:Label" is not possible in dynamic WHERE OR.
            # We use: any(l in labels(n) WHERE l IN $param)
            conditions.append(f"any(l IN labels({var_name}) WHERE l IN ${labels_param})")
            params[labels_param] = criteria.node_types

        # 2. Properties
        prop_conditions = []
        for prop_filter in criteria.property_filters:
            cond, p = self._build_property_condition(prop_filter, var_name, unique_prefix)
            prop_conditions.append(cond)
            params.update(p)

        if prop_conditions:
            # Logical operator (AND/OR) between properties of the SAME node filter
            op = f" {criteria.logical_operator.value} "
            conditions.append(f"({op.join(prop_conditions)})")

        if not conditions:
            return "", {}

        return f"({' AND '.join(conditions)})", params

    def _build_rel_criteria_block(
        self,
        criteria: RelationshipCriteria,
        idx: int
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Builds a WHERE clause block for a SINGLE relationship criteria item.
        Handles Type, Properties, and Direction manually.
        """
        conditions = []
        params = {}
        unique_prefix = f"rel{idx}"

        # 1. Type check
        if criteria.relationship_types:
            types_param = f"{unique_prefix}_types"
            conditions.append(f"type(r) IN ${types_param}")
            params[types_param] = criteria.relationship_types

        # 2. Properties
        for prop_filter in criteria.property_filters:
            cond, p = self._build_property_condition(prop_filter, "r", unique_prefix)
            conditions.append(cond)
            params.update(p)

        # 3. Direction Check (Crucial because MATCH is undirected)
        # Standard: (n)-[r]-(m)
        # Outgoing (n->m): startNode(r) = n
        # Incoming (n<-m): endNode(r) = n
        if criteria.direction:
            if criteria.direction == RelationshipDirection.OUTGOING:
                conditions.append("startNode(r) = n")
            elif criteria.direction == RelationshipDirection.INCOMING:
                conditions.append("endNode(r) = n")
            # RelationshipDirection.BOTH implied by default

        if not conditions:
            return "", {}

        return f"({' AND '.join(conditions)})", params

    def build_node_query(self, filter_request: GraphFilterRequest) -> Tuple[str, Dict[str, Any]]:
        """
        Builds query for Source Nodes filtering.
        Logic: Matches 'n' where 'n' fits (SourceCriteria #1 OR SourceCriteria #2 ...)
        """
        params = {}
        criteria_blocks = []

        # We start with a generic match
        query = "MATCH (n)"
        
        # Build Source Node blocks
        if filter_request.source_nodes:
            for i, criteria in enumerate(filter_request.source_nodes):
                block_str, block_params = self._build_node_criteria_block(criteria, "n", i, "s")
                if block_str:
                    criteria_blocks.append(block_str)
                    params.update(block_params)

        # Global Search (Text)
        search_block = ""
        if filter_request.search_query and filter_request.search_query.strip():
            params['global_search'] = f"(?i).*{filter_request.search_query}.*"
            search_parts = [
                "any(label IN labels(n) WHERE label =~ $global_search)",
                "any(key IN keys(n) WHERE toString(n[key]) =~ $global_search)"
            ]
            search_block = f"({' OR '.join(search_parts)})"

        # Assemble WHERE
        where_clauses = []
        
        # Combine Source Criteria with OR
        if criteria_blocks:
            where_clauses.append(f"({' OR '.join(criteria_blocks)})")
        
        # Add Search with AND
        if search_block:
            where_clauses.append(search_block)

        if where_clauses:
            query += f"\nWHERE {' AND '.join(where_clauses)}"

        query += "\nRETURN n, labels(n) as node_labels, id(n) as node_id"
        query += f"\nSKIP {filter_request.skip} LIMIT {filter_request.limit}"

        logger.debug(f"Built node query: {query}")
        return query, params

    def build_relationship_query(self, filter_request: GraphFilterRequest) -> Tuple[str, Dict[str, Any]]:
        """
        Builds query for Source -> Rel -> Target.
        Logic: MATCH (n)-[r]-(m)
        WHERE (n matches Sources)
        AND (m matches Targets)
        AND (r matches Rels)
        """
        params = {}
        
        # 1. Base Match (Undirected to allow flexible direction filtering in WHERE)
        # We use variable length path if min/max depth > 1, but complex WHERE on properties 
        # is difficult on variable paths. 
        # Simplified: Assuming depth 1 for property filtering support on 'r'. 
        # If variable depth is needed, syntax changes significantly.
        # Assuming standard single hop for detailed filtering.
        query = "MATCH (n)-[r]-(m)"

        where_parts = []

        # 2. Source Node Logic (n)
        source_blocks = []
        if filter_request.source_nodes:
            for i, criteria in enumerate(filter_request.source_nodes):
                block, p = self._build_node_criteria_block(criteria, "n", i, "s")
                if block:
                    source_blocks.append(block)
                    params.update(p)
            
            if source_blocks:
                where_parts.append(f"({' OR '.join(source_blocks)})")

        # 3. Target Node Logic (m)
        target_blocks = []
        if filter_request.target_nodes:
            for i, criteria in enumerate(filter_request.target_nodes):
                block, p = self._build_node_criteria_block(criteria, "m", i, "t")
                if block:
                    target_blocks.append(block)
                    params.update(p)
            
            if target_blocks:
                where_parts.append(f"({' OR '.join(target_blocks)})")

        # 4. Relationship Logic (r)
        rel_blocks = []
        if filter_request.relationships:
            for i, criteria in enumerate(filter_request.relationships):
                block, p = self._build_rel_criteria_block(criteria, i)
                if block:
                    rel_blocks.append(block)
                    params.update(p)
            
            if rel_blocks:
                where_parts.append(f"({' OR '.join(rel_blocks)})")

        # 5. Assemble Query
        if where_parts:
            query += f"\nWHERE {' AND '.join(where_parts)}"

        # 6. Return
        query += "\nRETURN n, r, m, type(r) as rel_type, id(r) as rel_id"
        query += f"\nSKIP {filter_request.skip} LIMIT {filter_request.limit}"

        logger.debug(f"Built relationship query: {query}")
        logger.debug(f"Params: {params}")
        
        return query, params

    def build_count_query(
        self,
        filter_request: GraphFilterRequest,
        query_type: str
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build a count query to get total results before pagination
        """
        if query_type == 'node':
            base_query, params = self.build_node_query(filter_request)
        else:
            base_query, params = self.build_relationship_query(filter_request)

        # Remove RETURN clause and pagination, add count
        query_parts = base_query.split("\nRETURN")[0]
        count_query = query_parts + "\nRETURN count(*) as total"

        return count_query, params