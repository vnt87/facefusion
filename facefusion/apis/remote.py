import os
import tempfile
from typing import Any, Dict, List

import httpx
import yt_dlp  # type: ignore
from gallery_dl import config as gallery_config, extractor as gallery_extractor, job as gallery_job
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from facefusion import asset_store, logger
from facefusion.choices import audio_formats


def resolve_image_urls(url : str) -> List[str]:
	gallery_config.load()
	image_urls : List[str] = []

	try:
		for extractor_instance in gallery_extractor.extractors():
			if extractor_instance.pattern and extractor_instance.pattern.match(url):
				logger.info(f'Detected gallery URL using extractor: {extractor_instance.__name__}', __name__)
				extractor_obj = extractor_instance.from_url(url)

				if extractor_obj:
					for msg in extractor_obj:
						if isinstance(msg, tuple) and len(msg) >= 2:
							msg_type = msg[0]
							if msg_type == 5:
								image_data = msg[1]
								image_url = image_data.get('url')
								if image_url:
									image_urls.append(image_url)
				break

		if not image_urls:
			logger.info('Not a gallery URL, treating as direct image URL', __name__)
			image_urls = [url]

	except Exception as e:
		logger.error(f'Failed to extract image URLs: {e}', __name__)
		logger.info('Falling back to treating as direct image URL', __name__)
		image_urls = [url]

	return image_urls


def download_images_from_url(url : str, asset_type : str) -> List[str]:
	gallery_config.load()
	temp_dir = tempfile.gettempdir()
	asset_ids : List[str] = []

	is_gallery = False
	for extractor_instance in gallery_extractor.extractors():
		if extractor_instance.pattern and extractor_instance.pattern.match(url):
			logger.info(f'Detected gallery URL using extractor: {extractor_instance.__name__}', __name__)
			is_gallery = True

			output_dir = os.path.join(temp_dir, f'facefusion_gallery_{os.urandom(8).hex()}')
			os.makedirs(output_dir, exist_ok = True)

			gallery_config.set((), 'base-directory', output_dir)
			gallery_config.set((), 'skip', False)

			gdl_job = gallery_job.DownloadJob(url)
			gdl_job.run()

			for root, dirs, files in os.walk(output_dir):
				for filename in files:
					file_path = os.path.join(root, filename)
					asset_id = asset_store.register(asset_type, file_path, filename)
					asset_ids.append(asset_id)
					logger.info(f'Registered image as asset {asset_id}', __name__)

			break

	if not is_gallery:
		logger.info('Not a gallery URL, treating as direct image URL', __name__)
		with httpx.stream('GET', url, timeout = 30, follow_redirects = True) as response:
			response.raise_for_status()

			content_type = response.headers.get('content-type', '')
			if not content_type.startswith('image/'):
				raise ValueError(f'URL does not point to an image. Content-Type: {content_type}')

			file_extension = None
			if 'image/jpeg' in content_type or 'image/jpg' in content_type:
				file_extension = '.jpg'
			if 'image/png' in content_type:
				file_extension = '.png'
			if 'image/gif' in content_type:
				file_extension = '.gif'
			if 'image/webp' in content_type:
				file_extension = '.webp'

			if not file_extension:
				url_path = url.split('?')[0]
				if '.' in url_path:
					file_extension = '.' + url_path.split('.')[-1].lower()
				else:
					file_extension = '.jpg'

			filename = f'facefusion_image_{os.urandom(8).hex()}{file_extension}'
			file_path = os.path.join(temp_dir, filename)

			with open(file_path, 'wb') as f:
				for chunk in response.iter_bytes(chunk_size = 8192):
					f.write(chunk)

		asset_id = asset_store.register(asset_type, file_path, filename)
		asset_ids.append(asset_id)
		logger.info(f'Downloaded and registered image as asset {asset_id}', __name__)

	return asset_ids


def download_audio_from_url(url : str, asset_type : str) -> List[str]:
	temp_dir = tempfile.gettempdir()
	asset_ids : List[str] = []

	# Extract file extension from URL
	url_path = url.split('?')[0]
	url_extension = os.path.splitext(url_path)[1].lstrip('.')

	# Validate extension against supported audio formats
	if url_extension not in audio_formats:
		raise ValueError(f'Unsupported audio format: {url_extension}. Supported formats: {", ".join(audio_formats)}')

	logger.info(f'Downloading audio from URL with extension: {url_extension}', __name__)
	with httpx.stream('GET', url, timeout = 30, follow_redirects = True) as response:
		response.raise_for_status()

		filename = f'facefusion_audio_{os.urandom(8).hex()}.{url_extension}'
		file_path = os.path.join(temp_dir, filename)

		with open(file_path, 'wb') as f:
			for chunk in response.iter_bytes(chunk_size = 8192):
				f.write(chunk)

	asset_id = asset_store.register(asset_type, file_path, filename)
	asset_ids.append(asset_id)
	logger.info(f'Downloaded and registered audio as asset {asset_id}', __name__)

	return asset_ids


