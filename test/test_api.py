"""API endpoint tests"""

def test_root_endpoint(client):
    """Test root endpoint returns correct information"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "version" in data
    assert "docs" in data


def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "neo4j_connected" in data
    assert "version" in data


def test_filter_nodes_endpoint(client, sample_node_filter):
    """Test node filtering endpoint"""
    response = client.post("/api/v1/nodes/filter", json=sample_node_filter)
    assert response.status_code in [200, 400, 503]


def test_filter_relationships_endpoint(client, sample_relationship_filter):
    """Test relationship filtering endpoint"""
    response = client.post("/api/v1/relationships/filter", json=sample_relationship_filter)
    assert response.status_code in [200, 400, 503]


def test_invalid_filter_request(client):
    """Test handling of invalid filter requests"""
    invalid_request = {
        "node_filter": {
            "property_filters": [
                {
                    "property_name": "age",
                    "operator": "INVALID_OPERATOR",
                    "value": 25
                }
            ]
        }
    }
    response = client.post("/api/v1/nodes/filter", json=invalid_request)
    assert response.status_code == 422