"""Cypher query builder updated for Variable Depth support"""

from typing import Dict, Any, Tuple, List
from app.core.models import GraphFilterRequest, PropertyFilter, NodeCriteria, RelationshipCriteria
from app.core.enums import ComparisonOperator, RelationshipDirection
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class CypherQueryBuilder:
    
    @staticmethod
    def _build_property_condition(
        prop_filter: PropertyFilter,
        var_name: str, # e.g., "r" or "n"
        param_prefix: str
    ) -> Tuple[str, Dict[str, Any]]:
        
        safe_prop = prop_filter.property_name.replace(".", "_").replace("-", "_")
        param_key = f"{param_prefix}_{safe_prop}_{prop_filter.operator.name.lower()}"
        
        # Use backticks for property name safety
        prop_ref = f"{var_name}.{prop_filter.property_name}"
        params = {param_key: prop_filter.value}
        condition = ""

        match prop_filter.operator:
            case ComparisonOperator.EQUAL: condition = f"{prop_ref} = ${param_key}"
            case ComparisonOperator.NOT_EQUAL: condition = f"{prop_ref} <> ${param_key}"
            case ComparisonOperator.GREATER: condition = f"{prop_ref} > ${param_key}"
            case ComparisonOperator.GREATER_EQUAL: condition = f"{prop_ref} >= ${param_key}"
            case ComparisonOperator.LESS: condition = f"{prop_ref} < ${param_key}"
            case ComparisonOperator.LESS_EQUAL: condition = f"{prop_ref} <= ${param_key}"
            case ComparisonOperator.CONTAINS: condition = f"{prop_ref} CONTAINS ${param_key}"
            case ComparisonOperator.STARTS_WITH: condition = f"{prop_ref} STARTS WITH ${param_key}"
            case ComparisonOperator.ENDS_WITH: condition = f"{prop_ref} ENDS WITH ${param_key}"
            case ComparisonOperator.IN: condition = f"{prop_ref} IN ${param_key}"
            case ComparisonOperator.NOT_IN: condition = f"NOT {prop_ref} IN ${param_key}"
            case ComparisonOperator.REGEX: condition = f"{prop_ref} =~ ${param_key}"
            case _: condition = f"{prop_ref} = ${param_key}"

        return condition, params

    def _build_node_block(self, criteria: NodeCriteria, var: str, idx: int, prefix: str) -> Tuple[str, Dict]:
        """Build WHERE clause for a node"""
        conds = []
        params = {}
        p_key = f"{prefix}{idx}"

        if criteria.node_types:
            lbl_param = f"{p_key}_labels"
            # Check intersection of labels
            conds.append(f"any(l IN labels({var}) WHERE l IN ${lbl_param})")
            params[lbl_param] = criteria.node_types

        prop_conds = []
        for pf in criteria.property_filters:
            c, p = self._build_property_condition(pf, var, p_key)
            prop_conds.append(c)
            params.update(p)
        
        if prop_conds:
            joiner = f" {criteria.logical_operator.value} "
            conds.append(f"({joiner.join(prop_conds)})")

        if not conds: return "", {}
        return f"({' AND '.join(conds)})", params

    def _build_rel_block_variable(self, criteria: RelationshipCriteria, path_var: str, idx: int) -> Tuple[str, Dict]:
        """
        Build WHERE clause for VARIABLE length path.
        Uses ALL(r in relationships(p) WHERE ...)
        """
        conds = []
        params = {}
        p_key = f"rel{idx}"
        rel_var = "r" # Variable used inside list comprehension

        # 1. Type Check inside list
        if criteria.relationship_types:
            t_param = f"{p_key}_types"
            conds.append(f"type({rel_var}) IN ${t_param}")
            params[t_param] = criteria.relationship_types

        # 2. Properties inside list
        for pf in criteria.property_filters:
            c, p = self._build_property_condition(pf, rel_var, p_key)
            conds.append(c)
            params.update(p)

        # Combine logic for a single relationship in the path
        inner_logic = " AND ".join(conds) if conds else "true"
        
        # Apply to ALL relationships in the path
        full_logic = f"ALL({rel_var} IN relationships({path_var}) WHERE {inner_logic})"
        
        # 3. Length Check (Depth)
        # We add this to the WHERE clause: length(p) >= min AND length(p) <= max
        length_logic = f"(length({path_var}) >= {criteria.min_depth} AND length({path_var}) <= {criteria.max_depth})"
        
        return f"({length_logic} AND {full_logic})", params

    def _build_rel_block_simple(self, criteria: RelationshipCriteria, idx: int) -> Tuple[str, Dict]:
        """Build WHERE clause for SINGLE hop (Standard optimization)"""
        conds = []
        params = {}
        p_key = f"rel{idx}"

        if criteria.relationship_types:
            t_param = f"{p_key}_types"
            conds.append(f"type(r) IN ${t_param}")
            params[t_param] = criteria.relationship_types

        for pf in criteria.property_filters:
            c, p = self._build_property_condition(pf, "r", p_key)
            conds.append(c)
            params.update(p)

        # Direction (Only possible in WHERE for simple match if we used undirected match)
        if criteria.direction == RelationshipDirection.OUTGOING:
            conds.append("startNode(r) = n")
        elif criteria.direction == RelationshipDirection.INCOMING:
            conds.append("endNode(r) = n")

        if not conds: return "", {}
        return f"({' AND '.join(conds)})", params

    def build_node_query(self, req: GraphFilterRequest) -> Tuple[str, Dict]:
        """Source Node Query (Unchanged logic)"""
        params = {}
        wheres = []
        
        # Source Nodes
        if req.source_nodes:
            blocks = []
            for i, c in enumerate(req.source_nodes):
                b, p = self._build_node_block(c, "n", i, "s")
                if b: blocks.append(b); params.update(p)
            if blocks: wheres.append(f"({' OR '.join(blocks)})")
            
        # Search
        if req.search_query:
            params['g_search'] = f"(?i).*{req.search_query}.*"
            wheres.append("(any(l in labels(n) WHERE l =~ $g_search) OR any(k in keys(n) WHERE toString(n[k]) =~ $g_search))")

        query = "MATCH (n)"
        if wheres: query += f"\nWHERE {' AND '.join(wheres)}"
        query += "\nRETURN n, labels(n) as node_labels, id(n) as node_id"
        query += f"\nSKIP {req.skip} LIMIT {req.limit}"
        
        return query, params

    def build_relationship_query(self, req: GraphFilterRequest) -> Tuple[str, Dict]:
        params = {}
        
        # 1. Determine Strategy: Simple vs Variable
        # If ANY criteria has depth != 1, we switch to Variable Path logic for robust handling
        use_variable_path = any(
            (r.min_depth != 1 or r.max_depth != 1) for r in req.relationships
        )

        if use_variable_path:
            # Calculate global bounds for the MATCH pattern optimization
            # e.g. match 1..5, then filter specifically in WHERE
            min_d = min((r.min_depth for r in req.relationships), default=1)
            max_d = max((r.max_depth for r in req.relationships), default=1)
            
            # MATCH p = (n)-[*1..5]-(m)
            query = f"MATCH p = (n)-[*1..{max_d}]-(m)"
            # Note: We hardcode 1 as min in MATCH to avoid missing paths if one filter needs 1 and another 3.
            # Refinement: MATCH p = (n)-[*min_global..max_global]-(m)
        else:
            # Simple Hop Optimization
            query = "MATCH (n)-[r]-(m)"

        wheres = []

        # 2. Source Nodes
        if req.source_nodes:
            blocks = []
            for i, c in enumerate(req.source_nodes):
                b, p = self._build_node_block(c, "n", i, "s")
                if b: blocks.append(b); params.update(p)
            if blocks: wheres.append(f"({' OR '.join(blocks)})")

        # 3. Target Nodes
        if req.target_nodes:
            blocks = []
            for i, c in enumerate(req.target_nodes):
                b, p = self._build_node_block(c, "m", i, "t")
                if b: blocks.append(b); params.update(p)
            if blocks: wheres.append(f"({' OR '.join(blocks)})")

        # 4. Relationships
        if req.relationships:
            blocks = []
            for i, c in enumerate(req.relationships):
                if use_variable_path:
                    b, p = self._build_rel_block_variable(c, "p", i)
                else:
                    b, p = self._build_rel_block_simple(c, i)
                
                if b: blocks.append(b); params.update(p)
            
            if blocks: wheres.append(f"({' OR '.join(blocks)})")

        if wheres: query += f"\nWHERE {' AND '.join(wheres)}"

        if use_variable_path:
            # Return the last relationship in path or the full path? 
            # Frontend expects 'r'. Usually we return the relationship connecting to target, 
            # or we might need to aggregate.
            # For simplicity consistent with `RelationshipResponse`, we return the last relationship `last(relationships(p))`
            # BUT warning: `RelationshipResponse` expects single source/target. 
            # Variable path implies intermediate nodes.
            # We will return the LAST relationship to satisfy the data model strictness.
            query += "\nWITH n, m, p, last(relationships(p)) as r"
            query += "\nRETURN n, r, m, type(r) as rel_type, id(r) as rel_id"
        else:
            query += "\nRETURN n, r, m, type(r) as rel_type, id(r) as rel_id"

        query += f"\nSKIP {req.skip} LIMIT {req.limit}"
        
        logger.debug(f"Built query (Variable={use_variable_path}): {query}")
        return query, params

    def build_count_query(self, req: GraphFilterRequest, q_type: str) -> Tuple[str, Dict]:
        if q_type == 'node':
            base, params = self.build_node_query(req)
        else:
            base, params = self.build_relationship_query(req)
        
        # Strip RETURN and add count
        parts = base.rsplit("\nRETURN", 1)
        return f"{parts[0]}\nRETURN count(*)", params