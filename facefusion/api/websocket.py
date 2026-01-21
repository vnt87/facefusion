import asyncio
import logging
import threading
from typing import List, Set

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState


class ConnectionManager:
	"""Manages WebSocket connections for real-time updates."""
	
	def __init__(self):
		self.active_connections: Set[WebSocket] = set()
		self._log_buffer: List[str] = []
		self._loop: asyncio.AbstractEventLoop = None
		self._lock = threading.Lock()
	
	def set_loop(self, loop: asyncio.AbstractEventLoop):
		"""Set the event loop for async operations."""
		self._loop = loop
	
	async def connect(self, websocket: WebSocket):
		await websocket.accept()
		with self._lock:
			self.active_connections.add(websocket)
			# Send buffered logs to new connection
			for log in self._log_buffer[-50:]:  # Last 50 logs
				try:
					await websocket.send_json({"type": "log", "message": log})
				except Exception:
					pass
	
	def disconnect(self, websocket: WebSocket):
		with self._lock:
			self.active_connections.discard(websocket)
	
	def broadcast_log(self, message: str):
		"""Broadcast a log message to all connected clients (thread-safe)."""
		with self._lock:
			self._log_buffer.append(message)
			if len(self._log_buffer) > 100:
				self._log_buffer = self._log_buffer[-100:]
		
		if self._loop:
			try:
				asyncio.run_coroutine_threadsafe(self._broadcast_async("log", {"message": message}), self._loop)
			except Exception:
				pass
	
	async def broadcast_progress(self, progress: float, status: str):
		"""Broadcast processing progress to all connected clients."""
		await self._broadcast_async("progress", {"progress": progress, "status": status})
	
	async def broadcast_complete(self, output_path: str):
		"""Broadcast processing complete to all connected clients."""
		await self._broadcast_async("complete", {"output_path": output_path})

	def broadcast_progress_sync(self, progress: float, status: str, current_frame: int = 0, total_frames: int = 0, speed: float = 0.0, execution_providers: str = ''):
		"""Broadcast processing progress to all connected clients (thread-safe, sync)."""
		if self._loop:
			try:
				data = {
					"progress": progress,
					"status": status,
					"current_frame": current_frame,
					"total_frames": total_frames,
					"speed": speed,
					"execution_providers": execution_providers
				}
				asyncio.run_coroutine_threadsafe(self._broadcast_async("progress", data), self._loop)
			except Exception:
				pass

	def broadcast_log_sync(self, message: str):
		"""Broadcast log message to all connected clients (thread-safe, sync)."""
		if self._loop:
			try:
				asyncio.run_coroutine_threadsafe(self._broadcast_async("log", {"message": message}), self._loop)
			except Exception:
				pass

	async def _broadcast_async(self, msg_type: str, data: dict):
		"""Internal async broadcast."""
		message = {"type": msg_type, **data}
		disconnected = set()
		
		with self._lock:
			connections = list(self.active_connections)
			
		for connection in connections:
			try:
				if connection.client_state == WebSocketState.CONNECTED:
					await connection.send_json(message)
			except Exception:
				disconnected.add(connection)
		
		with self._lock:
			for conn in disconnected:
				self.active_connections.discard(conn)


# Global connection manager instance
manager = ConnectionManager()


class WebSocketLogHandler(logging.Handler):
	"""Custom logging handler that broadcasts logs to WebSocket clients."""
	
	def __init__(self, connection_manager: ConnectionManager):
		super().__init__()
		self.manager = connection_manager
	
	def emit(self, record):
		try:
			message = self.format(record)
			# print(f"DEBUG: WebSocketLogHandler emitting: {message}", flush=True)
			self.manager.broadcast_log_sync(message)
		except Exception as e:
			print(f"DEBUG: WebSocketLogHandler failed: {e}", flush=True)


def setup_logging():
	"""Set up the WebSocket log handler for facefusion logging."""
	facefusion_logger = logging.getLogger('facefusion')
	# Remove existing WebSocketLogHandlers to prevent duplicates on reload
	for handler in facefusion_logger.handlers[:]:
		if isinstance(handler, WebSocketLogHandler):
			facefusion_logger.removeHandler(handler)
			
	handler = WebSocketLogHandler(manager)
	handler.setFormatter(logging.Formatter('%(message)s'))
	facefusion_logger.addHandler(handler)


async def websocket_endpoint(websocket: WebSocket):
	"""WebSocket endpoint for real-time updates."""
	# Capture the running loop
	try:
		loop = asyncio.get_running_loop()
		manager.set_loop(loop)
	except Exception:
		pass
		
	await manager.connect(websocket)
	try:
		while True:
			# Keep connection alive, handle any client messages
			data = await websocket.receive_text()
			if data == "ping":
				await websocket.send_json({"type": "pong"})
	except WebSocketDisconnect:
		manager.disconnect(websocket)
	except Exception:
		manager.disconnect(websocket)

