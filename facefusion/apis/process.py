import asyncio
import fractions
import subprocess
from functools import partial
from typing import Any, List, Optional, Set, TypeAlias

import cv2
import numpy
from aiortc import AudioStreamTrack, RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.codecs import h264
from av import AudioFrame, VideoFrame
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.websockets import WebSocket

from facefusion import config, content_analyser, logger, state_manager
from facefusion.streamer import process_stream_frame
from facefusion.vision import obscure_frame

PeerConnectionSet : TypeAlias = Set[RTCPeerConnection]
ResolutionTuple : TypeAlias = tuple[int, int]

NSFW_LOCK = False

pcs : PeerConnectionSet = set()

RESOLUTION_MAP : dict[str, ResolutionTuple] =\
{
	'480p': (640, 480),
	'720p': (1280, 720),
	'1080p': (1920, 1080)
}


def init_default_state() -> None:
	if state_manager.get_item('execution_providers') is None:
		state_manager.set_item('execution_providers', config.get_str_list('execution', 'execution_providers', 'cuda'))
	if state_manager.get_item('execution_thread_count') is None:
		state_manager.set_item('execution_thread_count', config.get_int_value('execution', 'execution_thread_count', '32'))
	if state_manager.get_item('face_detector_model') is None:
		state_manager.set_item('face_detector_model', config.get_str_value('face_detector', 'face_detector_model', 'yolo_face'))
	if state_manager.get_item('face_detector_size') is None:
		state_manager.set_item('face_detector_size', config.get_str_value('face_detector', 'face_detector_size', '640x640'))
	if state_manager.get_item('face_detector_margin') is None:
		state_manager.set_item('face_detector_margin', config.get_int_list('face_detector', 'face_detector_margin', '0 0 0 0'))
	if state_manager.get_item('face_detector_angles') is None:
		state_manager.set_item('face_detector_angles', config.get_int_list('face_detector', 'face_detector_angles', '0'))
	if state_manager.get_item('face_detector_score') is None:
		state_manager.set_item('face_detector_score', config.get_float_value('face_detector', 'face_detector_score', '0.5'))
	if state_manager.get_item('face_landmarker_model') is None:
		state_manager.set_item('face_landmarker_model', config.get_str_value('face_landmarker', 'face_landmarker_model', '2dfan4'))
	if state_manager.get_item('face_landmarker_score') is None:
		state_manager.set_item('face_landmarker_score', config.get_float_value('face_landmarker', 'face_landmarker_score', '0.5'))
	if state_manager.get_item('face_selector_mode') is None:
		state_manager.set_item('face_selector_mode', config.get_str_value('face_selector', 'face_selector_mode', 'many'))
	if state_manager.get_item('face_selector_order') is None:
		state_manager.set_item('face_selector_order', config.get_str_value('face_selector', 'face_selector_order', 'large-small'))
	if state_manager.get_item('face_mask_types') is None:
		state_manager.set_item('face_mask_types', config.get_str_list('face_masker', 'face_mask_types', 'occlusion'))
	if state_manager.get_item('face_mask_blur') is None:
		state_manager.set_item('face_mask_blur', config.get_float_value('face_masker', 'face_mask_blur', '0.3'))
	if state_manager.get_item('face_mask_padding') is None:
		state_manager.set_item('face_mask_padding', config.get_int_list('face_masker', 'face_mask_padding', '0 0 0 0'))
	if state_manager.get_item('face_swapper_model') is None:
		state_manager.set_item('face_swapper_model', config.get_str_value('processors', 'face_swapper_model', 'hyperswap_1a_256'))
	if state_manager.get_item('face_swapper_pixel_boost') is None:
		state_manager.set_item('face_swapper_pixel_boost', config.get_str_value('processors', 'face_swapper_pixel_boost', '256x256'))
	if state_manager.get_item('face_swapper_weight') is None:
		state_manager.set_item('face_swapper_weight', config.get_float_value('processors', 'face_swapper_weight', '0.5'))
	if state_manager.get_item('face_enhancer_model') is None:
		state_manager.set_item('face_enhancer_model', config.get_str_value('processors', 'face_enhancer_model', 'gfpgan_1.4'))
	if state_manager.get_item('face_enhancer_blend') is None:
		state_manager.set_item('face_enhancer_blend', config.get_int_value('processors', 'face_enhancer_blend', '80'))
	if state_manager.get_item('frame_enhancer_model') is None:
		state_manager.set_item('frame_enhancer_model', config.get_str_value('processors', 'frame_enhancer_model', 'real_esrgan_x2'))
	if state_manager.get_item('frame_enhancer_blend') is None:
		state_manager.set_item('frame_enhancer_blend', config.get_int_value('processors', 'frame_enhancer_blend', '80'))
	if state_manager.get_item('face_debugger_items') is None:
		state_manager.set_item('face_debugger_items', config.get_str_list('processors', 'face_debugger_items', 'kps'))
	logger.debug(f'Initialized state - execution_providers: {state_manager.get_item("execution_providers")}', __name__)


