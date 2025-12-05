"""Pytest configuration and fixtures"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    """FastAPI test client fixture"""
    return TestClient(app)


@pytest.fixture
def sample_node_filter():
    """Sample node filter for testing"""
    return {
        "node_filter": {
            "node_types": ["OFFICE"],
            "property_filters": [
                {
                    "property_name": "OFFICE",
                    "operator": "==",
                    "value": "21TO"
                }
            ],
            "logical_operator": "AND"
        },
        "limit": 10
    }


@pytest.fixture
def sample_relationship_filter():
    """Sample relationship filter for testing"""
    return {
        "relationship_filter": {
            "relationship_types": ["SEND_TO"],
            "direction": "outgoing",
            "min_depth": 1,
            "max_depth": 2
        },
        "limit": 10
    }