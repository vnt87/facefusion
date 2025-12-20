import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypeAlias

from facefusion import filesystem, state_manager
from facefusion.session_context import get_session_id

AssetRegistry : TypeAlias = Dict[str, Dict[str, Any]]


def get_asset_registry() -> AssetRegistry:
	registry = state_manager.get_item('asset_registry')
	if not registry:
		registry = {}
		state_manager.set_item('asset_registry', registry)
	return registry


def register(asset_type : str, file_path : str, filename : str = None, metadata : Optional[Dict[str, Any]] = None) -> str:
	if asset_type not in ['source', 'target', 'output']:
		raise ValueError(f"Invalid asset_type: {asset_type}. Must be 'source', 'target', or 'output'")

	asset_id = str(uuid.uuid4())
	session_id = get_session_id()

	if not session_id:
		raise ValueError("No active session - cannot register asset without session_id")

	if not filename:
		filename = os.path.basename(file_path)

	file_size = os.path.getsize(file_path)
	file_format = filesystem.get_file_format(file_path)
	media_type = None

	if filesystem.is_image(file_path):
		media_type = 'image'
	if filesystem.is_video(file_path):
		media_type = 'video'
	if filesystem.is_audio(file_path):
		media_type = 'audio'

	asset_data =\
	{
		'id': asset_id,
		'session_id': session_id,
		'type': asset_type,
		'media_type': media_type,
		'format': file_format,
		'path': file_path,
		'filename': filename,
		'size': file_size,
		'created_at': datetime.now(timezone.utc).isoformat()
	}

	if metadata:
		asset_data['metadata'] = metadata

	registry = get_asset_registry()
	registry[asset_id] = asset_data
	state_manager.set_item('asset_registry', registry)

	return asset_id


def get_asset(asset_id : str) -> Optional[Dict[str, Any]]:
	registry = get_asset_registry()
	return registry.get(asset_id)


def list_assets(asset_type : Optional[str] = None) -> List[Dict[str, Any]]:
	registry = get_asset_registry()
	session_id = get_session_id()

	assets = list(registry.values())

	if session_id:
		assets = [a for a in assets if a.get('session_id') == session_id]

	if asset_type:
		if asset_type not in ['source', 'target', 'output']:
			raise ValueError(f"Invalid asset_type: {asset_type}")
		assets = [a for a in assets if a.get('type') == asset_type]

	return assets


def delete_asset(asset_id : str) -> bool:
	registry = get_asset_registry()
	asset = registry.get(asset_id)

	if not asset:
		return False

	file_path = asset.get('path')
	if file_path and os.path.exists(file_path):
		os.remove(file_path)

	del registry[asset_id]
	state_manager.set_item('asset_registry', registry)

	return True


def cleanup_session_assets(session_id : str) -> None:
	registry = get_asset_registry()
	assets_to_delete = [aid for aid, asset in registry.items() if asset.get('session_id') == session_id]

	for asset_id in assets_to_delete:
		delete_asset(asset_id)
