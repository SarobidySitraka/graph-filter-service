"""Neo4j connection and session management service"""

from typing import Optional
from contextlib import contextmanager
from neo4j import GraphDatabase, Driver
from app.config import settings
from app.core.exceptions import Neo4jConnectionException
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class Neo4jService:
    """Manages Neo4j database connections and sessions"""

    _instance: Optional['Neo4jService'] = None
    _driver: Optional[Driver] = None

    def __new__(cls):
        """Implement singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize Neo4j connection"""
        if self._driver is None:
            self._connect()

    def _connect(self):
        """Establish connection to Neo4j database"""
        try:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            self._driver.verify_connectivity()
            logger.info(f"Successfully connected to Neo4j at {settings.NEO4J_URI}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {str(e)}")
            raise Neo4jConnectionException(f"Neo4j connection failed: {str(e)}")

    @contextmanager
    def get_session(self, database: Optional[str] = None):
        """Context manager for Neo4j sessions
        Args:
            database: Optional database name
        Yields:
            Neo4j session
        """
        session = self._driver.session(database=database)
        try:
            yield session
        finally:
            session.close()


    def verify_connection(self) -> bool:
        """Verify Neo4j connection is alive
        Returns:
            True if connected, False otherwise
        """
        try:
            self._driver.verify_connectivity()
            return True
        except Exception as e:
            logger.error(f"Connection verification failed: {str(e)}")
            return False


    def close(self):
        """Close Neo4j driver connection"""
        if self._driver:
            self._driver.close()
            logger.info("Neo4j connection closed")


    def __del__(self):
        """Cleanup on object destruction"""
        self.close()

# Global instance
neo4j_service = Neo4jService()