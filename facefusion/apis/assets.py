import os
import tempfile

from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from facefusion import asset_store, filesystem, logger
from facefusion.vision import count_video_frame_total, detect_video_fps, detect_video_resolution


async def upload_asset(request : Request) -> JSONResponse:
	asset_type = request.query_params.get('type')

	if not asset_type:
		return JSONResponse({'message': 'Missing required query parameter: type'}, status_code = HTTP_400_BAD_REQUEST)

	if asset_type not in ['source', 'target']:
		return JSONResponse({'message': 'Invalid type. Must be "source" or "target"'}, status_code = HTTP_400_BAD_REQUEST)

	form = await request.form()

	if asset_type == 'source':
		files = form.getlist('file')

		if not files:
			return JSONResponse({'message': 'No file provided'}, status_code = HTTP_400_BAD_REQUEST)

		asset_ids = []

		for file in files:
			filename = file.filename if hasattr(file, 'filename') else 'source.jpg'
			file_extension = os.path.splitext(filename)[1] if filename else '.jpg'

			with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
				content = await file.read()
				temp_file.write(content)
				file_path = temp_file.name

			if not (filesystem.is_image(file_path) or filesystem.is_video(file_path) or filesystem.is_audio(file_path)):
				if os.path.exists(file_path):
					os.remove(file_path)
				return JSONResponse(
					{
						'message': 'Unsupported file format. Allowed formats - Images: bmp, jpeg, png, tiff, webp. Videos: avi, m4v, mkv, mov, mp4, mpeg, mxf, webm, wmv.'
					},
					status_code = HTTP_400_BAD_REQUEST
				)

			asset_id = asset_store.register('source', file_path, filename)
			asset_ids.append(asset_id)

		logger.debug(f'Uploaded {len(asset_ids)} source(s)', __name__)

		return JSONResponse(
			{
				'message': f'{len(asset_ids)} source(s) uploaded successfully',
				'asset_ids': asset_ids
			},
			status_code = HTTP_201_CREATED
		)

	if asset_type == 'target':
		file = form.get('file')

		if not file:
			return JSONResponse({'message': 'No file provided'}, status_code = HTTP_400_BAD_REQUEST)

		if isinstance(file, str):
			return JSONResponse({'message': 'Expected file upload, got string. Use /stream/target for URLs'}, status_code = HTTP_400_BAD_REQUEST)

		if not hasattr(file, 'filename'):
			return JSONResponse({'message': 'Invalid file object'}, status_code = HTTP_400_BAD_REQUEST)

		filename = file.filename
		file_extension = os.path.splitext(filename)[1] if filename else '.jpg'

		with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
			content = await file.read()
			temp_file.write(content)
			file_path = temp_file.name

		if not (filesystem.is_image(file_path) or filesystem.is_video(file_path) or filesystem.is_audio(file_path)):
			if os.path.exists(file_path):
				os.remove(file_path)
			return JSONResponse(
				{
					'message': 'Unsupported file format. Allowed formats - Images: bmp, jpeg, png, tiff, webp. Videos: avi, m4v, mkv, mov, mp4, mpeg, mxf, webm, wmv.'
				},
				status_code = HTTP_400_BAD_REQUEST
			)

		metadata = None

		if filesystem.is_video(file_path):
			frame_total = count_video_frame_total(file_path)
			fps = detect_video_fps(file_path)
			resolution = detect_video_resolution(file_path)
			metadata =\
			{
				'frame_total': frame_total,
				'fps': fps,
				'resolution': resolution
			}
			logger.debug(f'Video metadata - frames: {frame_total}, fps: {fps}, resolution: {resolution}', __name__)

		asset_id = asset_store.register('target', file_path, filename, metadata)

		logger.debug(f'Target uploaded with asset_id: {asset_id}', __name__)

		return JSONResponse(
			{
				'message': 'Target uploaded successfully',
				'asset_id': asset_id
			},
			status_code = HTTP_201_CREATED
		)


async def list_all_assets(request : Request) -> JSONResponse:
	asset_type = request.query_params.get('type')
	media_type = request.query_params.get('media_type')
	format = request.query_params.get('format')

	assets = asset_store.list_assets(asset_type)

	if media_type:
		assets = [a for a in assets if a.get('media_type') == media_type]

	if format:
		assets = [a for a in assets if a.get('format') == format]

	safe_assets = []
	for asset in assets:
		safe_asset = {k: v for k, v in asset.items() if k != 'path'}
		safe_assets.append(safe_asset)

	return JSONResponse({'assets': safe_assets, 'count': len(safe_assets)}, status_code = HTTP_200_OK)


async def get_asset_by_id(request : Request) -> JSONResponse | FileResponse:
	from facefusion.session_context import get_session_id

	asset_id = request.path_params.get('asset_id')
	action = request.query_params.get('action')
	asset = asset_store.get_asset(asset_id)

	if not asset:
		return JSONResponse({'message': 'Asset not found'}, status_code = HTTP_404_NOT_FOUND)

	if asset.get('session_id') != get_session_id():
		return JSONResponse({'message': 'Asset not found'}, status_code = HTTP_404_NOT_FOUND)

	if action == 'download':
		file_path = asset.get('path')

		if not file_path or not os.path.exists(file_path):
			return JSONResponse({'message': 'Asset file not found'}, status_code = HTTP_404_NOT_FOUND)

		filename = asset.get('filename', 'download')

		return FileResponse(file_path, filename = filename)

	safe_asset = {k: v for k, v in asset.items() if k != 'path'}

	return JSONResponse(safe_asset, status_code = HTTP_200_OK)


async def delete_asset_by_id(request : Request) -> JSONResponse:
	from facefusion.session_context import get_session_id

	asset_id = request.path_params.get('asset_id')
	asset = asset_store.get_asset(asset_id)

	if not asset:
		return JSONResponse({'message': 'Asset not found'}, status_code = HTTP_404_NOT_FOUND)

	if asset.get('session_id') != get_session_id():
		return JSONResponse({'message': 'Asset not found'}, status_code = HTTP_404_NOT_FOUND)

	success = asset_store.delete_asset(asset_id)

	if not success:
		return JSONResponse({'message': 'Asset not found'}, status_code = HTTP_404_NOT_FOUND)

	return JSONResponse({'message': 'Asset deleted successfully'}, status_code = HTTP_200_OK)
