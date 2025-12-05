"""Custom exception definitions with detailed error handling"""

from typing import Any, Dict, Optional
from fastapi import status


class Neo4jFilterException(Exception):
    """
    Base exception for Neo4j filter service
    All custom exceptions inherit from this class
    """
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize base exception
        
        Args:
            message: Human-readable error message
            status_code: HTTP status code
            details: Additional error details
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for API response
        
        Returns:
            Dictionary with error information
        """
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "status_code": self.status_code,
            **self.details
        }


class InvalidFilterException(Neo4jFilterException):
    """
    Raised when filter parameters are invalid
    
    Examples:
        - Invalid operator
        - Missing required fields
        - Invalid value types
        - Conflicting parameters
    """
    
    def __init__(
        self,
        message: str,
        filter_type: Optional[str] = None,
        invalid_field: Optional[str] = None,
        invalid_value: Any = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize invalid filter exception
        
        Args:
            message: Error message
            filter_type: Type of filter (node/relationship/property)
            invalid_field: Name of invalid field
            invalid_value: The invalid value provided
            details: Additional error details
        """
        error_details = details or {}
        
        if filter_type:
            error_details["filter_type"] = filter_type
        if invalid_field:
            error_details["invalid_field"] = invalid_field
        if invalid_value is not None:
            error_details["invalid_value"] = str(invalid_value)
        
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=error_details
        )


class Neo4jConnectionException(Neo4jFilterException):
    """
    Raised when Neo4j connection fails
    
    Examples:
        - Cannot connect to Neo4j server
        - Authentication failure
        - Connection timeout
        - Network issues
    """
    
    def __init__(
        self,
        message: str,
        neo4j_uri: Optional[str] = None,
        connection_error: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Neo4j connection exception
        
        Args:
            message: Error message
            neo4j_uri: Neo4j URI (sanitized)
            connection_error: Underlying connection error
            details: Additional error details
        """
        error_details = details or {}
        
        if neo4j_uri:
            # Sanitize URI to remove credentials
            sanitized_uri = neo4j_uri.split("@")[-1] if "@" in neo4j_uri else neo4j_uri
            error_details["neo4j_uri"] = sanitized_uri
        
        if connection_error:
            error_details["connection_error"] = connection_error
        
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=error_details
        )


class QueryExecutionException(Neo4jFilterException):
    """
    Raised when Cypher query execution fails
    
    Examples:
        - Syntax errors in generated query
        - Neo4j constraints violated
        - Transaction failures
        - Timeout errors
    """
    
    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        cypher_error: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize query execution exception
        
        Args:
            message: Error message
            query: The Cypher query that failed (truncated if too long)
            cypher_error: Neo4j error message
            error_code: Neo4j error code
            details: Additional error details
        """
        error_details = details or {}
        
        if query:
            # Truncate long queries
            max_query_length = 500
            truncated_query = query[:max_query_length]
            if len(query) > max_query_length:
                truncated_query += "... (truncated)"
            error_details["query"] = truncated_query
        
        if cypher_error:
            error_details["cypher_error"] = cypher_error
        
        if error_code:
            error_details["error_code"] = error_code
        
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=error_details
        )


class ValidationException(Neo4jFilterException):
    """
    Raised when request validation fails
    
    Examples:
        - Invalid pagination parameters
        - Out of range values
        - Invalid data types
        - Missing required fields
    """
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Any = None,
        expected_type: Optional[str] = None,
        validation_rule: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize validation exception
        
        Args:
            message: Error message
            field_name: Name of field that failed validation
            field_value: The invalid value
            expected_type: Expected data type
            validation_rule: Validation rule that was violated
            details: Additional error details
        """
        error_details = details or {}
        
        if field_name:
            error_details["field_name"] = field_name
        if field_value is not None:
            error_details["field_value"] = str(field_value)
        if expected_type:
            error_details["expected_type"] = expected_type
        if validation_rule:
            error_details["validation_rule"] = validation_rule
        
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=error_details
        )


class AuthorizationException(Neo4jFilterException):
    """
    Raised when authorization fails
    
    Examples:
        - Missing API key
        - Invalid credentials
        - Insufficient permissions
        - Expired tokens
    """
    
    def __init__(
        self,
        message: str = "Authorization failed",
        required_permission: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize authorization exception
        
        Args:
            message: Error message
            required_permission: Permission that was required
            details: Additional error details
        """
        error_details = details or {}
        
        if required_permission:
            error_details["required_permission"] = required_permission
        
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=error_details
        )


class RateLimitException(Neo4jFilterException):
    """
    Raised when rate limit is exceeded
    
    Examples:
        - Too many requests per minute
        - Query complexity limit exceeded
        - Resource quota exceeded
    """
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        limit: Optional[int] = None,
        reset_time: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize rate limit exception
        
        Args:
            message: Error message
            limit: Rate limit threshold
            reset_time: Unix timestamp when limit resets
            details: Additional error details
        """
        error_details = details or {}
        
        if limit:
            error_details["limit"] = limit
        if reset_time:
            error_details["reset_time"] = reset_time
        
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=error_details
        )


class ResourceNotFoundException(Neo4jFilterException):
    """
    Raised when requested resource is not found
    
    Examples:
        - Node not found
        - Relationship not found
        - Label doesn't exist
        - Property doesn't exist
    """
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize resource not found exception
        
        Args:
            message: Error message
            resource_type: Type of resource (node/relationship/label)
            resource_id: ID of missing resource
            details: Additional error details
        """
        error_details = details or {}
        
        if resource_type:
            error_details["resource_type"] = resource_type
        if resource_id:
            error_details["resource_id"] = resource_id
        
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=error_details
        )


class TimeoutException(Neo4jFilterException):
    """
    Raised when operation times out
    
    Examples:
        - Query execution timeout
        - Connection timeout
        - Transaction timeout
    """
    
    def __init__(
        self,
        message: str = "Operation timed out",
        timeout_seconds: Optional[float] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize timeout exception
        
        Args:
            message: Error message
            timeout_seconds: Timeout duration in seconds
            operation: Operation that timed out
            details: Additional error details
        """
        error_details = details or {}
        
        if timeout_seconds:
            error_details["timeout_seconds"] = timeout_seconds
        if operation:
            error_details["operation"] = operation
        
        super().__init__(
            message=message,
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            details=error_details
        )


class ConfigurationException(Neo4jFilterException):
    """
    Raised when service configuration is invalid
    
    Examples:
        - Missing environment variables
        - Invalid configuration values
        - Configuration file errors
    """
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Any = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize configuration exception
        
        Args:
            message: Error message
            config_key: Configuration key that's invalid
            config_value: Invalid configuration value
            details: Additional error details
        """
        error_details = details or {}
        
        if config_key:
            error_details["config_key"] = config_key
        if config_value is not None:
            error_details["config_value"] = str(config_value)
        
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=error_details
        )