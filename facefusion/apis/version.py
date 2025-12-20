import subprocess
from functools import lru_cache
from typing import Optional

from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.websockets import WebSocket


@lru_cache(maxsize = 1)
def get_api_version() -> str:
	try:
		result = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output = True, text = True, check = True)
		return result.stdout.strip()
	except Exception:
		return 'unknown'


def check_version_match(request : Request) -> Optional[JSONResponse]:
	client_version = request.headers.get('X-API-Version')
	server_version = get_api_version()

	if not client_version:
		return JSONResponse({'error': 'Missing X-API-Version header', 'server_version': server_version}, status_code = 400)

	if client_version != server_version:
		return JSONResponse({'error': 'Version mismatch', 'client_version': client_version, 'server_version': server_version}, status_code = 409)

	return None


def check_version_match_websocket(websocket : WebSocket) -> Optional[str]:
	client_version = websocket.headers.get('X-API-Version')
	server_version = get_api_version()

	if not client_version:
		return f'Missing X-API-Version header, server version: {server_version}'

	if client_version != server_version:
		return f'Version mismatch: client={client_version}, server={server_version}'

	return None


async def version_guard_middleware(scope : Scope, receive : Receive, send : Send, app : ASGIApp) -> None:
	if scope['type'] == 'http':
		# Skip version check for OPTIONS requests (CORS preflight)
		if scope.get('method') == 'OPTIONS':
			await app(scope, receive, send)
			return

		headers = Headers(scope = scope)
		client_version = headers.get('X-API-Version')
		server_version = get_api_version()

		if not client_version:
			response = JSONResponse({'error': 'Missing X-API-Version header', 'server_version': server_version}, status_code = 400)
			await response(scope, receive, send)
			return

		if client_version != server_version:
			response = JSONResponse({'error': 'Version mismatch', 'client_version': client_version, 'server_version': server_version}, status_code = 409)
			await response(scope, receive, send)
			return

	if scope['type'] == 'websocket':
		headers = Headers(scope = scope)
		client_version = headers.get('X-API-Version')

		# For WebSocket connections, also check subprotocols since browsers can't set custom headers
		if not client_version:
			protocol_header = headers.get('Sec-WebSocket-Protocol')
			if protocol_header:
				# Parse subprotocols to find api_version
				protocols = [p.strip() for p in protocol_header.split(',')]
				for protocol in protocols:
					if protocol.startswith('api_version.'):
						client_version = protocol.split('.', 1)[1]
						break

		server_version = get_api_version()

		if not client_version or client_version != server_version:
			websocket = WebSocket(scope, receive = receive, send = send)
			reason = f'Missing X-API-Version header, server version: {server_version}' if not client_version else f'Version mismatch: client={client_version}, server={server_version}'
			await websocket.close(code = 1008, reason = reason)
			return

	await app(scope, receive, send)


def create_version_guard(app : ASGIApp) -> ASGIApp:
	async def version_guard_app(scope : Scope, receive : Receive, send : Send) -> None:
		await version_guard_middleware(scope, receive, send, app)

	return version_guard_app
