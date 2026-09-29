import json
import logging
from typing import Any, Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accept connection and register client."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("WebSocket client connected. Total clients: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        """Remove client on disconnect."""
        self.active_connections.discard(websocket)
        logger.info("WebSocket client disconnected. Total clients: %d", len(self.active_connections))

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send message to a specific client."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.warning("Error sending message to specific WebSocket client: %s", e)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        if not self.active_connections:
            return

        payload = json.dumps(message)
        disconnected_clients = set()

        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception as e:
                logger.debug("Failed to send to WebSocket client (%s), queuing for removal", e)
                disconnected_clients.add(connection)

        for conn in disconnected_clients:
            self.disconnect(conn)

    @property
    def client_count(self) -> int:
        return len(self.active_connections)


ws_manager = WebSocketManager()
