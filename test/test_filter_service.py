"""Filter service integration tests"""

import pytest
from app.services.filter_service import FilterService
from app.core.models import (
    GraphFilterRequest,
    NodeFilter,
    PropertyFilter
)
from app.core.enums import ComparisonOperator

@pytest.fixture
def filter_service():
    """Filter service fixture"""
    return FilterService()

class TestActiveFiltersSummary:
    """Test active filters summary generation"""

    def test_empty_filters(self, filter_service):
        """Test summary with no filters"""
        request = GraphFilterRequest(limit=10)
        summary = filter_service.get_active_filters_summary(request)

        assert isinstance(summary, list)
        assert len(summary) == 0

    def test_node_type_filter(self, filter_service):
        """Test summary with node type filter"""
        request = GraphFilterRequest(
            node_filter=NodeFilter(node_types=["Person", "Employee"]),
            limit=10
        )
        summary = filter_service.get_active_filters_summary(request)

        assert len(summary) > 0
        assert any("Person" in s for s in summary)

    def test_property_filter(self, filter_service):
        """Test summary with property filter"""
        request = GraphFilterRequest(
            node_filter=NodeFilter(
                property_filters=[
                    PropertyFilter(
                        property_name="age",
                        operator=ComparisonOperator.GREATER,
                        value=25
                    )
                ]
            ),
            limit=10
        )
        summary = filter_service.get_active_filters_summary(request)

        assert len(summary) > 0
        assert any("age" in s for s in summary)

    def test_search_query_filter(self, filter_service):
        """Test summary with search query"""
        request = GraphFilterRequest(
            search_query="John Doe",
            limit=10
        )
        summary = filter_service.get_active_filters_summary(request)

        assert len(summary) > 0
        assert any("Search" in s for s in summary)