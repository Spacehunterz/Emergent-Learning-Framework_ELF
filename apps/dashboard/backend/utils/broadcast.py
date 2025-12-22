"""
WebSocket broadcast management for the Emergent Learning Dashboard.

Provides ConnectionManager for handling real-time updates to connected clients.
"""

import logging
from datetime import datetime
from typing import List

from fastapi import WebSocket


logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.last_state_hash = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to broadcast to client: {e}")
                dead_connections.append(connection)

        # Remove dead connections
        for conn in dead_connections:
            self.active_connections.remove(conn)

    async def broadcast_update(self, update_type: str, data: dict):
        await self.broadcast({
            "type": update_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        })
