"""WebSocket endpoint for real-time telemetry, drop updates, and live logs."""

from __future__ import annotations

import asyncio
import json
from typing import Set, Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.core.logging import logger
from app.core.security import decode_token
from app.engine.miner_worker import miner_service

router = APIRouter(tags=["WebSocket"])


class WebSocketManager:
    """Manages active WebSocket connections and handles broadcasting."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")
        # Send initial status immediately upon connecting
        try:
            status_payload = {"type": "STATUS_UPDATE", "data": miner_service.get_status()}
            await websocket.send_text(json.dumps(status_payload))
        except Exception:
            pass

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast JSON payload to all active clients."""
        if not self.active_connections:
            return

        payload_str = json.dumps(message)
        dead_connections = set()

        for conn in list(self.active_connections):
            try:
                await conn.send_text(payload_str)
            except Exception:
                dead_connections.add(conn)

        for dead in dead_connections:
            self.disconnect(dead)


ws_manager = WebSocketManager()


async def ws_status_broadcaster(status_data: Dict[str, Any]) -> None:
    """Callback passed to miner worker to broadcast status."""
    await ws_manager.broadcast({
        "type": "STATUS_UPDATE",
        "data": status_data,
    })


# Register broadcaster callback with miner worker
miner_service.register_ws_broadcaster(ws_status_broadcaster)


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """Authenticate and maintain WebSocket stream."""
    # Check token from query param or cookie
    auth_token = token or websocket.cookies.get("access_token")
    if not auth_token:
        await websocket.close(code=4001, reason="Authentication token missing")
        return

    try:
        decode_token(auth_token, expected_type="access")
    except Exception:
        await websocket.close(code=4003, reason="Invalid or expired authentication token")
        return

    await ws_manager.connect(websocket)

    try:
        while True:
            # Keepalive / ping-pong handler
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("action") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except Exception:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
