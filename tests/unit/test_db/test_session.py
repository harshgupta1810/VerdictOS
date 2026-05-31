"""Unit tests for the async database session factory."""

import pytest
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db

@pytest.mark.asyncio
async def test_get_db_yields_session() -> None:
    """Test that get_db yields an async session and commits on success."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = False
    
    with patch("src.db.session.AsyncSessionLocal", return_value=mock_session):
        gen = get_db()
        
        # Advance generator
        session = await anext(gen)
        assert session is mock_session
        
        # Finish generator
        with pytest.raises(StopAsyncIteration):
            await anext(gen)
            
        mock_session.commit.assert_awaited_once()
        mock_session.close.assert_awaited_once()

@pytest.mark.asyncio
async def test_get_db_rollbacks_on_exception() -> None:
    """Test that get_db rolls back the session on exception."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = False
    
    with patch("src.db.session.AsyncSessionLocal", return_value=mock_session):
        gen = get_db()
        session = await anext(gen)
        assert session is mock_session
        
        # Inject an exception into the generator
        with pytest.raises(ValueError, match="Test error"):
            await gen.athrow(ValueError("Test error"))
            
        mock_session.rollback.assert_awaited_once()
        mock_session.close.assert_awaited_once()
        mock_session.commit.assert_not_called()
