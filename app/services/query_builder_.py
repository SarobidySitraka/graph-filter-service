"""Cypher query builder for constructing Neo4j queries from filters"""

from typing import Dict, Any, Tuple, Optional
from app.core.models import GraphFilterRequest, PropertyFilter, RelationshipFilter
from app.core.enums import ComparisonOperator, LogicalOperator, RelationshipDirection
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class CypherQueryBuilder:
    """Builds Cypher queries from filter objects"""

    @staticmethod
    def _build_property_condition(
        prop_filter: PropertyFilter,
        var_name: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Build a Cypher condition for a property filter
        Args:
            prop_filter: Property filter specification
            var_name: Variable name in Cypher query(e.g., 'n', 'r')
        Returns:
            Tuple of(condition_string, parameters_dict)
        """
        # Use backticks to handle special characters in property names
        param_key = f"{prop_filter.property_name}".replace(".", "_").replace("-", "_")
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
                raise ValueError(f"Unsupported operator: {prop_filter.operator}")

        return condition, params


    @staticmethod
    def _build_relationship_pattern(rel_filter: Optional[RelationshipFilter]) -> Tuple[str, str]:
        """
        Build relationship pattern and depth range
        Args:
            rel_filter: Relationship filter specification
        Returns:
            Tuple of(direction_arrow, depth_range)
        """
        direction_arrow = "-"
        depth_range = ""

        if rel_filter is None:
            return direction_arrow, depth_range

        # Determine direction
        if rel_filter.direction == RelationshipDirection.OUTGOING:
            direction_arrow = "->"
        elif rel_filter.direction == RelationshipDirection.INCOMING:
            direction_arrow = "<-"
        else:
            direction_arrow = "-"  # Both directions

        # Determine depth range
        min_depth = rel_filter.min_depth
        max_depth = rel_filter.max_depth

        if min_depth == max_depth:
            depth_range = f"*{min_depth}" if min_depth > 1 else ""
        else:
            depth_range = f"*{min_depth}..{max_depth}"

        return direction_arrow, depth_range


    def build_node_query(self, filter_request: GraphFilterRequest) -> Tuple[str, Dict[str, Any]]:
        """
        Build a Cypher query for node filtering
        Args:
            filter_request: Complete filter specification
        Returns:
            Tuple of(cypher_query, parameters)
        """
        params = {}
        conditions = []

        # Build node pattern with labels
        node_labels = ""
        if filter_request.node_filter is not None:
            if filter_request.node_filter.node_types:
                node_labels = ":" + ":".join(filter_request.node_filter.node_types)

        query = f"MATCH (n{node_labels})"

        # Add property filters
        if filter_request.node_filter is not None:
            if filter_request.node_filter.property_filters:
                for prop_filter in filter_request.node_filter.property_filters:
                    condition, prop_params = self._build_property_condition(prop_filter, "n")
                    conditions.append(condition)
                    params.update(prop_params)

        # Add text search
        if filter_request.search_query is not None and filter_request.search_query.strip():
            search_conditions = []
            params['search_query'] = f"(?i).*{filter_request.search_query}.*"

            # Search in labels
            search_conditions.append("any(label IN labels(n) WHERE label =~ $search_query)")

            # Search in property values
            search_conditions.append(
                "any(key IN keys(n) WHERE toString(n[key]) =~ $search_query)"
            )

            conditions.append(f"({' OR '.join(search_conditions)})")

        # Combine conditions with logical operator
        if conditions:
            logical_op = " AND "
            if (filter_request.node_filter is not None and
                    filter_request.node_filter.logical_operator == LogicalOperator.OR):
                logical_op = " OR "
            query += f"\nWHERE {logical_op.join(conditions)}"

        # Return clause
        query += "\nRETURN n, labels(n) as node_labels, id(n) as node_id"

        # Pagination
        query += f"\nSKIP {filter_request.skip} LIMIT {filter_request.limit}"

        logger.debug(f"Built node query: {query}")
        logger.debug(f"Query parameters: {params}")

        return query, params


    def build_relationship_query(
        self,
        filter_request: GraphFilterRequest
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build a Cypher query for relationship filtering FIXED: Proper attribute access handling
        Args:
            filter_request: Complete filter specification
        Returns:
            Tuple of(cypher_query, parameters)
        """
        params = {}
        conditions = []

        # Build relationship type pattern
        rel_types = ""
        if filter_request.relationship_filter is not None:
            if filter_request.relationship_filter.relationship_types:
                rel_types = "|".join(filter_request.relationship_filter.relationship_types)

        # Get direction and depth using helper method
        direction_arrow, depth_range = self._build_relationship_pattern(
            filter_request.relationship_filter
        )

        # Build relationship pattern based on direction
        if direction_arrow == "->":
            rel_pattern = f"-[r:{rel_types}{depth_range}]->"
        elif direction_arrow == "<-":
            rel_pattern = f"<-[r:{rel_types}{depth_range}]-"
        else:
            rel_pattern = f"-[r:{rel_types}{depth_range}]-"

        query = f"MATCH (n){rel_pattern}(m)"

        # Add node type filter for source node
        if filter_request.node_filter is not None:
            if filter_request.node_filter.node_types:
                node_labels = ":" + ":".join(filter_request.node_filter.node_types)
                conditions.append(f"n{node_labels}")

        # Add relationship property filters
        if filter_request.relationship_filter is not None:
            if filter_request.relationship_filter.property_filters:
                for prop_filter in filter_request.relationship_filter.property_filters:
                    condition, prop_params = self._build_property_condition(prop_filter, "r")
                    conditions.append(condition)
                    params.update(prop_params)

        # Combine conditions
        if conditions:
            query += f"\nWHERE {' AND '.join(conditions)}"

        # Return clause
        query += "\nRETURN n, r, m, type(r) as rel_type, id(r) as rel_id"

        # Pagination
        query += f"\nSKIP {filter_request.skip} LIMIT {filter_request.limit}"

        logger.debug(f"Built relationship query: {query}")
        logger.debug(f"Query parameters: {params}")

        return query, params


    def build_count_query(
        self,
        filter_request: GraphFilterRequest,
        query_type: str
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build a count query to get total results before pagination
        Args:
            filter_request: Complete filter specification
            query_type: Either 'node' or 'relationship'
        Returns:
            Tuple of(cypher_query, parameters)
        """
        if query_type == 'node':
            base_query, params = self.build_node_query(filter_request)
        else:
            base_query, params = self.build_relationship_query(filter_request)

        # Remove RETURN clause and pagination, add count
        query_parts = base_query.split("\nRETURN")[0]
        count_query = query_parts + "\nRETURN count(*) as total"

        return count_query, params


# """Cypher query builder for constructing Neo4j queries from filters"""
#
# from typing import Dict, Any, Tuple
# from app.core.models import GraphFilterRequest, PropertyFilter
# from app.core.enums import ComparisonOperator, LogicalOperator, RelationshipDirection
# from app.utils.logger import setup_logger
#
# logger = setup_logger(__name__)
#
# class CypherQueryBuilder:
#     """Builds Cypher queries from filter objects"""
#
#     @staticmethod
#     def _build_property_condition(
#         prop_filter: PropertyFilter,
#         var_name: str
#     ) -> Tuple[str, Dict[str, Any]]:
#         """Build a Cypher condition for a property filter
#         Args:
#             prop_filter: Property filter specification
#             var_name: Variable name in Cypher query(e.g., 'n', 'r')
#         Returns:
#             Tuple of(condition_string, parameters_dict)
#         """
#         param_key = f"{var_name}_{prop_filter.property_name}".replace(".", "_")
#         prop_ref = f"{var_name}.`{prop_filter.property_name}`"
#         params = {}
#
#         match prop_filter.operator:
#             case ComparisonOperator.EQUAL:
#                 condition = f"{prop_ref} = ${param_key}"
#                 params[param_key] = prop_filter.value
#
#             case ComparisonOperator.NOT_EQUAL:
#                 condition = f"{prop_ref} <> ${param_key}"
#                 params[param_key] = prop_filter.value
#
#             case ComparisonOperator.GREATER:
#                 condition = f"{prop_ref} > ${param_key}"
#                 params[param_key] = prop_filter.value
#
#             case ComparisonOperator.GREATER_EQUAL:
#                 condition = f"{prop_ref} >= ${param_key}"
#                 params[param_key] = prop_filter.value
#
#             case ComparisonOperator.LESS:
#                 condition = f"{prop_ref} < ${param_key}"
#                 params[param_key] = prop_filter.value
#
#             case ComparisonOperator.LESS_EQUAL:
#                 condition = f"{prop_ref} <= ${param_key}"
#                 params[param_key] = prop_filter.value
#
#             case ComparisonOperator.CONTAINS:
#                 condition = f"{prop_ref} CONTAINS ${param_key}"
#                 params[param_key] = prop_filter.value
#
#             case ComparisonOperator.STARTS_WITH:
#                 condition = f"{prop_ref} STARTS WITH ${param_key}"
#                 params[param_key] = prop_filter.value
#
#             case ComparisonOperator.ENDS_WITH:
#                 condition = f"{prop_ref} ENDS WITH ${param_key}"
#                 params[param_key] = prop_filter.value
#
#             case ComparisonOperator.IN:
#                 condition = f"{prop_ref} IN ${param_key}"
#                 params[param_key] = prop_filter.value
#
#             case ComparisonOperator.NOT_IN:
#                 condition = f"NOT {prop_ref} IN ${param_key}"
#                 params[param_key] = prop_filter.value
#
#             case ComparisonOperator.REGEX:
#                 condition = f"{prop_ref} =~ ${param_key}"
#                 params[param_key] = prop_filter.value
#
#             case _:
#                 raise ValueError(f"Unsupported operator: {prop_filter.operator}")
#
#         return condition, params
#
#
#     def build_node_query(self, filter_request: GraphFilterRequest) -> Tuple[str, Dict[str, Any]]:
#         """
#         Build a Cypher query for node filtering
#         Args:
#             filter_request: Complete filter specification
#         Returns:
#             Tuple of(cypher_query, parameters)
#         """
#         params = {}
#         conditions = []
#
#         node_labels = ""
#         if filter_request.node_filter and filter_request.node_filter.node_types:
#             node_labels = ":" + ":".join(filter_request.node_filter.node_types)
#
#         query = f"MATCH (n{node_labels})"
#
#         if filter_request.node_filter and filter_request.node_filter.property_filters:
#             for prop_filter in filter_request.node_filter.property_filters:
#                 condition, prop_params = self._build_property_condition(prop_filter, "n")
#                 conditions.append(condition)
#                 params.update(prop_params)
#
#         if filter_request.search_query:
#             search_conditions = []
#             params['search_query'] = f"(?i).*{filter_request.search_query}.*"
#             search_conditions.append("any(label IN labels(n) WHERE label =~ $search_query)")
#             search_conditions.append("any(key IN keys(n) WHERE toString(n[key]) =~ $search_query)")
#             conditions.append(f"({' OR '.join(search_conditions)})")
#
#         if conditions:
#             logical_op = " AND "
#             if (filter_request.node_filter and
#                     filter_request.node_filter.logical_operator == LogicalOperator.OR):
#                 logical_op = " OR "
#             query += f"\\nWHERE {logical_op.join(conditions)}"
#
#         query += "\\nRETURN n, labels(n) as node_labels, id(n) as node_id"
#         query += f"\\nSKIP {filter_request.skip} LIMIT {filter_request.limit}"
#
#         logger.debug(f"Built node query: {query}")
#         return query, params
#
#
#     def build_relationship_query(self, filter_request: GraphFilterRequest) -> Tuple[str, Dict[str, Any]]:
#         """Build a Cypher query for relationship filtering"""
#         params = {}
#         conditions = []
#
#         rel_types = ""
#         if (filter_request.relationship_filter and
#                 filter_request.relationship_filter.relationship_types):
#             rel_types = "|".join(filter_request.relationship_filter.relationship_types)
#
#         direction_arrow = "-"
#         depth_range = ""
#
#         if filter_request.relationship_filter:
#             rf = filter_request.relationship_filter
#             if rf.direction == RelationshipDirection.OUTGOING:
#                 direction_arrow = "->"
#             elif rf.direction == RelationshipDirection.INCOMING:
#                 direction_arrow = "<-"
#
#             if rf.min_depth == rf.max_depth:
#                 depth_range = f"*{rf.min_depth}"
#             else:
#                 depth_range = f"*{rf.min_depth}..{rf.max_depth}"
#
#         if direction_arrow == "->":
#             rel_pattern = f"-[r:{rel_types}{depth_range}]->"
#         elif direction_arrow == "<-":
#             rel_pattern = f"<-[r:{rel_types}{depth_range}]-"
#         else:
#             rel_pattern = f"-[r:{rel_types}{depth_range}]-"
#
#         query = f"MATCH (n){rel_pattern}(m)"
#
#         if filter_request.node_filter and filter_request.node_filter.node_types:
#             node_labels = ":" + ":".join(filter_request.node_filter.node_types)
#             conditions.append(f"n{node_labels}")
#
#         if (filter_request.relationship_filter and
#                 filter_request.relationship_filter.property_filters):
#             for prop_filter in filter_request.relationship_filter.property_filters:
#                 condition, prop_params = self._build_property_condition(prop_filter, "r")
#                 conditions.append(condition)
#                 params.update(prop_params)
#
#         if conditions:
#             query += f"\\nWHERE {' AND '.join(conditions)}"
#
#         query += "\\nRETURN n, r, m, type(r) as rel_type, id(r) as rel_id"
#         query += f"\\nSKIP {filter_request.skip} LIMIT {filter_request.limit}"
#
#         logger.debug(f"Built relationship query: {query}")
#         return query, params
#
#
# # """Cypher query builder for constructing Neo4j queries from filters"""
# #
# # from typing import Dict, Any, Tuple
# # from app.core.models import GraphFilterRequest, PropertyFilter
# # from app.core.enums import ComparisonOperator, LogicalOperator, RelationshipDirection
# # from app.utils.logger import setup_logger
# #
# # logger = setup_logger(__name__)
# #
# # class CypherQueryBuilder:
# #     """Builds Cypher queries from filter objects"""
# #
# #     @staticmethod
# #     def _build_property_condition(
# #         prop_filter: PropertyFilter,
# #         var_name: str
# #     ) -> Tuple[str, Dict[str, Any]]:
# #         """Build a Cypher condition for a property filter
# #
# #         Args:
# #             prop_filter: Property filter specification
# #             var_name: Variable name in Cypher query(e.g., 'n', 'r')
# #
# #             Returns:
# #             Tuple
# #             of(condition_string, parameters_dict)
# #
# #         """
# #         param_key = f"{var_name}_{prop_filter.property_name}".replace(".", "_")
# #         prop_ref = f"{var_name}.{prop_filter.property_name}"
# #         params = {}
# #
# #         match prop_filter.operator:
# #             case ComparisonOperator.EQUAL:
# #                 condition = f"{prop_ref} = ${param_key}"
# #                 params[param_key] = prop_filter.value
# #
# #             case ComparisonOperator.NOT_EQUAL:
# #                 condition = f"{prop_ref} <> ${param_key}"
# #                 params[param_key] = prop_filter.value
# #
# #             case ComparisonOperator.GREATER:
# #                 condition = f"{prop_ref} > ${param_key}"
# #                 params[param_key] = prop_filter.value
# #
# #             case ComparisonOperator.GREATER_EQUAL:
# #                 condition = f"{prop_ref} >= ${param_key}"
# #                 params[param_key] = prop_filter.value
# #
# #             case ComparisonOperator.LESS:
# #                 condition = f"{prop_ref} < ${param_key}"
# #                 params[param_key] = prop_filter.value
# #
# #             case ComparisonOperator.LESS_EQUAL:
# #                 condition = f"{prop_ref} <= ${param_key}"
# #                 params[param_key] = prop_filter.value
# #
# #             case ComparisonOperator.CONTAINS:
# #                 condition = f"{prop_ref} CONTAINS ${param_key}"
# #                 params[param_key] = prop_filter.value
# #
# #             case ComparisonOperator.STARTS_WITH:
# #                 condition = f"{prop_ref} STARTS WITH ${param_key}"
# #                 params[param_key] = prop_filter.value
# #
# #             case ComparisonOperator.ENDS_WITH:
# #                 condition = f"{prop_ref} ENDS WITH ${param_key}"
# #                 params[param_key] = prop_filter.value
# #
# #             case ComparisonOperator.IN:
# #                 condition = f"{prop_ref} IN ${param_key}"
# #                 params[param_key] = prop_filter.value
# #
# #             case ComparisonOperator.NOT_IN:
# #                 condition = f"NOT {prop_ref} IN ${param_key}"
# #                 params[param_key] = prop_filter.value
# #
# #             case ComparisonOperator.REGEX:
# #                 condition = f"{prop_ref} =~ ${param_key}"
# #                 params[param_key] = prop_filter.value
# #
# #             case _:
# #                 raise ValueError(f"Unsupported operator: {prop_filter.operator}")
# #
# #         return condition, params
# #
# #     def build_node_query(self, filter_request: GraphFilterRequest) -> Tuple[str, Dict[str, Any]]:
# #         """
# #         Build a Cypher query for node filtering
# #
# #         Args:
# #             filter_request: Complete filter specification
# #
# #         Returns:
# #             Tuple of(cypher_query, parameters)
# #         """
# #         params = {}
# #         conditions = []
# #
# #         # Build node pattern with labels
# #         node_labels = ""
# #         if filter_request.node_filter and filter_request.node_filter.node_types:
# #             node_labels = ":" + ":".join(filter_request.node_filter.node_types)
# #
# #         query = f"MATCH (n{node_labels})"
# #
# #         # Add property filters
# #         if filter_request.node_filter and filter_request.node_filter.property_filters:
# #             for prop_filter in filter_request.node_filter.property_filters:
# #                 condition, prop_params = self._build_property_condition(prop_filter, "n")
# #                 conditions.append(condition)
# #                 params.update(prop_params)
# #
# #         # Add text search
# #         if filter_request.search_query:
# #             search_conditions = []
# #             params['search_query'] = f"(?i).*{filter_request.search_query}.*"
# #
# #             # Search in labels
# #             search_conditions.append("any(label IN labels(n) WHERE label =~ $search_query)")
# #
# #             # Search in property values
# #             search_conditions.append(
# #                 "any(key IN keys(n) WHERE toString(n[key]) =~ $search_query)"
# #             )
# #
# #             conditions.append(f"({' OR '.join(search_conditions)})")
# #
# #         # Combine conditions with logical operator
# #         if conditions:
# #             logical_op = " AND "
# #             if (filter_request.node_filter and
# #                     filter_request.node_filter.logical_operator == LogicalOperator.OR):
# #                 logical_op = " OR "
# #             query += f"\\nWHERE {logical_op.join(conditions)}"
# #
# #         # Return clause
# #         query += "\\nRETURN n, labels(n) as node_labels, id(n) as node_id"
# #
# #         # Pagination
# #         query += f"\\nSKIP {filter_request.skip} LIMIT {filter_request.limit}"
# #
# #         logger.debug(f"Built node query: {query}")
# #         logger.debug(f"Query parameters: {params}")
# #
# #         return query, params
# #
# #     def build_relationship_query(
# #             self,
# #             filter_request: GraphFilterRequest
# #     ) -> Tuple[str, Dict[str, Any]]:
# #         """
# #         Build a Cypher query for relationship filtering
# #
# #         Args:
# #         filter_request: Complete filter specification
# #
# #         Returns:
# #             Tuple of(cypher_query, parameters)
# #         """
# #         params = {}
# #         conditions = []
# #
# #         # Build relationship type pattern
# #         rel_types = ""
# #         if (filter_request.relationship_filter and
# #                 filter_request.relationship_filter.relationship_types):
# #             rel_types = "|".join(filter_request.relationship_filter.relationship_types)
# #
# #         # Determine direction and depth
# #         direction_arrow = "-"
# #         depth_range = ""
# #
# #         if filter_request.relationship_filter:
# #             rf = filter_request.relationship_filter
# #
# #             # Set direction
# #             if rf.direction == RelationshipDirection.OUTGOING:
# #                 direction_arrow = "->"
# #             elif rf.direction == RelationshipDirection.INCOMING:
# #                 direction_arrow = "<-"
# #
# #             # Set depth range
# #             if rf.min_depth == rf.max_depth:
# #                 depth_range = f"*{rf.min_depth}"
# #             else:
# #                 depth_range = f"*{rf.min_depth}..{rf.max_depth}"
# #
# #         # Build relationship pattern
# #         if direction_arrow == "->":
# #             rel_pattern = f"-[r:{rel_types}{depth_range}]->"
# #         elif direction_arrow == "<-":
# #             rel_pattern = f"<-[r:{rel_types}{depth_range}]-"
# #         else:
# #             rel_pattern = f"-[r:{rel_types}{depth_range}]-"
# #
# #         query = f"MATCH (n){rel_pattern}(m)"
# #
# #         # Add node type filter
# #         if filter_request.node_filter and filter_request.node_filter.node_types:
# #             node_labels = ":" + ":".join(filter_request.node_filter.node_types)
# #             conditions.append(f"n{node_labels}")
# #
# #         # Add relationship property filters
# #         if filter_request.relationship_filter and filter_request.relationship_filter.property_filters:
# #             for prop_filter in filter_request.relationship_filter.property_filters:
# #                 condition, prop_params = self._build_property_condition(prop_filter, "r")
# #                 conditions.append(condition)
# #                 params.update(prop_params)
# #
# #         # Combine conditions
# #         if conditions:
# #             query += f"\\nWHERE {' AND '.join(conditions)}"
# #
# #         # Return clause
# #         query += "\\nRETURN n, r, m, type(r) as rel_type, id(r) as rel_id"
# #
# #         # Pagination
# #         query += f"\\nSKIP {filter_request.skip} LIMIT {filter_request.limit}"
# #
# #         logger.debug(f"Built relationship query: {query}")
# #         logger.debug(f"Query parameters: {params}")
# #
# #         return query, params
# #
# #
# #     def build_count_query(self, filter_request: GraphFilterRequest, query_type: str) -> Tuple[str, Dict[str, Any]]:
# #         """
# #         Build a count query to get total results before pagination
# #
# #         Args:
# #             filter_request: Complete filter specification
# #             query_type: Either 'node' or 'relationship'
# #
# #         Returns:
# #             Tuple of(cypher_query, parameters)
# #         """
# #         if query_type == 'node':
# #             base_query, params = self.build_node_query(filter_request)
# #         else:
# #             base_query, params = self.build_relationship_query(filter_request)
# #
# #         # Remove RETURN clause and pagination
# #         query_parts = base_query.split("\\nRETURN")[0]
# #         count_query = query_parts + "\\nRETURN count(*) as total"
# #
# #         return count_query, params