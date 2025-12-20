import asyncio
from functools import lru_cache
from typing import Any, Dict, Optional, cast

from starlette.datastructures import Headers
from starlette.websockets import WebSocket, WebSocketDisconnect

from facefusion import state_manager
from facefusion.execution import detect_execution_devices
from facefusion.system import get_cpu_info, get_disk_info, get_load_average, get_network_info
from facefusion.system import get_operating_system_info, get_python_info, get_ram_info, get_temperature_info
from facefusion.types import SystemInfo


@lru_cache(maxsize = 1)
def get_cached_static_system_info() -> Dict[str, Any]:
	return\
	{
		'operating_system': get_operating_system_info(),
		'python': get_python_info()
	}


@lru_cache(maxsize = 1)
def get_cached_semi_static_system_info(temp_path : Optional[str]) -> Dict[str, Any]:
	return\
	{
		'disk': get_disk_info(temp_path),
		'network': get_network_info()
	}


def get_optimized_system_info(temp_path : Optional[str] = None) -> SystemInfo:
	static_data = get_cached_static_system_info()
	semi_static_data = get_cached_semi_static_system_info(temp_path)
	dynamic_data : Dict[str, Any] =\
	{
		'cpu': get_cpu_info(),
		'ram': get_ram_info(),
		'temperatures': get_temperature_info(),
		'load_average': get_load_average()
	}

	return cast(SystemInfo, {**static_data, **semi_static_data, **dynamic_data})


async def websocket_metrics(websocket : WebSocket) -> None:
	subprotocol = get_requested_subprotocol(websocket)
	await websocket.accept(subprotocol = subprotocol)

	try:
		while True:
			temp_path = state_manager.get_temp_path()
			execution_devices = detect_execution_devices()
			system_info = get_optimized_system_info(temp_path)
			metrics =\
			{
				'devices': execution_devices,
				'system': system_info
			}
			await websocket.send_json(metrics)
			await asyncio.sleep(2)

	except (WebSocketDisconnect, Exception):
		pass


def get_requested_subprotocol(websocket : WebSocket) -> Optional[str]:
	headers = Headers(scope = websocket.scope)
	protocol_header = headers.get('Sec-WebSocket-Protocol')

	if protocol_header:
		protocol, _, _ = protocol_header.partition(',')
		return protocol.strip()

	return None
