import logging
import orjson
import asyncio, uuid, zlib, json
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
        self.message_retries = defaultdict(int)  # Track retry counts
        self.pending_messages = defaultdict(dict) 
        self.lock = asyncio.Lock()
    #SH:method of Handle a new WebSocket connection
        self.message_timestamps = defaultdict(list)  # Track message timestamps per user
        self.priority_queues = settings.WEBSOCKET_OPTIMIZATION['priority_queues']
        self._processing_task = asyncio.create_task(self.process_messages())

        # Add these new properties
        self.error_counts = defaultdict(int)
        self.last_error_time = {}
        self.maintenance_mode = False

    async def check_rate_limit(self, user_id: str):
        now = datetime.now()
        timestamps = self.message_timestamps[user_id]
        timestamps = [ts for ts in timestamps if (now - ts).total_seconds() < 1]
        self.message_timestamps[user_id] = timestamps

        if len(timestamps) >= settings.WEBSOCKET_RATE_LIMIT:
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Rate limit exceeded"
            )

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
            websocket.timeout = settings.WEBSOCKET_TIMEOUT
            logger.info(f"Set WebSocket timeout to {settings.WEBSOCKET_TIMEOUT} seconds for user {user_id}")
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
        logger.debug(f"Sending message to {user_id}: {message}")
        async with self.lock:
            await self.check_rate_limit(user_id)
            self.message_timestamps[user_id].append(datetime.now())
            if websocket := self.active_connections.get(user_id):
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    self.error_counts[user_id] += 1
                    logger.error(f"Error sending message to {user_id}: {str(e)}")
                    
                    #SH: Disconnect user if sending fails
                    if self.error_counts[user_id] > 3:
                        await self.send_system_notification(
                            user_id, 
                            "Connection unstable. Please check your network."
                        )
                    
                    await self.disconnect(user_id, None)
                    
    #SH: Broadcast a message to all users connected to a specific agent
    async def send_system_notification(self, user_id: str, message: str):
        notification = {
            "type": "system",
            "content": message,
            "timestamp": datetime.now().isoformat()
        }
        await self.enqueue_message(user_id, notification, priority=2)

    async def check_system_status(self):
        if self.maintenance_mode:
            return {
                "status": "maintenance",
                "message": "System maintenance in progress. Please try again later."
            }
        return {"status": "ok"}

    async def broadcast(self, message: dict, agent_id: int, exclude: Optional[str] = None):
        async with self.lock:
            for user_id in self.agent_connections[agent_id]:
                if user_id != exclude:
                    await self.send_personal_message(message, user_id)

    #SH: Queue a message to be sent later
    async def enqueue_message(self, user_id: str, message: dict, priority: int = 0):
        logger.debug(f"Enqueuing message for {user_id}: {message}")
        if self.priority_queues:
            await self.message_queues[user_id].put((priority, message))
        else:
            await self.message_queues[user_id].put(message)

    async def process_messages(self):
        while True:
            for user_id, queue in self.message_queues.items():
                batch = []
                while not queue.empty() and len(batch) < settings.WEBSOCKET_BATCH_SIZE:
                    batch.append(await queue.get())

                if batch:
                    if settings.PRIORITY_QUEUES:
                        batch.sort(key=lambda x: x[0], reverse=True)
                        processed_batch = [msg for (_, msg) in batch]
                    else:
                        processed_batch = batch

                    if settings.MESSAGE_COMPRESSION:
                        await self._send_compressed_batch(user_id, processed_batch)
                    else:
                        await self._send_raw_batch(user_id, processed_batch)

            await asyncio.sleep(0)

    async def _send_compressed_batch(self, user_id, messages):
        compressed = zlib.compress(json.dumps(messages).encode())
        await self.active_connections[user_id].send_bytes(compressed)

    async def _send_raw_batch(self, user_id, messages):
        for message in messages:
            await self.send_personal_message(message, user_id)

    async def send_with_retry(self, websocket: WebSocket, message: dict, max_retries: int = settings.MESSAGE_RETRY_LIMIT):
        message_id = str(uuid.uuid4())
        message['message_id'] = message_id

        for attempt in range(max_retries):
            try:
                await websocket.send_json(message)
                self.pending_messages[websocket][message_id] = {
                    'message': message,
                    'timestamp': datetime.now(),
                    'retries': attempt
                }
                return True
            except Exception as e:
                if attempt == max_retries - 1:
                    await self.handle_failed_message(websocket, message_id)
                    return False
                await asyncio.sleep(1 * (attempt + 1))

    async def handle_failed_message(self, websocket: WebSocket, message_id: str):
        async with self.lock:
            if message_id in self.pending_messages.get(websocket, {}):
                message_data = self.pending_messages[websocket].pop(message_id)
                logger.error(f"Failed to deliver message after {settings.MESSAGE_RETRY_LIMIT} attempts")
                if len(self.pending_messages[websocket]) >= settings.WEBSOCKET_OPTIMIZATION['max_pending_messages']:
                    logger.warning("Too many pending messages, disconnecting client")
                    user_id = next((uid for uid, ws in self.active_connections.items() if ws == websocket), None)
                    if user_id:
                        await self.disconnect(user_id, None)

    async def shutdown(self):
        self._processing_task.cancel()
        try:
            await self._processing_task
        except asyncio.CancelledError:
            pass

websocket_manager = ConnectionManager()

#SH: WidgetConnectionManager for embedded widgets
class WidgetConnectionManager:
    def _init_(self):
        self.active_connections = defaultdict(dict)
        
    async def connect(self, agent_id: int, websocket: WebSocket):
        self.active_connections[agent_id][id(websocket)] = websocket

    async def disconnect(self, agent_id: int, websocket: WebSocket):
        if id(websocket) in self.active_connections.get(agent_id, {}):
            del self.active_connections[agent_id][id(websocket)]
            await websocket.close()

    async def broadcast(self, agent_id: int, message: dict):
        for connection in self.active_connections.get(agent_id, {}).values():
            try:
                await connection.send_json(message)
            except:
                await self.disconnect(agent_id, connection)

widget_manager = WidgetConnectionManager()
