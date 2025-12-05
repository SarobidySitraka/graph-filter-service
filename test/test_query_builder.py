"""Query builder unit tests"""

import pytest
from app.services.query_builder import CypherQueryBuilder
from app.core.models import (
    GraphFilterRequest,
    NodeFilter,
    RelationshipFilter,
    PropertyFilter
)
from app.core.enums import ComparisonOperator, RelationshipDirection

@pytest.fixture
def query_builder():
    """Query builder fixture"""
    return CypherQueryBuilder()


class TestRelationshipPatternBuilding:
    """Test relationship pattern building (FIXED TESTS)"""

    def test_no_relationship_filter(self, query_builder):
        """Test pattern building with no filter"""
        direction, depth = query_builder._build_relationship_pattern(None)
        assert direction == "-"
        assert depth == ""

    def test_outgoing_direction(self, query_builder, relationship_type=None):
        """Test outgoing direction"""
        if relationship_type is None:
            relationship_type = ["SEND_TO"]
        rel_filter = RelationshipFilter(
            relationship_types=relationship_type,
            direction=RelationshipDirection.OUTGOING
        )
        direction, depth = query_builder._build_relationship_pattern(rel_filter)
        assert direction == "->"

    def test_incoming_direction(self, query_builder, relationship_type=None):
        """Test incoming direction"""
        if relationship_type is None:
            relationship_type = ["SEND_TO"]
        rel_filter = RelationshipFilter(
            relationship_types=relationship_type,
            direction=RelationshipDirection.INCOMING
        )
        direction, depth = query_builder._build_relationship_pattern(rel_filter)
        assert direction == "<-"

    def test_both_directions(self, query_builder, relationship_type=None):
        """Test both directions"""
        if relationship_type is None:
            relationship_type = ["SEND_TO"]
        rel_filter = RelationshipFilter(
            relationship_types=relationship_type,
            direction=RelationshipDirection.BOTH
        )
        direction, depth = query_builder._build_relationship_pattern(rel_filter)
        assert direction == "-"

    def test_depth_range_same(self, query_builder,  relationship_type=None):
        """Test depth range when min equals max"""
        if relationship_type is None:
            relationship_type = ["SEND_TO"]
        rel_filter = RelationshipFilter(
            relationship_types=relationship_type,
            min_depth=2,
            max_depth=2
        )
        direction, depth = query_builder._build_relationship_pattern(rel_filter)
        assert depth == "*2"

    def test_depth_range_different(self, query_builder, relationship_type=None):
        """Test depth range when min differs from max"""
        if relationship_type is None:
            relationship_type = ["SEND_TO"]
        rel_filter = RelationshipFilter(
            relationship_types=relationship_type,
            min_depth=1,
            max_depth=3
        )
        direction, depth = query_builder._build_relationship_pattern(rel_filter)
        assert depth == "*1..3"

    def test_depth_range_default(self, query_builder, relationship_type=None):
        """Test depth range with defaults (1,1)"""
        if relationship_type in None:
            relationship_type = ["SEND_TO"]
        rel_filter = RelationshipFilter(
            relationship_types=relationship_type,
            min_depth=1,
            max_depth=1
        )
        direction, depth = query_builder._build_relationship_pattern(rel_filter)
        assert depth == ""  # Single hop, no depth notation needed


class TestCompleteRelationshipQueries:
    """Test complete relationship query building"""

    def test_relationship_query_null_safe(self, query_builder):
        """Test query building handles None relationship_filter"""
        request = GraphFilterRequest(limit=10)
        query, params = query_builder.build_relationship_query(request)

        assert "MATCH (n)-[r" in query
        assert "RETURN n, r, m" in query

    def test_relationship_query_with_all_filters(
        self,
        query_builder,
        node_types=None,
        relationship_type=None,
        property_filters: PropertyFilter = PropertyFilter(
            property_name="OFFICE",
            operator=ComparisonOperator.EQUAL,
            value="21TO"
        )
    ):
        """Test relationship query with all filter types"""
        if relationship_type is None:
            relationship_type = ["SEND_TO", "PROCESSED_BY"]
        if node_types is None:
            node_types = ["OFFICE"]
        request = GraphFilterRequest(
            node_filter=NodeFilter(node_types=node_types),
            relationship_filter=RelationshipFilter(
                relationship_types=relationship_type,
                direction=RelationshipDirection.OUTGOING,
                min_depth=1,
                max_depth=2,
                property_filters=[
                    property_filters,
                ]
            ),
            limit=50
        )

        query, params = query_builder.build_relationship_query(request)

        assert "MATCH (n)-[r:KNOWS|WORKS_WITH*1..2]->(m)" in query
        assert "WHERE" in query
        assert "n:OFFICE" in query
        assert "r.`PROCESSED_BY`" in query
        assert params.get("PROCESSED_BY") == "21TO"

class TestNodeQueries:
    """Test node query building"""

    def test_simple_node_query(self, query_builder):
        """Test basic node query without filters"""
        request = GraphFilterRequest(limit=10)
        query, params = query_builder.build_node_query(request)

        assert "MATCH (n)" in query
        assert "RETURN n" in query
        assert "LIMIT 10" in query

    def test_node_query_with_labels(self, query_builder, node_types=None):
        """Test node query with label filtering"""
        if node_types is None:
            node_types = ["OFFICE"]
        request = GraphFilterRequest(
            node_filter=NodeFilter(node_types=node_types),
            limit=10
        )
        query, params = query_builder.build_node_query(request)

        assert "MATCH (n:OFFICE)" in query

    def test_node_query_with_property_filters(self, query_builder):
        """Test node query with property filters"""
        request = GraphFilterRequest(
            node_filter=NodeFilter(
                node_types=["OFFICE"],
                property_filters=[
                    PropertyFilter(
                        property_name="OFFICE",
                        operator=ComparisonOperator.EQUAL,
                        value="21TO"
                    )
                ]
            ),
            limit=10
        )
        query, params = query_builder.build_node_query(request)

        assert "MATCH (n:OFFICE)" in query
        assert "WHERE" in query
        assert "n.`OFFICE` == 21TO" in query
        assert params["OFFICE"] == "21TO"

    def test_node_query_with_text_search(self, query_builder):
        """Test node query with text search"""
        request = GraphFilterRequest(
            search_query="John",
            limit=10
        )
        query, params = query_builder.build_node_query(request)

        assert "WHERE" in query
        assert "search_query" in params
        assert "(?i).*John.*" in params["search_query"]

    def test_node_query_with_pagination(self, query_builder):
        """Test node query with pagination"""
        request = GraphFilterRequest(skip=20, limit=10)
        query, params = query_builder.build_node_query(request)

        assert "SKIP 20" in query
        assert "LIMIT 10" in query