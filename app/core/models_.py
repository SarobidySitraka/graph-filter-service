"""Pydantic models for request response validation"""

from typing import Any, List, Optional
from pydantic import BaseModel, Field, field_validator
from app.core.enums import ComparisonOperator, LogicalOperator, RelationshipDirection


class PropertyFilter(BaseModel):
    """Filter criteria for a node or relationship property"""
    property_name: str = Field(..., description="Property name to filter on")
    operator: ComparisonOperator = Field(..., description="Comparison operator")
    value: Any = Field(..., description="Value to compare against")

    @field_validator('value')
    @classmethod
    def validate_value(cls, v: Any, info) -> Any:
        """Validate value is compatible with operator"""
        operator = info.data.get('operator')
        if operator in [ComparisonOperator.IN, ComparisonOperator.NOT_IN]:
            if not isinstance(v, (list, tuple)):
                raise ValueError(f"Value must be a list for operator {operator}")
        return v


class NodeFilter(BaseModel):
    """Filter criteria for graph nodes"""
    node_types: List[str] = Field(
        default_factory=list,
        description="Node labels to filter by"
    )
    property_filters: List[PropertyFilter] = Field(
        default_factory=list,
        description="Property-based filters"
    )
    logical_operator: LogicalOperator = Field(
        default=LogicalOperator.AND,
        description="Logical operator to combine property filters"
    )
    labels: Optional[List[str]] = Field(
        default=None,
        description="Specific labels to match"
    )


class RelationshipFilter(BaseModel):
    """Filter criteria for graph relationships"""
    relationship_types: List[str] = Field(
        default_factory=list,
        description="Relationship types to filter by"
    )
    property_filters: List[PropertyFilter] = Field(
        default_factory=list,
        description="Property-based filters for relationships"
    )
    direction: Optional[RelationshipDirection] = Field(
        default=None,
        description="Direction of relationship traversal"
    )
    min_depth: int = Field(
        default=1,
        ge=1,
        description="Minimum relationship depth"
    )
    max_depth: int = Field(
        default=1,
        ge=1,
        description="Maximum relationship depth"
    )


class GraphFilterRequest(BaseModel):
    """Complete graph filter request"""
    node_filter: Optional[NodeFilter] = Field(
        default=None,
        description="Node filtering criteria"
    )
    relationship_filter: Optional[RelationshipFilter] = Field(
        default=None,
        description="Relationship filtering criteria"
    )
    search_query: Optional[str] = Field(
        default=None,
        description="Text search query for labels and properties"
    )
    limit: Optional[int] = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of results"
    )
    skip: Optional[int] = Field(
        default=0,
        ge=0,
        description="Number of results to skip"
    )


class NodeResponse(BaseModel):
    """Response model for a graph node"""
    id: int = Field(..., description="Neo4j node ID")
    labels: List[str] = Field(..., description="Node labels")
    properties: dict = Field(..., description="Node properties")


class RelationshipResponse(BaseModel):
    """Response model for a graph relationship"""
    id: int = Field(..., description="Neo4j relationship ID")
    type: str = Field(..., description="Relationship type")
    source: NodeResponse = Field(..., description="Source node")
    target: NodeResponse = Field(..., description="Target node")
    properties: dict = Field(..., description="Relationship properties")


class FilterResponse(BaseModel):
    """Generic filter response with metadata"""
    total: int = Field(..., description="Total number of results")
    limit: int = Field(..., description="Applied limit")
    skip: int = Field(..., description="Applied skip offset")
    data: List[Any] = Field(..., description="Result data")
    active_filters: List[str] | None = Field(
        default=None,
        description="Summary of active filters"
    )


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    neo4j_connected: bool = Field(..., description="Neo4j connection status")
    version: str = Field(..., description="Service version")