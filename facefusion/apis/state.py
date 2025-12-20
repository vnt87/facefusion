from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from facefusion import args_store, asset_store, logger, state_manager


async def get_state(request : Request) -> JSONResponse:
	api_args = args_store.filter_api_args(state_manager.get_state()) #type:ignore[arg-type]
	return JSONResponse(state_manager.collect_state(api_args), status_code = HTTP_200_OK)


async def set_state(request : Request) -> JSONResponse:
	body = await request.json()
	action = request.query_params.get('action')

	if action == 'select':
		asset_type = request.query_params.get('asset_type')

		if not asset_type:
			return JSONResponse({'message': 'Missing required query parameter: asset_type'}, status_code = HTTP_400_BAD_REQUEST)

		if asset_type not in ['source', 'target']:
			return JSONResponse({'message': 'Invalid asset_type. Must be "source" or "target"'}, status_code = HTTP_400_BAD_REQUEST)

		if asset_type == 'source':
			asset_ids = body.get('asset_ids', [])

			if not isinstance(asset_ids, list):
				return JSONResponse({'message': 'asset_ids must be an array'}, status_code = HTTP_400_BAD_REQUEST)

			if not asset_ids:
				return JSONResponse({'message': 'asset_ids cannot be empty'}, status_code = HTTP_400_BAD_REQUEST)

			source_paths = []
			for asset_id in asset_ids:
				asset = asset_store.get_asset(asset_id)
				if not asset:
					return JSONResponse({'message': f'Source asset not found: {asset_id}'}, status_code = HTTP_404_NOT_FOUND)
				source_paths.append(asset['path'])

			state_manager.set_item('source_paths', source_paths)

			__api_args__ = args_store.filter_api_args(state_manager.get_state()) #type:ignore[arg-type]
			return JSONResponse(state_manager.collect_state(__api_args__), status_code = HTTP_200_OK)

		if asset_type == 'target':
			asset_id = body.get('asset_id')

			if not asset_id:
				return JSONResponse({'message': 'Missing required field: asset_id'}, status_code = HTTP_400_BAD_REQUEST)

			if not isinstance(asset_id, str):
				return JSONResponse({'message': 'asset_id must be a string'}, status_code = HTTP_400_BAD_REQUEST)

			asset = asset_store.get_asset(asset_id)
			if not asset:
				return JSONResponse({'message': f'Target asset not found: {asset_id}'}, status_code = HTTP_404_NOT_FOUND)

			state_manager.set_item('target_path', asset['path'])

			__api_args__ = args_store.filter_api_args(state_manager.get_state()) #type:ignore[arg-type]
			return JSONResponse(state_manager.collect_state(__api_args__), status_code = HTTP_200_OK)

	api_args = args_store.get_api_args()
	logger.info(f'[State] Normal update - body keys: {list(body.keys())}', __name__)

	for key, value in body.items():
		if key in api_args:
			state_manager.set_item(key, value)
			logger.debug(f'[State] Set {key} = {value}', __name__)
		else:
			logger.warn(f'[State] Skipped {key} (not in api_args)', __name__)

	__api_args__ = args_store.filter_api_args(state_manager.get_state()) #type:ignore[arg-type]
	return JSONResponse(state_manager.collect_state(__api_args__), status_code = HTTP_200_OK)
