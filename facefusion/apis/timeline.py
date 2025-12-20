import base64
import subprocess
from typing import List, Optional

import cv2
import numpy
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from facefusion import logger
from facefusion.asset_store import get_asset
from facefusion.filesystem import is_video
from facefusion.video_manager import get_video_capture
from facefusion.vision import fit_contain_frame


def extract_frame_at_timestamp(stream_url : str, timestamp : float, width : int, height : int) -> Optional[numpy.ndarray]:
	ffmpeg_command =\
	[
		'ffmpeg',
		'-user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
		'-ss', str(timestamp),
		'-i', stream_url,
		'-vf', f'scale={width}:{height}',
		'-frames:v', '1',
		'-f', 'rawvideo',
		'-pix_fmt', 'bgr24',
		'-'
	]

	try:
		result = subprocess.run(ffmpeg_command, capture_output = True, timeout = 10)
		if result.returncode == 0 and result.stdout:
			frame_size = width * height * 3
			if len(result.stdout) >= frame_size:
				frame = numpy.frombuffer(result.stdout[:frame_size], dtype = numpy.uint8).reshape((height, width, 3))
				return frame
	except Exception as e:
		logger.debug(f'Failed to extract frame at {timestamp}s: {e}', __name__)

	return None


async def get_timeline(request: Request) -> JSONResponse:
    """
    Return N preview frames (as base64 JPEGs) from the target video,
    resized to specified resolution for timeline preview.

    Route: /timeline/{count:int}?target_path=...&is_remote_stream=true&duration=120&fps=30&target_width=1920&target_height=1080&width=160&height=120
    """

    # Extract and validate requested count
    try:
        count = int(request.path_params.get('count', 0))
    except (TypeError, ValueError):
        return JSONResponse({'message': 'Invalid count parameter'}, status_code=HTTP_400_BAD_REQUEST)

    if count <= 0:
        return JSONResponse({'message': 'Count must be a positive integer'}, status_code=HTTP_400_BAD_REQUEST)

    # Extract and validate preview resolution parameters
    try:
        preview_width = int(request.query_params.get('width', 160))
        preview_height = int(request.query_params.get('height', 120))
    except (TypeError, ValueError):
        return JSONResponse({'message': 'Invalid width or height parameter'}, status_code=HTTP_400_BAD_REQUEST)

    if preview_width <= 0 or preview_height <= 0 or preview_width > 1920 or preview_height > 1080:
        return JSONResponse({'message': 'Width and height must be between 1 and 1920x1080'}, status_code=HTTP_400_BAD_REQUEST)

    # Extract target_path or asset_id (one is required)
    target_path = request.query_params.get('target_path')
    asset_id = request.query_params.get('asset_id')

    # Extract is_remote_stream flag
    is_remote_stream_param = request.query_params.get('is_remote_stream', 'false').lower()
    is_remote_stream = is_remote_stream_param in ['true', '1', 'yes']

    # Resolve asset_id to path if provided (for local files)
    if asset_id and not target_path:
        from facefusion.session_context import get_session_id

        asset = get_asset(asset_id)
        if not asset:
            return JSONResponse({'message': f'Asset not found: {asset_id}'}, status_code=HTTP_400_BAD_REQUEST)

        # Verify asset belongs to current session (security)
        if asset.get('session_id') != get_session_id():
            return JSONResponse({'message': 'Asset not found'}, status_code=HTTP_400_BAD_REQUEST)

        target_path = asset.get('path')
        if not target_path:
            return JSONResponse({'message': 'Asset has no path'}, status_code=HTTP_400_BAD_REQUEST)

        is_remote_stream = False  # Assets are always local files
        logger.debug(f'Resolved asset_id {asset_id} to path for timeline preview', __name__)

    # Now check if we have a target_path
    if not target_path:
        return JSONResponse({'message': 'Missing required parameter: either target_path or asset_id'}, status_code=HTTP_400_BAD_REQUEST)

    # Extract video metadata (optional for local files, required for remote streams)
    duration = None
    fps = None
    width = 1280
    height = 720

    if request.query_params.get('duration'):
        try:
            duration = float(request.query_params.get('duration'))
        except (TypeError, ValueError):
            return JSONResponse({'message': 'Invalid duration parameter'}, status_code=HTTP_400_BAD_REQUEST)

    if request.query_params.get('fps'):
        try:
            fps = float(request.query_params.get('fps'))
        except (TypeError, ValueError):
            return JSONResponse({'message': 'Invalid fps parameter'}, status_code=HTTP_400_BAD_REQUEST)

    if request.query_params.get('target_width'):
        try:
            width = int(request.query_params.get('target_width'))
        except (TypeError, ValueError):
            return JSONResponse({'message': 'Invalid target_width parameter'}, status_code=HTTP_400_BAD_REQUEST)

    if request.query_params.get('target_height'):
        try:
            height = int(request.query_params.get('target_height'))
        except (TypeError, ValueError):
            return JSONResponse({'message': 'Invalid target_height parameter'}, status_code=HTTP_400_BAD_REQUEST)

    previews: List[str] = []

    if is_remote_stream:
        if not duration or duration <= 0:
            return JSONResponse({'message': 'Duration not available for remote stream'}, status_code=HTTP_400_BAD_REQUEST)

        frame_total = 0
        if duration and fps:
            try:
                frame_total = int(float(duration) * float(fps))
            except Exception:
                frame_total = 0

        sample_count = min(count, frame_total) if frame_total > 0 else count
        timestamps = list(numpy.linspace(0, float(duration), num=sample_count, endpoint=False))

        logger.info(f'Extracting {sample_count} frames from remote stream using ffmpeg', __name__)

        for timestamp in timestamps:
            frame = extract_frame_at_timestamp(target_path, timestamp, width, height)
            if frame is None:
                logger.warn(f'Failed to extract frame at {timestamp}s', __name__)
                continue

            thumb_bgr = fit_contain_frame(frame, (preview_width, preview_height))
            if thumb_bgr.shape[1] != preview_width or thumb_bgr.shape[0] != preview_height:
                thumb_bgr = cv2.resize(thumb_bgr, (preview_width, preview_height))

            ok_enc, buf = cv2.imencode('.jpg', thumb_bgr, [cv2.IMWRITE_JPEG_QUALITY, 50])
            if not ok_enc:
                logger.warn(f'JPEG encode failed for timestamp {timestamp}s', __name__)
                continue

            b64 = base64.b64encode(buf.tobytes()).decode('ascii')
            previews.append(b64)
    else:
        video_capture = get_video_capture(target_path)
        if not video_capture or not video_capture.isOpened():
            logger.error(f'Unable to open video capture for target: {target_path}', __name__)
            return JSONResponse({'message': 'Unable to open target video'}, status_code=HTTP_400_BAD_REQUEST)

        frame_total = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        if frame_total <= 0 and is_video(target_path):
            return JSONResponse({'message': 'Could not determine frame count for target video'}, status_code=HTTP_400_BAD_REQUEST)

        sample_count = min(count, frame_total)
        indices: List[int] = list(numpy.linspace(1, frame_total, num=sample_count, endpoint=True, dtype=int))

        for frame_number in indices:
            video_capture.set(cv2.CAP_PROP_POS_FRAMES, max(0, frame_number - 1))
            ok_read, frame = video_capture.read()
            if not ok_read or frame is None:
                logger.warn(f'Failed reading frame {frame_number}', __name__)
                continue

            thumb_bgr = fit_contain_frame(frame, (preview_width, preview_height))
            if thumb_bgr.shape[1] != preview_width or thumb_bgr.shape[0] != preview_height:
                thumb_bgr = cv2.resize(thumb_bgr, (preview_width, preview_height))

            ok_enc, buf = cv2.imencode('.jpg', thumb_bgr, [cv2.IMWRITE_JPEG_QUALITY, 50])
            if not ok_enc:
                logger.warn(f'JPEG encode failed for frame {frame_number}', __name__)
                continue
            b64 = base64.b64encode(buf.tobytes()).decode('ascii')
            previews.append(b64)

    logger.info(f'Returned {len(previews)}/{sample_count} timeline frames at {preview_width}x{preview_height}', __name__)

    return JSONResponse({
        'message': 'ok',
        'count': len(previews),
        'requested': count,
        'width': preview_width,
        'height': preview_height,
        'format': 'jpeg',
        'frames': previews
    }, status_code=HTTP_200_OK)
