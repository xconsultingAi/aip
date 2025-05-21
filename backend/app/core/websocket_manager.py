import logging
import asyncio, uuid, zlib, json
from collections import defaultdict
from datetime import datetime
from typing import Dict, Set, Optional
from fastapi import WebSocket, status
from fastapi.exceptions import WebSocketException
from app.core.config import settings
from app.db.models.agent import Agent
from sqlalchemy.future import select
from app.db.database import AsyncSession

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
        message_id = message.get("message_id", str(uuid.uuid4()))
        if message_id not in self.pending_messages[user_id]:
            self.pending_messages[user_id][message_id] = message
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
    async def validate_public_agent(self, agent_id: int, db: AsyncSession):
        result = await db.execute(
            select(Agent)
            .where(
                (Agent.id == agent_id) & 
                (Agent.is_public == True)
            )
        )
        return result.scalars().first()

websocket_manager = ConnectionManager()

#SH: WidgetConnectionManager for embedded widgets
class WidgetConnectionManager:
    def __init__(self):
        self.active_connections = defaultdict(dict)
        self.message_queues = defaultdict(asyncio.Queue)
        self.message_timestamps = defaultdict(list) 
        self.priority_queues = True 
        self.pending_messages = defaultdict(dict) 
        self.message_retries = defaultdict(int) 
        self.lock = asyncio.Lock()
        self.error_counts = defaultdict(int)
        self.last_error_time = {}
        self.maintenance_mode = False
        self._processing_task = asyncio.create_task(self.process_messages())

        #SH: Visitor support
        self.visitor_sessions = defaultdict(dict)  # visitor_id -> {agent_id, websocket}
        self.agent_visitors = defaultdict(set)     # agent_id -> set(visitor_ids)

    async def check_rate_limit(self, user_id: str):
        # Check if the user has exceeded the rate limit.
        now = datetime.now()
        timestamps = self.message_timestamps[user_id]
        timestamps = [ts for ts in timestamps if (now - ts).total_seconds() < 1]
        self.message_timestamps[user_id] = timestamps

        if len(timestamps) >= 10:  # rate limit.
            raise Exception(f"Rate limit exceeded for user {user_id}")

    async def connect(self, agent_id: int, websocket: WebSocket):
        # Handle a new WebSocket connection for an agent.
        connection_id = id(websocket)
        self.active_connections[agent_id][connection_id] = websocket
        logger.info(f"Widget connection established for agent {agent_id}")

    async def disconnect(self, agent_id: int, websocket: WebSocket):
        # Disconnect a WebSocket connection from an agent.
        connection_id = id(websocket)
        if connection_id in self.active_connections.get(agent_id, {}):
            del self.active_connections[agent_id][connection_id]
            logger.info(f"Widget disconnected from agent {agent_id}")
        try:
            await websocket.close()
        except:
            logger.warning("WebSocket already closed or failed to close.")

    async def send_direct(self, agent_id: int, message: dict, websocket: WebSocket):
        # Send a direct message to a specific WebSocket connection.
        connection_id = id(websocket)
        if connection_id in self.active_connections.get(agent_id, {}):
            try:
                await self.active_connections[agent_id][connection_id].send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to client: {e}")
                await self.disconnect(agent_id, websocket)

    async def send_with_retry(self, agent_id: int, message: dict, websocket: WebSocket, max_retries: int = 3):
        # Send a message to the WebSocket with retry logic.
        message_id = str(uuid.uuid4())
        message['message_id'] = message_id

        for attempt in range(max_retries):
            try:
                await self.send_direct(agent_id, message, websocket)
                self.pending_messages[agent_id][message_id] = {
                    'message': message,
                    'timestamp': datetime.now(),
                    'retries': attempt
                }
                return True
            except Exception as e:
                if attempt == max_retries - 1:
                    await self.handle_failed_message(agent_id, message_id, websocket)
                    return False
                await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff

    async def handle_failed_message(self, agent_id: int, message_id: str, websocket: WebSocket):
        # Handle a message that has failed to send after retries.
        async with self.lock:
            if message_id in self.pending_messages.get(agent_id, {}):
                message_data = self.pending_messages[agent_id].pop(message_id)
                logger.error(f"Failed to deliver message {message_id} after retries.")
                self.error_counts[agent_id] += 1
                if self.error_counts[agent_id] > 3:
                    await self.send_system_notification(agent_id, "Connection issues detected.")

    async def send_system_notification(self, agent_id: int, message: str):
        # Send a system-wide notification to all connected widgets.
        notification = {
            "type": "system",
            "content": message,
            "timestamp": datetime.now().isoformat()
        }
        for connection_id, websocket in self.active_connections.get(agent_id, {}).items():
            try:
                await websocket.send_json(notification)
            except Exception as e:
                logger.error(f"Failed to send system notification to widget (agent {agent_id}): {e}")
                await self.disconnect(agent_id, websocket)

    async def process_messages(self):
        # Process queued messages and send them to connected WebSockets.
        while True:
            for agent_id, queue in self.message_queues.items():
                batch = []
                while not queue.empty() and len(batch) < 10:  # Batch size limit (configurable)
                    batch.append(await queue.get())

                if batch:
                    if self.priority_queues:
                        batch.sort(key=lambda x: x[0], reverse=True)  # Priority queue processing
                        processed_batch = [msg for _, msg in batch]
                    else:
                        processed_batch = batch

                    for message in processed_batch:
                        await self.send_direct(agent_id, message, websocket=None)

            await asyncio.sleep(0)

    async def shutdown(self):
        self._processing_task.cancel()
        try:
            await self._processing_task
        except asyncio.CancelledError:
            pass

    # Visitor Methods
    async def connect_visitor(self, agent_id: int, visitor_id: str, websocket: WebSocket):
        # Register a new visitor connection"
        async with self.lock:
            self.visitor_sessions[visitor_id] = {
                'agent_id': agent_id,
                'websocket': websocket,
                'last_active': datetime.now()
            }
            self.agent_visitors[agent_id].add(visitor_id)

    async def disconnect_visitor(self, visitor_id: str):
        # Remove visitor connection
        async with self.lock:
            session = self.visitor_sessions.pop(visitor_id, None)
            if session and session['agent_id']:
                self.agent_visitors[session['agent_id']].discard(visitor_id)

    async def send_to_visitor(self, visitor_id: str, message: dict):
        # Send message to specific visitor
        if session := self.visitor_sessions.get(visitor_id):
            try:
                await session['websocket'].send_json(message)
                session['last_active'] = datetime.now()
            except Exception as e:
                logger.error(f"Error sending to visitor {visitor_id}: {str(e)}")

    async def broadcast_to_agent(self, agent_id: int, message: dict, exclude: str = None):
        # Send message to all visitors of an agent
        for visitor_id in self.agent_visitors.get(agent_id, []):
            if visitor_id != exclude:
                await self.send_to_visitor(visitor_id, message)


# Instantiate the widget manager
widget_manager = WidgetConnectionManager()

