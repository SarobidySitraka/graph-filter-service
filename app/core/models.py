# """Pydantic models for request response validation"""

# from typing import Any, List, Optional
# from pydantic import BaseModel, Field, field_validator
# from app.core.enums import ComparisonOperator, LogicalOperator, RelationshipDirection


# class PropertyFilter(BaseModel):
#     """Filter criteria for a node or relationship property"""
#     property_name: str = Field(..., description="Property name to filter on")
#     operator: ComparisonOperator = Field(..., description="Comparison operator")
#     value: Any = Field(..., description="Value to compare against")

#     @field_validator('value')
#     @classmethod
#     def validate_value(cls, v: Any, info) -> Any:
#         """Validate value is compatible with operator"""
#         operator = info.data.get('operator')
#         if operator in [ComparisonOperator.IN, ComparisonOperator.NOT_IN]:
#             if not isinstance(v, (list, tuple)):
#                 raise ValueError(f"Value must be a list for operator {operator}")
#         return v


# class NodeFilter(BaseModel):
#     """Filter criteria for graph nodes"""
#     node_types: List[str] = Field(
#         default_factory=list,
#         description="Node labels to filter by"
#     )
#     property_filters: List[PropertyFilter] = Field(
#         default_factory=list,
#         description="Property-based filters"
#     )
#     logical_operator: LogicalOperator = Field(
#         default=LogicalOperator.AND,
#         description="Logical operator to combine property filters"
#     )
#     labels: Optional[List[str]] = Field(
#         default=None,
#         description="Specific labels to match"
#     )


# class RelationshipFilter(BaseModel):
#     """Filter criteria for graph relationships"""
#     relationship_types: List[str] = Field(
#         default_factory=list,
#         description="Relationship types to filter by"
#     )
#     property_filters: List[PropertyFilter] = Field(
#         default_factory=list,
#         description="Property-based filters for relationships"
#     )
#     direction: Optional[RelationshipDirection] = Field(
#         default=None,
#         description="Direction of relationship traversal"
#     )
#     min_depth: int = Field(
#         default=1,
#         ge=1,
#         description="Minimum relationship depth"
#     )
#     max_depth: int = Field(
#         default=1,
#         ge=1,
#         description="Maximum relationship depth"
#     )


# class GraphFilterRequest(BaseModel):
#     """Complete graph filter request"""
#     node_filter: Optional[NodeFilter] = Field(
#         default=None,
#         description="Node filtering criteria"
#     )
#     relationship_filter: Optional[RelationshipFilter] = Field(
#         default=None,
#         description="Relationship filtering criteria"
#     )
#     search_query: Optional[str] = Field(
#         default=None,
#         description="Text search query for labels and properties"
#     )
#     limit: Optional[int] = Field(
#         default=100,
#         ge=1,
#         le=1000,
#         description="Maximum number of results"
#     )
#     skip: Optional[int] = Field(
#         default=0,
#         ge=0,
#         description="Number of results to skip"
#     )


# class NodeResponse(BaseModel):
#     """Response model for a graph node"""
#     id: int = Field(..., description="Neo4j node ID")
#     labels: List[str] = Field(..., description="Node labels")
#     properties: dict = Field(..., description="Node properties")


# class RelationshipResponse(BaseModel):
#     """Response model for a graph relationship"""
#     id: int = Field(..., description="Neo4j relationship ID")
#     type: str = Field(..., description="Relationship type")
#     source: NodeResponse = Field(..., description="Source node")
#     target: NodeResponse = Field(..., description="Target node")
#     properties: dict = Field(..., description="Relationship properties")


# class FilterResponse(BaseModel):
#     """Generic filter response with metadata"""
#     total: int = Field(..., description="Total number of results")
#     limit: int = Field(..., description="Applied limit")
#     skip: int = Field(..., description="Applied skip offset")
#     data: List[Any] = Field(..., description="Result data")
#     active_filters: List[str] | None = Field(
#         default=None,
#         description="Summary of active filters"
#     )

"""Pydantic models for request response validation - Adapted for Multi-Node/Rel support"""

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
        if not info.data.get('operator'):
            return v
        
        operator = info.data.get('operator')
        if operator in [ComparisonOperator.IN, ComparisonOperator.NOT_IN]:
            if not isinstance(v, (list, tuple)):
                raise ValueError(f"Value must be a list for operator {operator}")
            return v
        
        if operator in [ComparisonOperator.GREATER, ComparisonOperator.GREATER_EQUAL, 
                  ComparisonOperator.LESS, ComparisonOperator.LESS_EQUAL]:
            if isinstance(v, str):
                # Try converting integer first, then float
                if v.isdigit(): 
                    return int(v)
                try:
                    return float(v)
                except ValueError:
                    pass # Keep as string if not a number (maybe lexicographical compare)
                    
        return v


class NodeCriteria(BaseModel):
    """
    Criteria for a single node filter block (e.g. 'Source #1')
    Corresponds to one item in the 'Source Nodes' or 'Target Nodes' list UI
    """
    node_types: List[str] = Field(
        default_factory=list,
        description="Node labels (OR logic often implied between types)"
    )
    property_filters: List[PropertyFilter] = Field(
        default_factory=list,
        description="Property-based filters"
    )
    logical_operator: LogicalOperator = Field(
        default=LogicalOperator.AND,
        description="Logical operator to combine property filters"
    )


class RelationshipCriteria(BaseModel):
    """
    Criteria for a single relationship filter block (e.g. 'Relationship #1')
    """
    relationship_types: List[str] = Field(
        default_factory=list,
        description="Relationship types to filter by"
    )
    property_filters: List[PropertyFilter] = Field(
        default_factory=list,
        description="Property-based filters"
    )
    direction: Optional[RelationshipDirection] = Field(
        default=RelationshipDirection.OUTGOING, # Default per your UI screenshot
        description="Direction relative to source"
    )
    # Support variable length paths if needed (e.g. 1..3)
    min_depth: int = Field(default=1, ge=1)
    max_depth: int = Field(default=1, ge=1)


class GraphFilterRequest(BaseModel):
    """
    Complete graph filter request supporting multiple sources, relations, and targets.
    Structure: (Source Nodes) - [Relationships] -> (Target Nodes)
    """
    # Changed from single NodeFilter to List[NodeCriteria] to match 'Source Nodes (n)'
    source_nodes: Optional[List[NodeCriteria]] = Field(
        default_factory=list,
        description="List of criteria for Source Nodes (OR logic between blocks)"
    )
    
    # Changed from single RelationshipFilter to List[RelationshipCriteria]
    relationships: Optional[List[RelationshipCriteria]] = Field(
        default_factory=list,
        description="List of criteria for Relationships traversal"
    )
    
    # Added Target Nodes to support full path filtering
    target_nodes: Optional[List[NodeCriteria]] = Field(
        default_factory=list,
        description="List of criteria for Target Nodes"
    )

    search_query: Optional[str] = Field(
        default=None,
        description="Global text search query"
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


# --- Response Models (Restés inchangés ou légèrement adaptés) ---

class NodeResponse(BaseModel):
    id: int
    labels: List[str]
    properties: dict

class RelationshipResponse(BaseModel):
    id: int
    type: str
    source: NodeResponse
    target: NodeResponse
    properties: dict

class FilterResponse(BaseModel):
    total: int
    limit: int
    skip: int
    data: List[Any]
    active_filters: List[str] | None = None

class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    neo4j_connected: bool = Field(..., description="Neo4j connection status")
    version: str = Field(..., description="Service version")