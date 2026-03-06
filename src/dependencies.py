"""
Dependency injection para FastAPI.
"""

from src.db.session import get_db

# Re-export para uso limpio en endpoints
__all__ = ["get_db"]
