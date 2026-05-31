"""WebSocket Event Emitter.

Manages active WebSocket connections per deal and broadcasts
pipeline progress, state transitions, and real-time events.
"""

import json
from collections import defaultdict
from typing import Any
from fastapi import WebSocket

class DealConnectionManager:
    """Manages WebSocket connections for active deals."""
    
    def __init__(self):
        # Maps deal_id -> list of active WebSockets
        self.active_connections: dict[str, list[WebSocket]] = defaultdict(list)
        
    async def connect(self, deal_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[deal_id].append(websocket)
        
    def disconnect(self, deal_id: str, websocket: WebSocket):
        if deal_id in self.active_connections:
            if websocket in self.active_connections[deal_id]:
                self.active_connections[deal_id].remove(websocket)
            if not self.active_connections[deal_id]:
                del self.active_connections[deal_id]
                
    async def emit(self, deal_id: str, event_type: str, payload: dict[str, Any]):
        """Emit an event to all connected clients for a specific deal."""
        if deal_id not in self.active_connections:
            return
            
        message = {
            "type": event_type,
            "payload": payload
        }
        text_data = json.dumps(message)
        
        # Create a copy of the list for safe iteration
        connections = list(self.active_connections[deal_id])
        for connection in connections:
            try:
                await connection.send_text(text_data)
            except Exception:
                # If connection is dead, remove it
                self.disconnect(deal_id, connection)

# Global singleton manager
manager = DealConnectionManager()

async def emit_pipeline_event(deal_id: str, event_type: str, data: dict[str, Any]):
    """Helper function to emit events from pipeline workers."""
    await manager.emit(deal_id, event_type, data)
