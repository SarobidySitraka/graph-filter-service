"""Enumeration definitions for filter operations"""
from enum import Enum

class ComparisonOperator(str, Enum):
    """Comparison operators supported for property filtering"""
    EQUAL = "="
    NOT_EQUAL = "!="
    GREATER = ">"
    GREATER_EQUAL = ">="
    LESS = "<"
    LESS_EQUAL = "<="
    CONTAINS = "CONTAINS"
    STARTS_WITH = "STARTS WITH"
    ENDS_WITH = "ENDS WITH"
    IN = "IN"
    NOT_IN = "NOT IN"
    REGEX = "=~"


class LogicalOperator(str, Enum):
    """Logical operators for combining multiple filters"""
    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class RelationshipDirection(str, Enum):
    """Direction for relationship traversal"""
    INCOMING = "incoming"
    OUTGOING = "outgoing"
    BOTH = "undirected"