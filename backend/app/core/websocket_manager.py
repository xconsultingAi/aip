import logging
import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Dict, Set, Optional

from fastapi import WebSocket, status
from fastapi.exceptions import WebSocketException

from app.core.config import settings

logger = logging.getLogger(__name__)

#SH: This class manages all active WebSocket connections and messaging logic
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.agent_connections: Dict[int, Set[str]] = defaultdict(set)
        self.message_queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self.lock = asyncio.Lock()
    #SH:method of Handle a new WebSocket connection
    async def connect(self, websocket: WebSocket, user_id: str, agent_id: int):
        async with self.lock:
            #SH: Check if maximum allowed connections reached
            if len(self.active_connections) >= settings.MAX_CONNECTIONS:
                raise WebSocketException(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Too many connections"
                )

            #SH: Prevent same user from opening multiple connections
            if user_id in self.active_connections:
                raise WebSocketException(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Existing connection found"
                )

            #SH: Save connection and link it with the agent
            self.active_connections[user_id] = websocket
            self.agent_connections[agent_id].add(user_id)
            logger.info(f"User {user_id} connected to Agent {agent_id}")

    #SH: Method to cleanly disconnect a user
    async def disconnect(self, user_id: str, agent_id: Optional[int]):
        async with self.lock:
            websocket = self.active_connections.pop(user_id, None)

            #SH: Remove user from agent's connection list
            if agent_id is not None:
                self.agent_connections[agent_id].discard(user_id)

            #SH: Attempt to close the WebSocket connection
            if websocket:
                try:
                    await websocket.close()
                except Exception as e:
                    logger.error(f"Error closing connection for {user_id}: {str(e)}")
            
            logger.info(f"User {user_id} disconnected")

    #SH: Send a message to a specific user
    async def send_personal_message(self, message: dict, user_id: str):
        async with self.lock:
            if websocket := self.active_connections.get(user_id):
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to {user_id}: {str(e)}")
                    #SH: Disconnect user if sending fails
                    await self.disconnect(user_id, None)

    #SH: Broadcast a message to all users connected to a specific agent
    async def broadcast(self, message: dict, agent_id: int, exclude: Optional[str] = None):
        async with self.lock:
            for user_id in self.agent_connections[agent_id]:
                if user_id != exclude:
                    await self.send_personal_message(message, user_id)

    #SH: Queue a message to be sent later
    async def enqueue_message(self, user_id: str, message: dict):
        await self.message_queues[user_id].put(message)
        
websocket_manager = ConnectionManager()
