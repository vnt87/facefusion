import asyncio
import json
from typing import List, Set

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState


class ConnectionManager:
	"""Manages WebSocket connections for real-time updates."""
	
	def __init__(self):
		self.active_connections: Set[WebSocket] = set()
		self._log_buffer: List[str] = []
	
	async def connect(self, websocket: WebSocket):
		await websocket.accept()
		self.active_connections.add(websocket)
		# Send buffered logs to new connection
		for log in self._log_buffer[-50:]:  # Last 50 logs
			await websocket.send_json({"type": "log", "message": log})
	
	def disconnect(self, websocket: WebSocket):
		self.active_connections.discard(websocket)
	
	async def broadcast_log(self, message: str):
		"""Broadcast a log message to all connected clients."""
		self._log_buffer.append(message)
		if len(self._log_buffer) > 100:
			self._log_buffer = self._log_buffer[-100:]
		
		disconnected = set()
		for connection in self.active_connections:
			try:
				if connection.client_state == WebSocketState.CONNECTED:
					await connection.send_json({"type": "log", "message": message})
			except Exception:
				disconnected.add(connection)
		
		for conn in disconnected:
			self.active_connections.discard(conn)
	
	async def broadcast_progress(self, progress: float, status: str):
		"""Broadcast processing progress to all connected clients."""
		disconnected = set()
		for connection in self.active_connections:
			try:
				if connection.client_state == WebSocketState.CONNECTED:
					await connection.send_json({
						"type": "progress",
						"progress": progress,
						"status": status
					})
			except Exception:
				disconnected.add(connection)
		
		for conn in disconnected:
			self.active_connections.discard(conn)
	
	async def broadcast_complete(self, output_path: str):
		"""Broadcast processing complete to all connected clients."""
		disconnected = set()
		for connection in self.active_connections:
			try:
				if connection.client_state == WebSocketState.CONNECTED:
					await connection.send_json({
						"type": "complete",
						"output_path": output_path
					})
			except Exception:
				disconnected.add(connection)
		
		for conn in disconnected:
			self.active_connections.discard(conn)


# Global connection manager instance
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
	"""WebSocket endpoint for real-time updates."""
	await manager.connect(websocket)
	try:
		while True:
			# Keep connection alive, handle any client messages
			data = await websocket.receive_text()
			# Echo back or handle commands if needed
			if data == "ping":
				await websocket.send_json({"type": "pong"})
	except WebSocketDisconnect:
		manager.disconnect(websocket)
