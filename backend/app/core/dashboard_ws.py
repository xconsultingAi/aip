from collections import defaultdict
from fastapi import WebSocket
from typing import Dict, List, DefaultDict, Optional
import asyncio

class DashboardWSManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: DefaultDict[str, List[WebSocket]] = defaultdict(list)
        self.org_connections: DefaultDict[str, List[WebSocket]] = defaultdict(list)
        
    async def connect(self, websocket: WebSocket, user_id: str, org_id: str):
        self.active_connections[user_id] = websocket
        self.user_connections[user_id].append(websocket)
        self.org_connections[org_id].append(websocket)
      
    async def disconnect(self, user_id: str, org_id: str):
        websocket = self.active_connections.pop(user_id, None)
        if websocket:
            self.user_connections[user_id] = [ws for ws in self.user_connections[user_id] if ws != websocket]
            self.org_connections[org_id] = [ws for ws in self.org_connections[org_id] if ws != websocket]
    
    async def send_user_stats(self, user_id: str, stats: dict):
        if user_id in self.user_connections:
            for websocket in self.user_connections[user_id]:
                try:
                    await websocket.send_json({
                        "type": "stats_update",
                        "data": stats
                    })
                except:
                    await self.disconnect(user_id, stats.get('org_id', ''))
    
    async def broadcast_org_stats(self, org_id: str, stats: dict):
        if org_id in self.org_connections:
            for websocket in self.org_connections[org_id]:
                try:
                    await websocket.send_json({
                        "type": "stats_update",
                        "data": stats
                    })
                except:
                    user_id = next((uid for uid, ws in self.active_connections.items() if ws == websocket), None)
                    if user_id:
                        await self.disconnect(user_id, org_id)
                        
dashboard_ws_manager = DashboardWSManager()