def setup_bitrate_config(bitrate : int, encoder : str, mode_prefix : str = 'WebRTC') -> tuple[int, bool]:
	if bitrate == 0:
		bitrate_bps = 100000
		h264.DEFAULT_BITRATE = bitrate_bps
		h264.MIN_BITRATE = 100000
		h264.MAX_BITRATE = 2000000
		logger.info(
			f'{mode_prefix} setup: mode=auto, encoder={encoder}, '
			f'DEF={h264.DEFAULT_BITRATE / 1000} kbps, '
			f'MIN={h264.MIN_BITRATE / 1000} kbps, MAX={h264.MAX_BITRATE / 1000} kbps',
			__name__
		)
		adaptive_bitrate = True
	else:
		bitrate_bps = bitrate * 1000
		h264.DEFAULT_BITRATE = bitrate_bps
		h264.MIN_BITRATE = max(500000, bitrate_bps // 2)
		h264.MAX_BITRATE = max(bitrate_bps * 2, 3000000)
		logger.info(
			f'{mode_prefix} setup: mode=manual, encoder={encoder}, '
			f'DEF={h264.DEFAULT_BITRATE / 1000} kbps, '
			f'MIN={h264.MIN_BITRATE / 1000} kbps, MAX={h264.MAX_BITRATE / 1000} kbps',
			__name__
		)
		adaptive_bitrate = False

	return bitrate_bps, adaptive_bitrate


def create_video_stream_track(pc : RTCPeerConnection, bitrate_bps : int, adaptive_bitrate : bool, buffer_size : int = 30, mode_prefix : str = 'WebRTC') -> tuple[VideoStreamTrack, Any]:
	logger.info(f'Creating {mode_prefix} output queue with buffer size: {buffer_size}', __name__)

	processed_track = VideoStreamTrack()
	processed_track.frame_queue = asyncio.Queue(maxsize = buffer_size)
	processed_track.recv = partial(recv_from_queue, processed_track.frame_queue)
	processed_track.data_channel = None
	processed_track.ready_sent = False
	processed_track._target_bitrate = bitrate_bps
	processed_track._adaptive = adaptive_bitrate
	processed_track._current_bitrate = bitrate_bps

	sender = pc.addTrack(processed_track)

	return processed_track, sender


async def monitor_and_set_bitrate(sender : Any, bitrate_bps : int, adaptive_bitrate : bool, processed_track : VideoStreamTrack, buffer_size : int) -> None:
	encoder_obj = None
	for attempt in range(30):
		if hasattr(sender, '_RTCRtpSender__encoder') and sender._RTCRtpSender__encoder:
			encoder_obj = sender._RTCRtpSender__encoder
			encoder_type = type(encoder_obj).__name__
			if hasattr(encoder_obj, 'target_bitrate'):
				old_bitrate = encoder_obj.target_bitrate
				encoder_obj.target_bitrate = bitrate_bps
				logger.info(
					f'Encoder type: {encoder_type}, updated bitrate from {old_bitrate / 1000} kbps to {bitrate_bps / 1000} kbps',
					__name__
				)
				if hasattr(encoder_obj, 'codec') and encoder_obj.codec:
					logger.info(
						f'Encoder codec context: {encoder_obj.codec.name if hasattr(encoder_obj.codec, "name") else "unknown"}',
						__name__
					)
				break

	if not encoder_obj:
		logger.warn('Encoder not created after 9 seconds', __name__)
		return

	if not adaptive_bitrate:
		return

	stable_checks = 0
	INCREASE_STEP = 50000
	DECREASE_FACTOR = 0.9

	while True:
		await asyncio.sleep(0.5)

		if not hasattr(encoder_obj, 'target_bitrate'):
			break

		queue_ratio = processed_track.frame_queue.qsize() / buffer_size

		if queue_ratio > 0.7:
			new_bitrate = max(int(processed_track._current_bitrate * DECREASE_FACTOR), h264.MIN_BITRATE)
			processed_track._current_bitrate = new_bitrate
			encoder_obj.target_bitrate = new_bitrate
			stable_checks = 0
			logger.info(f'Auto: decreased to {new_bitrate / 1000} kbps (congestion)', __name__)
		elif queue_ratio < 0.3:
			stable_checks += 1
			if stable_checks >= 4:
				new_bitrate = min(processed_track._current_bitrate + INCREASE_STEP, h264.MAX_BITRATE)
				if new_bitrate > processed_track._current_bitrate:
					processed_track._current_bitrate = new_bitrate
					encoder_obj.target_bitrate = new_bitrate
					logger.info(f'Auto: increased to {new_bitrate / 1000} kbps (stable)', __name__)
				stable_checks = 0
		else:
			stable_checks = 0


async def websocket_process(websocket : WebSocket) -> None:
	subprotocol = get_requested_subprotocol(websocket)
	await websocket.accept(subprotocol = subprotocol)
	init_default_state()

	output_resolution = websocket.query_params.get('output_resolution', 'original')

	while True:
		message = await websocket.receive()

		if message['type'] == 'websocket.disconnect':
			logger.debug('Client disconnected', __name__)
			break

		if message['type'] == 'websocket.receive':
			if 'bytes' in message:
				logger.debug(f'Received {len(message["bytes"])} bytes', __name__)

				target_vision_frame = cv2.imdecode(numpy.frombuffer(message['bytes'], numpy.uint8), cv2.IMREAD_COLOR)
				if target_vision_frame is None:
					logger.error('Failed to decode target image!', __name__)
					continue

				logger.debug(f'Decoded target frame shape: {target_vision_frame.shape}', __name__)

				if output_resolution and output_resolution != 'original':
					resolution_map =\
					{
						'480p': (640, 480),
						'720p': (1280, 720),
						'1080p': (1920, 1080)
					}
					if output_resolution in resolution_map:
						target_width, target_height = resolution_map[output_resolution]
						current_height, current_width = target_vision_frame.shape[:2]
						if current_width > target_width or current_height > target_height:
							scale = min(target_width / current_width, target_height / current_height)
							new_width = int(current_width * scale)
							new_height = int(current_height * scale)
							target_vision_frame = cv2.resize(target_vision_frame, (new_width, new_height), interpolation = cv2.INTER_AREA)
							logger.debug(f'Downscaled target from {current_width}x{current_height} to {new_width}x{new_height}', __name__)

				temp_vision_frame = process_stream_frame(target_vision_frame)
				if temp_vision_frame is None:
					continue

				if content_analyser.analyse_frame(temp_vision_frame):
					logger.warn('NSFW content detected in output, blurring frame', __name__)
					temp_vision_frame = obscure_frame(temp_vision_frame)

				success, result_bytes = cv2.imencode('.jpg', temp_vision_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
				if success:
					await websocket.send_bytes(result_bytes.tobytes())


async def process_incoming_video_track(track : Any, frame_queue : Any, output_track : Any = None, output_resolution : str = 'original') -> None:
	from aiortc.mediastreams import MediaStreamError

	logger.debug(f'Track received: {track.kind}', __name__)
	max_fps = 60
	min_frame_time = 1.0 / max_fps
	last_process_time = 0.0
	frame_counter = 0
	frame_skip = 2
	last_processed_frame = None

	try:
		global NSFW_LOCK
		while True:
			try:
				frame = await track.recv()
			except MediaStreamError:
				logger.info('Media stream ended (connection closed)', __name__)
				break
			except asyncio.CancelledError:
				logger.info('Video processing cancelled', __name__)
				raise
			except Exception as e:
				logger.error(f'Error receiving frame: {e}', __name__)
				break

			current_time = asyncio.get_event_loop().time()
			time_since_last = current_time - last_process_time

			if time_since_last < min_frame_time:
				continue

			img = frame.to_ndarray(format='bgr24')
			logger.debug(f'Received frame shape: {img.shape}', __name__)

			if output_resolution and output_resolution != 'original':
				if output_resolution in RESOLUTION_MAP:
					target_width, target_height = RESOLUTION_MAP[output_resolution]
					current_height, current_width = img.shape[:2]
					if current_width > target_width or current_height > target_height:
						scale = min(target_width / current_width, target_height / current_height)
						new_width = int(current_width * scale)
						new_height = int(current_height * scale)
						img = cv2.resize(img, (new_width, new_height), interpolation = cv2.INTER_AREA)
						logger.debug(f'Downscaled target from {current_width}x{current_height} to {new_width}x{new_height}', __name__)

			if content_analyser.analyse_stream(img, float(max_fps)):
				NSFW_LOCK = True

			if NSFW_LOCK:
				temp_vision_frame = obscure_frame(img)
			else:
				frame_counter += 1
				if frame_counter % frame_skip == 0:
					temp_vision_frame = process_stream_frame(img)
					last_processed_frame = temp_vision_frame
				else:
					if last_processed_frame is not None:
						temp_vision_frame = last_processed_frame
					else:
						temp_vision_frame = process_stream_frame(img)
						last_processed_frame = temp_vision_frame

			if temp_vision_frame is not None:
				new_frame = VideoFrame.from_ndarray(temp_vision_frame, format='bgr24')
				new_frame.pts = frame.pts
				new_frame.time_base = frame.time_base

				if frame_queue.full():
					try:
						frame_queue.get_nowait()
					except asyncio.QueueEmpty:
						pass

				try:
					frame_queue.put_nowait(new_frame)
					last_process_time = current_time

					if output_track and not output_track.ready_sent and frame_queue.qsize() >= int(frame_queue.maxsize * 0.5):
						output_track.ready_sent = True
						logger.info(f'Buffer ready ({frame_queue.qsize()}/{frame_queue.maxsize} frames), sending ready signal', __name__)
						if output_track.data_channel and output_track.data_channel.readyState == 'open':
							output_track.data_channel.send('ready')
							logger.info('Ready signal sent to client', __name__)

					if output_track and output_track.data_channel and output_track.data_channel.readyState == 'open':
						try:
							output_track.data_channel.send(f'frame:{frame_counter}')
						except Exception:
							pass
				except asyncio.QueueFull:
					logger.debug('Frame queue full, frame dropped', __name__)
	except Exception as e:
		logger.error(f'Unexpected error in video processing: {e}', __name__)
	finally:
		logger.info('Video processing task completed', __name__)


async def recv_from_queue(frame_queue : Any) -> Any:
	frame = await frame_queue.get()
	return frame


def check_and_lock_nsfw(vision_frame : Any, fps : float) -> bool:
	global NSFW_LOCK

	if NSFW_LOCK:
		return True

	if content_analyser.analyse_stream(vision_frame, fps):
		NSFW_LOCK = True
		logger.warn('NSFW content detected, locking all future frames', __name__)
		return True

	return False


def get_requested_subprotocol(websocket : WebSocket) -> Optional[str]:
	headers = Headers(scope = websocket.scope)
	protocol_header = headers.get('Sec-WebSocket-Protocol')

	if protocol_header:
		protocol, _, _ = protocol_header.partition(',')
		return protocol.strip()

	return None


async def webrtc_offer(request : Request) -> JSONResponse:
	global NSFW_LOCK
	init_default_state()
	NSFW_LOCK = False

	params = await request.json()
	offer = RTCSessionDescription(sdp=params['sdp'], type=params['type'])
	bitrate = int(params.get('bitrate', 0))
	encoder = params.get('encoder', 'VP8')
	buffer_size = int(params.get('stream_buffer_size', 30))
	output_resolution = params.get('output_resolution', 'original')

	bitrate_bps, adaptive_bitrate = setup_bitrate_config(bitrate, encoder, 'WebRTC')

	pc = RTCPeerConnection()
	pcs.add(pc)

	processed_track, sender = create_video_stream_track(pc, bitrate_bps, adaptive_bitrate, buffer_size, 'WebRTC')

	asyncio.create_task(monitor_and_set_bitrate(sender, bitrate_bps, adaptive_bitrate, processed_track, buffer_size))

	processing_tasks : List[Any] = []

	@pc.on('connectionstatechange')
	async def on_connectionstatechange() -> None:
		logger.info(f'WebRTC connection state: {pc.connectionState}', __name__)
		if pc.connectionState == 'failed' or pc.connectionState == 'closed':
			logger.info('WebRTC connection closed, cleaning up', __name__)
			pcs.discard(pc)
			for task in processing_tasks:
				task.cancel()

	@pc.on('datachannel')
	def on_datachannel(channel : Any) -> None:
		logger.info(f'Data channel received: {channel.label}', __name__)
		processed_track.data_channel = channel

	await pc.setRemoteDescription(offer)

	for transceiver in pc.getTransceivers():
		if transceiver.receiver and transceiver.receiver.track:
			track = transceiver.receiver.track
			if track.kind == 'video':
				logger.info('Found video track, starting processing', __name__)
				video_task = asyncio.create_task(process_incoming_video_track(track, processed_track.frame_queue, processed_track, output_resolution))
				processing_tasks.append(video_task)
			if track.kind == 'audio':
				logger.info('Found audio track, forwarding as-is', __name__)
				pc.addTrack(track)

	answer = await pc.createAnswer()
	await pc.setLocalDescription(answer)

	return JSONResponse({'sdp': pc.localDescription.sdp, 'type': pc.localDescription.type})


async def process_stream_from_url(stream_url : str, frame_queue : Any, output_track : Any = None, width : int = 1280, height : int = 720, target_fps : int = 30, duration : float = 0, output_resolution : str = 'original') -> None:
	logger.info(f'Opening stream from URL: {stream_url[:100]}', __name__)
	logger.info(f'Using metadata - Resolution: {width}x{height}, FPS: {target_fps}, Duration: {duration}s', __name__)

	frame_size = width * height * 3
	frame_interval = 1.0 / target_fps

	import threading
	import time

	current_process = None
	seek_position = [0.0]
	stop_flag = [False]
	lock = threading.Lock()

	def start_ffmpeg(start_time : float) -> Any:
		ffmpeg_command =\
		[
			'ffmpeg',
			'-user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
			'-reconnect', '1',
			'-reconnect_streamed', '1',
			'-reconnect_delay_max', '5'
		]

		if start_time > 0:
			ffmpeg_command.extend(['-ss', str(start_time)])

		ffmpeg_command.extend([
			'-i', stream_url,
			'-f', 'rawvideo',
			'-pix_fmt', 'bgr24',
			'-'
		])

		try:
			return subprocess.Popen(ffmpeg_command, stdout = subprocess.PIPE, stderr = subprocess.DEVNULL, bufsize = 10**8)
		except Exception as e:
			logger.error(f'Failed to start ffmpeg: {e}', __name__)
			return None

	def read_stream() -> None:
		nonlocal current_process
		frame_count = int(seek_position[0] * target_fps)

		current_process = start_ffmpeg(seek_position[0])
		if not current_process:
			return

		logger.info(f'FFmpeg stream started at position {seek_position[0]}s', __name__)

		last_frame_time = time.time()
		local_process = current_process

		while not stop_flag[0]:
			with lock:
				if local_process != current_process:
					logger.info('Process changed due to seek, switching to new process', __name__)
					local_process = current_process
					frame_count = int(seek_position[0] * target_fps)
					if not local_process:
						break
					continue

			if local_process.poll() is not None:
				logger.info('Stream process terminated', __name__)
				break

			raw_frame = local_process.stdout.read(frame_size)
			if not raw_frame or len(raw_frame) != frame_size:
				with lock:
					if local_process != current_process:
						logger.info('Incomplete read due to seek, switching to new process', __name__)
						local_process = current_process
						frame_count = int(seek_position[0] * target_fps)
						continue
				logger.info('Stream ended or incomplete frame', __name__)
				break

			frame = numpy.frombuffer(raw_frame, dtype = numpy.uint8).reshape((height, width, 3))

			if output_resolution and output_resolution != 'original':
				if output_resolution in RESOLUTION_MAP:
					target_width, target_height = RESOLUTION_MAP[output_resolution]
					current_height, current_width = frame.shape[:2]
					if current_width > target_width or current_height > target_height:
						scale = min(target_width / current_width, target_height / current_height)
						new_width = int(current_width * scale)
						new_height = int(current_height * scale)
						frame = cv2.resize(frame, (new_width, new_height), interpolation = cv2.INTER_AREA)

			if check_and_lock_nsfw(frame, float(target_fps)):
				processed_frame = obscure_frame(frame)
			else:
				processed_frame = process_stream_frame(frame)

			if processed_frame is not None:
				current_time = time.time()
				elapsed = current_time - last_frame_time

				if elapsed < frame_interval:
					time.sleep(frame_interval - elapsed)
					current_time = time.time()

				video_frame = VideoFrame.from_ndarray(processed_frame, format = 'bgr24')
				video_frame.pts = frame_count
				video_frame.time_base = fractions.Fraction(1, target_fps)

				if frame_queue.full():
					try:
						frame_queue.get_nowait()
					except asyncio.QueueEmpty:
						pass

				try:
					frame_queue.put_nowait(video_frame)
					if output_track and not output_track.ready_sent and frame_queue.qsize() >= int(frame_queue.maxsize * 0.5):
						output_track.ready_sent = True
						logger.info(f'Buffer ready ({frame_queue.qsize()}/{frame_queue.maxsize} frames)', __name__)
						if output_track.data_channel and output_track.data_channel.readyState == 'open':
							output_track.data_channel.send('ready')

					if output_track and output_track.data_channel and output_track.data_channel.readyState == 'open':
						try:
							output_track.data_channel.send(f'frame:{frame_count}')
						except Exception:
							pass
				except asyncio.QueueFull:
					pass

				last_frame_time = current_time
				frame_count += 1

		if current_process:
			current_process.terminate()
			current_process.wait()
		logger.info(f'Stream reading completed, {frame_count} frames processed', __name__)

	def handle_seek(new_position : float) -> None:
		nonlocal current_process
		with lock:
			seek_position[0] = new_position
			if current_process:
				logger.info(f'Seeking to {new_position}s, restarting ffmpeg', __name__)
				current_process.terminate()
				current_process = start_ffmpeg(new_position)

	if output_track:
		output_track.seek_handler = handle_seek

	stream_task = asyncio.get_event_loop().run_in_executor(None, read_stream)

	try:
		await stream_task
	except asyncio.CancelledError:
		logger.info('Video stream task cancelled', __name__)
		raise
	finally:
		stop_flag[0] = True
		if current_process:
			current_process.terminate()
		logger.info('Video stream cleanup completed', __name__)


async def process_audio_from_url(stream_url : str, audio_queue : Any, video_output_track : Any = None) -> None:
	logger.info('Opening audio stream from URL', __name__)

	import threading

	current_process = None
	seek_position = [0.0]
	stop_flag = [False]
	lock = threading.Lock()

	sample_rate = 24000
	channels = 2
	frame_samples = 480
	bytes_per_sample = 2
	frame_size = frame_samples * channels * bytes_per_sample

	def start_ffmpeg_audio(start_time : float) -> Any:
		ffmpeg_command =\
		[
			'ffmpeg',
			'-user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
			'-reconnect', '1',
			'-reconnect_streamed', '1',
			'-reconnect_delay_max', '5'
		]

		if start_time > 0:
			ffmpeg_command.extend(['-ss', str(start_time)])

		ffmpeg_command.extend([
			'-i', stream_url,
			'-vn',
			'-f', 's16le',
			'-acodec', 'pcm_s16le',
			'-ar', str(sample_rate),
			'-ac', str(channels),
			'-'
		])

		try:
			return subprocess.Popen(ffmpeg_command, stdout = subprocess.PIPE, stderr = subprocess.DEVNULL, bufsize = 10**8)
		except Exception as e:
			logger.error(f'Failed to start ffmpeg audio: {e}', __name__)
			return None

	def read_audio_stream() -> None:
		nonlocal current_process
		import time

		current_process = start_ffmpeg_audio(seek_position[0])
		if not current_process:
			return

		logger.info(f'FFmpeg audio stream started at position {seek_position[0]}s', __name__)

		local_process = current_process
		frame_count = 0

		frame_duration = frame_samples / sample_rate
		start_time = time.time()
		expected_time = start_time

		logger.info(f'Starting audio read loop, expecting {frame_size} bytes per frame', __name__)

		while not stop_flag[0]:
			with lock:
				if local_process != current_process:
					logger.info('Audio process changed due to seek, switching to new process', __name__)
					local_process = current_process
					frame_count = 0
					start_time = time.time()
					expected_time = start_time
					if not local_process:
						break
					continue

			if local_process.poll() is not None:
				logger.info('Audio stream process terminated', __name__)
				break

			raw_audio = local_process.stdout.read(frame_size)

			if frame_count == 0:
				logger.info('Successfully read first audio frame', __name__)
			if not raw_audio or len(raw_audio) != frame_size:
				with lock:
					if local_process != current_process:
						logger.info('Incomplete audio read due to seek, switching to new process', __name__)
						local_process = current_process
						continue
				logger.info('Audio stream ended or incomplete frame', __name__)
				break

			audio_array = numpy.frombuffer(raw_audio, dtype = numpy.int16)

			audio_frame = AudioFrame(format = 's16', layout = 'stereo', samples = frame_samples)
			audio_frame.sample_rate = sample_rate
			audio_frame.pts = frame_count * frame_samples
			audio_frame.time_base = fractions.Fraction(1, sample_rate)

			for plane in audio_frame.planes:
				plane.update(audio_array.tobytes())

			expected_time += frame_duration
			current_time = time.time()
			sleep_time = expected_time - current_time

			if sleep_time > 0:
				time.sleep(sleep_time)

			if audio_queue.full():
				try:
					audio_queue.get_nowait()
				except asyncio.QueueEmpty:
					pass

			try:
				audio_queue.put_nowait(audio_frame)
				frame_count += 1
				if frame_count % 50 == 0:
					logger.info(f'Audio frames queued: {frame_count}, queue depth: {audio_queue.qsize()}', __name__)
			except asyncio.QueueFull:
				pass

		if current_process:
			current_process.terminate()
		logger.info('Audio stream reading completed', __name__)

	def handle_audio_seek(new_position : float) -> None:
		nonlocal current_process
		with lock:
			seek_position[0] = new_position
			if current_process:
				logger.info(f'Seeking audio to {new_position}s, restarting ffmpeg', __name__)
				current_process.terminate()
				current_process = start_ffmpeg_audio(new_position)

	if video_output_track:
		video_output_track.audio_seek_handler = handle_audio_seek

	audio_task = asyncio.get_event_loop().run_in_executor(None, read_audio_stream)

	try:
		await audio_task
	except asyncio.CancelledError:
		logger.info('Audio stream task cancelled', __name__)
		raise
	finally:
		stop_flag[0] = True
		if current_process:
			current_process.terminate()
		logger.info('Audio stream cleanup completed', __name__)


async def webrtc_stream_offer(request : Request) -> JSONResponse:
	global NSFW_LOCK
	init_default_state()
	NSFW_LOCK = False

	params = await request.json()
	offer = RTCSessionDescription(sdp = params['sdp'], type = params['type'])
	bitrate = int(params.get('bitrate', 0))
	encoder = params.get('encoder', 'VP8')
	is_remote_stream = params.get('is_remote_stream', False)
	stream_url = params.get('stream_url')
	target_width = int(params.get('target_width', 1280))
	target_height = int(params.get('target_height', 720))
	target_fps = int(params.get('target_fps', 30))
	target_duration = float(params.get('target_duration', 0))
	target_audio_path = params.get('target_audio_path')
	buffer_size = int(params.get('stream_buffer_size', 30))
	output_resolution = params.get('output_resolution', 'original')

	logger.info(f'[WebRTC Stream] stream_url: {stream_url[:50] if stream_url else None}', __name__)
	logger.info(f'[WebRTC Stream] is_remote_stream: {is_remote_stream}', __name__)

	if not stream_url:
		logger.error('[WebRTC Stream] No stream URL provided', __name__)
		return JSONResponse({'error': 'No stream URL provided in request'}, status_code = 400)

	if not is_remote_stream:
		logger.error('[WebRTC Stream] is_remote_stream=False, use /webrtc/offer for local files', __name__)
		return JSONResponse({'error': 'Use /webrtc/offer endpoint for local files, not /stream/webrtc/offer'}, status_code = 400)

	bitrate_bps, adaptive_bitrate = setup_bitrate_config(bitrate, encoder, 'WebRTC stream')

	pc = RTCPeerConnection()
	pcs.add(pc)

	processed_track, sender = create_video_stream_track(pc, bitrate_bps, adaptive_bitrate, buffer_size, 'WebRTC stream')

	audio_track = AudioStreamTrack()
	audio_track.audio_queue = asyncio.Queue(maxsize = buffer_size)
	audio_track.recv = partial(recv_from_queue, audio_track.audio_queue)
	pc.addTrack(audio_track)

	asyncio.create_task(monitor_and_set_bitrate(sender, bitrate_bps, adaptive_bitrate, processed_track, buffer_size))

	stream_tasks : List[Any] = []

	@pc.on('connectionstatechange')
	async def on_connectionstatechange() -> None:
		logger.info(f'WebRTC stream connection state: {pc.connectionState}', __name__)
		if pc.connectionState == 'failed' or pc.connectionState == 'closed':
			logger.info('WebRTC stream connection closed, stopping ffmpeg processes', __name__)
			pcs.discard(pc)
			for task in stream_tasks:
				task.cancel()

	@pc.on('datachannel')
	def on_datachannel(channel : Any) -> None:
		logger.info(f'Data channel received: {channel.label}', __name__)
		processed_track.data_channel = channel

		@channel.on('message')
		def on_message(message : Any) -> None:
			if isinstance(message, str) and message.startswith('seek:'):
				try:
					seek_time = float(message.split(':', 1)[1])
					logger.info(f'Received seek command: {seek_time}s', __name__)
					if hasattr(processed_track, 'seek_handler') and processed_track.seek_handler:
						processed_track.seek_handler(seek_time)
					if hasattr(processed_track, 'audio_seek_handler') and processed_track.audio_seek_handler:
						processed_track.audio_seek_handler(seek_time)
				except Exception as e:
					logger.error(f'Error handling seek command: {e}', __name__)

	await pc.setRemoteDescription(offer)

	audio_url = target_audio_path or stream_url
	logger.info(f'Starting stream processing from URL (video: {stream_url[:50]}..., audio: {audio_url[:50]}...)', __name__)

	video_task = asyncio.create_task(process_stream_from_url(stream_url, processed_track.frame_queue, processed_track, target_width, target_height, target_fps, target_duration, output_resolution))
	audio_task = asyncio.create_task(process_audio_from_url(audio_url, audio_track.audio_queue, processed_track))
	stream_tasks.extend([video_task, audio_task])

	answer = await pc.createAnswer()
	await pc.setLocalDescription(answer)

	return JSONResponse({'sdp': pc.localDescription.sdp, 'type': pc.localDescription.type})
