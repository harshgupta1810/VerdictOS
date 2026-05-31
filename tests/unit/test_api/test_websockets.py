import pytest
from src.api.websockets.emitter import DealConnectionManager, emit_pipeline_event
from unittest.mock import AsyncMock, patch
from fastapi import WebSocket

@pytest.mark.asyncio
async def test_deal_connection_manager_connect_disconnect() -> None:
    manager = DealConnectionManager()
    ws = AsyncMock(spec=WebSocket)
    await manager.connect("123", ws)
    ws.accept.assert_called_once()
    assert ws in manager.active_connections["123"]
    
    manager.disconnect("123", ws)
    assert "123" not in manager.active_connections

@pytest.mark.asyncio
async def test_deal_connection_manager_emit() -> None:
    manager = DealConnectionManager()
    ws1 = AsyncMock(spec=WebSocket)
    ws2 = AsyncMock(spec=WebSocket)
    await manager.connect("123", ws1)
    await manager.connect("123", ws2)
    
    await manager.emit("123", "test_event", {"data": 1})
    ws1.send_text.assert_called_once()
    ws2.send_text.assert_called_once()

@pytest.mark.asyncio
async def test_deal_connection_manager_emit_dead_connection() -> None:
    manager = DealConnectionManager()
    ws = AsyncMock(spec=WebSocket)
    ws.send_text.side_effect = Exception("Dead")
    await manager.connect("123", ws)
    
    await manager.emit("123", "test_event", {"data": 1})
    # Should disconnect
    assert "123" not in manager.active_connections

@pytest.mark.asyncio
async def test_deal_connection_manager_emit_no_connections() -> None:
    manager = DealConnectionManager()
    # This shouldn't crash
    await manager.emit("456", "test", {})

@pytest.mark.asyncio
async def test_emit_pipeline_event() -> None:
    with patch("src.api.websockets.emitter.manager.emit", new_callable=AsyncMock) as mock_emit:
        await emit_pipeline_event("123", "event", {"k": "v"})
        mock_emit.assert_called_once_with("123", "event", {"k": "v"})
