"""FastAPI Dependency Injection Providers.

Provides database sessions, search engine clients, and service
instances as injectable dependencies for route handlers.
"""

from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db

# Add placeholder search client/service dependencies if needed,
# but get_db is the core database session dependency.