async def remote(request : Request) -> JSONResponse:
	body = await request.json()
	url = body.get('url')
	action = request.query_params.get('action')
	media_type = request.query_params.get('media_type', 'video')
	asset_type = request.query_params.get('asset_type', 'target')

	if not action:
		return JSONResponse({'message': 'No action provided. Must be "resolve" or "download"'}, status_code = HTTP_400_BAD_REQUEST)

	if action not in ['resolve', 'download']:
		return JSONResponse({'message': 'Invalid action. Must be "resolve" or "download"'}, status_code = HTTP_400_BAD_REQUEST)

	if media_type not in ['image', 'video', 'audio']:
		return JSONResponse({'message': 'Invalid media_type. Must be "image", "video", or "audio"'}, status_code = HTTP_400_BAD_REQUEST)

	if asset_type not in ['source', 'target']:
		return JSONResponse({'message': 'Invalid asset_type. Must be "source" or "target"'}, status_code = HTTP_400_BAD_REQUEST)

	if not url:
		return JSONResponse({'message': 'No URL provided'}, status_code = HTTP_400_BAD_REQUEST)

	if not isinstance(url, str):
		return JSONResponse({'message': 'URL must be a string'}, status_code = HTTP_400_BAD_REQUEST)

	url = url.strip()

	if not url.startswith('http://') and not url.startswith('https://'):
		return JSONResponse({'message': 'URL must start with http:// or https://'}, status_code = HTTP_400_BAD_REQUEST)

	quality = body.get('quality', '720p')

	if quality not in ['360p', '480p', '720p', '1080p']:
		return JSONResponse({'message': 'Quality must be 360p, 480p, 720p, or 1080p'}, status_code = HTTP_400_BAD_REQUEST)

	if action == 'resolve':
		if media_type == 'image':
			image_urls = resolve_image_urls(url)
			logger.info(f'Resolved {len(image_urls)} image URL(s)', __name__)

			response_data =\
			{
				'message': 'Image URL(s) resolved successfully',
				'image_urls': image_urls,
				'count': len(image_urls)
			}

			return JSONResponse(response_data, status_code = HTTP_200_OK)

		quality_map =\
		{
			'360p': 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]',
			'480p': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]',
			'720p': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]',
			'1080p': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]'
		}

		ydl_opts : Dict[str, Any] =\
		{
			'format': quality_map[quality],
			'quiet': True,
			'no_warnings': True
		}

		logger.info(f'Extracting stream URL from {url} at {quality}', __name__)

		try:
			ydl = yt_dlp.YoutubeDL(ydl_opts)
			info = ydl.extract_info(url, download = False)
		except Exception as e:
			logger.error(f'Failed to extract video information: {e}', __name__)
			return JSONResponse({'message': f'Failed to extract video information: {str(e)}'}, status_code = HTTP_500_INTERNAL_SERVER_ERROR)

		if not info:
			logger.error('Failed to extract video information', __name__)
			return JSONResponse({'message': 'Failed to extract video information'}, status_code = HTTP_500_INTERNAL_SERVER_ERROR)

		stream_url = info.get('url')

		if not stream_url:
			if 'requested_formats' in info and len(info['requested_formats']) > 0:
				stream_url = info['requested_formats'][0].get('url')
				logger.info('Using URL from requested_formats (video track)', __name__)
			elif 'formats' in info and len(info['formats']) > 0:
				for fmt in reversed(info['formats']):
					if fmt.get('url') and fmt.get('vcodec') != 'none':
						stream_url = fmt['url']
						logger.info(f'Using URL from format: {fmt.get("format_id")}', __name__)
						break

		if not stream_url:
			logger.error('No stream URL found in any format', __name__)
			logger.debug(f'Available keys in info: {list(info.keys())}', __name__)
			return JSONResponse({'message': 'No stream URL found'}, status_code = HTTP_500_INTERNAL_SERVER_ERROR)

		audio_url = None
		if 'requested_formats' in info and len(info['requested_formats']) > 1:
			audio_url = info['requested_formats'][1].get('url')
			if audio_url:
				logger.info('Found separate audio track URL', __name__)

		duration = info.get('duration')
		fps = info.get('fps')
		width = info.get('width')
		height = info.get('height')

		total_frames = None
		if duration and fps:
			total_frames = int(duration * fps)
			logger.info(f'Calculated total frames: {total_frames} ({duration}s * {fps} fps)', __name__)

		logger.info('Stream URL extracted successfully', __name__)

		response_data =\
		{
			'message': 'Stream URL resolved successfully',
			'stream_url': stream_url,
			'audio_url': audio_url,
			'duration': duration,
			'fps': fps,
			'total_frames': total_frames,
			'width': width,
			'height': height
		}

		return JSONResponse(response_data, status_code = HTTP_200_OK)

	if action == 'download':
		if media_type == 'image':
			try:
				asset_ids = download_images_from_url(url, asset_type)
			except ValueError as e:
				return JSONResponse({'message': str(e)}, status_code = HTTP_400_BAD_REQUEST)
			except Exception as e:
				logger.error(f'Failed to download image(s): {e}', __name__)
				return JSONResponse({'message': f'Failed to download image(s): {str(e)}'}, status_code = HTTP_500_INTERNAL_SERVER_ERROR)

			response_data =\
			{
				'message': f'Downloaded and registered {len(asset_ids)} image(s)',
				'asset_ids': asset_ids,
				'count': len(asset_ids)
			}

			return JSONResponse(response_data, status_code = HTTP_201_CREATED)

		if media_type == 'audio':
			try:
				asset_ids = download_audio_from_url(url, asset_type)
			except ValueError as e:
				return JSONResponse({'message': str(e)}, status_code = HTTP_400_BAD_REQUEST)
			except Exception as e:
				logger.error(f'Failed to download audio: {e}', __name__)
				return JSONResponse({'message': f'Failed to download audio: {str(e)}'}, status_code = HTTP_500_INTERNAL_SERVER_ERROR)

			response_data =\
			{
				'message': f'Downloaded and registered {len(asset_ids)} audio file(s)',
				'asset_ids': asset_ids,
				'count': len(asset_ids)
			}

			return JSONResponse(response_data, status_code = HTTP_201_CREATED)

		quality_map =\
		{
			'360p': 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/best[height<=360]',
			'480p': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best[height<=480]',
			'720p': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]',
			'1080p': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]'
		}

		temp_dir = tempfile.gettempdir()
		output_path = os.path.join(temp_dir, 'facefusion_remote_%(id)s.%(ext)s')

		download_opts : Dict[str, Any] =\
		{
			'format': quality_map[quality],
			'outtmpl': output_path,
			'quiet': False,
			'no_warnings': False
		}

		logger.info(f'Downloading video from {url} at {quality}', __name__)

		ydl = yt_dlp.YoutubeDL(download_opts)
		info = ydl.extract_info(url, download = True)

		if not info:
			logger.error('Failed to download video', __name__)
			return JSONResponse({'message': 'Failed to download video'}, status_code = HTTP_500_INTERNAL_SERVER_ERROR)

		downloaded_file = ydl.prepare_filename(info)
		if not os.path.exists(downloaded_file):
			logger.error(f'Downloaded file not found: {downloaded_file}', __name__)
			return JSONResponse({'message': 'Downloaded file not found'}, status_code = HTTP_500_INTERNAL_SERVER_ERROR)

		duration = info.get('duration')
		fps = info.get('fps')
		width = info.get('width')
		height = info.get('height')

		total_frames = None
		if duration and fps:
			total_frames = int(duration * fps)
			logger.info(f'Calculated total frames: {total_frames} ({duration}s * {fps} fps)', __name__)

		filename = os.path.basename(downloaded_file)
		metadata =\
		{
			'frame_total': total_frames,
			'fps': fps,
			'resolution': (width, height) if width and height else None,
			'duration': duration
		}

		asset_id = asset_store.register(asset_type, downloaded_file, filename, metadata)
		logger.info(f'Video downloaded and registered as asset {asset_id}', __name__)

		response_data =\
		{
			'message': 'Video downloaded and registered as asset',
			'asset_id': asset_id,
			'metadata':
			{
				'duration': duration,
				'fps': fps,
				'total_frames': total_frames,
				'width': width,
				'height': height
			}
		}

		return JSONResponse(response_data, status_code = HTTP_201_CREATED)

	return JSONResponse({'message': 'Invalid request'}, status_code = HTTP_400_BAD_REQUEST)
