"""Unit tests for custom exceptions"""

from app.core.exceptions import (
    Neo4jFilterException,
    InvalidFilterException,
    Neo4jConnectionException,
    QueryExecutionException,
    ValidationException,
    AuthorizationException,
    RateLimitException,
    ResourceNotFoundException,
    TimeoutException,
    ConfigurationException
)


class TestBaseException:
    """Test base exception class"""

    def test_base_exception_creation(self):
        """Test creating base exception"""
        exc = Neo4jFilterException(
            message="Test error",
            status_code=500,
            details={"key": "value"}
        )

        assert exc.message == "Test error"
        assert exc.status_code == 500
        assert exc.details == {"key": "value"}

    def test_to_dict(self):
        """Test exception to dict conversion"""
        exc = Neo4jFilterException(
            message="Test error",
            details={"extra": "info"}
        )

        result = exc.to_dict()

        assert result["error"] == "Neo4jFilterException"
        assert result["message"] == "Test error"
        assert result["status_code"] == 500
        assert result["extra"] == "info"


class TestInvalidFilterException:
    """Test invalid filter exception"""

    def test_with_all_params(self):
        """Test with all parameters"""
        exc = InvalidFilterException(
            message="Invalid operator",
            filter_type="property",
            invalid_field="age",
            invalid_value="not_a_number"
        )

        assert exc.status_code == 400
        assert exc.details["filter_type"] == "property"
        assert exc.details["invalid_field"] == "age"
        assert "not_a_number" in exc.details["invalid_value"]

    def test_minimal_params(self):
        """Test with minimal parameters"""
        exc = InvalidFilterException(message="Invalid filter")

        assert exc.message == "Invalid filter"
        assert exc.status_code == 400


class TestNeo4jConnectionException:
    """Test Neo4j connection exception"""

    def test_uri_sanitization(self):
        """Test URI sanitization removes credentials"""
        exc = Neo4jConnectionException(
            message="Connection failed",
            neo4j_uri="bolt://user:pwd@localhost:7687"
        )

        assert "pwd" not in exc.details["neo4j_uri"]
        assert "localhost:7687" in exc.details["neo4j_uri"]

    def test_status_code(self):
        """Test correct status code"""
        exc = Neo4jConnectionException(message="Connection failed")
        assert exc.status_code == 503


class TestQueryExecutionException:
    """Test query execution exception"""

    def test_query_truncation(self):
        """Test long queries are truncated"""
        long_query = "MATCH (n) " * 100
        exc = QueryExecutionException(
            message="Query failed",
            query=long_query
        )

        assert len(exc.details["query"]) < len(long_query)
        assert "truncated" in exc.details["query"]

    def test_with_error_code(self):
        """Test with Neo4j error code"""
        exc = QueryExecutionException(
            message="Syntax error",
            error_code="Neo.ClientError.Statement.SyntaxError"
        )

        assert exc.details["error_code"] == "Neo.ClientError.Statement.SyntaxError"


class TestValidationException:
    """Test validation exception"""

    def test_field_validation(self):
        """Test field validation details"""
        exc = ValidationException(
            message="Invalid value",
            field_name="limit",
            field_value=10000,
            expected_type="int[1-1000]",
            validation_rule="max_value"
        )

        assert exc.status_code == 422
        assert exc.details["field_name"] == "limit"
        assert exc.details["validation_rule"] == "max_value"


class TestAuthorizationException:
    """Test authorization exception"""

    def test_permission_required(self):
        """Test with required permission"""
        exc = AuthorizationException(
            message="Access denied",
            required_permission="write:nodes"
        )

        assert exc.status_code == 403
        assert exc.details["required_permission"] == "write:nodes"


class TestRateLimitException:
    """Test rate limit exception"""

    def test_with_limits(self):
        """Test with rate limit details"""
        exc = RateLimitException(
            message="Too many requests",
            limit=100,
            reset_time=1234567890
        )

        assert exc.status_code == 429
        assert exc.details["limit"] == 100
        assert exc.details["reset_time"] == 1234567890


class TestResourceNotFoundException:
    """Test resource not found exception"""

    def test_with_resource_details(self):
        """Test with resource details"""
        exc = ResourceNotFoundException(
            message="Node not found",
            resource_type="node",
            resource_id="0001"
        )

        assert exc.status_code == 404
        assert exc.details["resource_type"] == "node"
        assert exc.details["resource_id"] == "0001"


class TestTimeoutException:
    """Test timeout exception"""

    def test_with_timeout_details(self):
        """Test with timeout details"""
        exc = TimeoutException(
            message="Query timeout",
            timeout_seconds=30.0,
            operation="filter_nodes"
        )

        assert exc.status_code == 504
        assert exc.details["timeout_seconds"] == 30.0
        assert exc.details["operation"] == "filter_nodes"


class TestConfigurationException:
    """Test configuration exception"""

    def test_with_config_details(self):
        """Test with configuration details"""
        exc = ConfigurationException(
            message="Invalid config",
            config_key="NEO4J_URI",
            config_value="invalid_uri"
        )

        assert exc.status_code == 500
        assert exc.details["config_key"] == "NEO4J_URI"