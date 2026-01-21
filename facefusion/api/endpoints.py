import os
import uuid
import shutil
import base64
from pathlib import Path
from typing import Optional

import cv2

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from facefusion import state_manager
from facefusion.filesystem import is_image, is_video
from facefusion.vision import read_static_image, read_video_frame, count_video_frame_total, detect_video_fps, detect_video_resolution, fit_cover_frame
from facefusion.face_analyser import get_many_faces
from facefusion.face_selector import sort_and_filter_faces
from .schemas import (
	HealthResponse, UploadResponse, ProcessRequest, ProcessResponse, StateResponse,
	FaceDetectionRequest, FaceDetectionResponse, DetectedFace,
	PreviewFrameRequest, PreviewFrameResponse, VideoInfoResponse
)

router = APIRouter()

# Temporary storage for uploaded files
UPLOAD_DIR = Path(state_manager.get_item('temp_path') or './temp') / 'api_uploads'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get('/health', response_model=HealthResponse)
def health() -> HealthResponse:
	return HealthResponse(status='ok')


@router.post('/upload/source', response_model=UploadResponse)
async def upload_source(file: UploadFile = File(...)) -> UploadResponse:
	"""Upload a source image or video file."""
	file_id = str(uuid.uuid4())
	file_extension = Path(file.filename or '').suffix
	file_path = UPLOAD_DIR / f"source_{file_id}{file_extension}"
	
	try:
		with open(file_path, 'wb') as buffer:
			shutil.copyfileobj(file.file, buffer)
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
	
	# Update state manager - replace existing source
	state_manager.set_item('source_paths', [str(file_path)])
	
	return UploadResponse(
		file_id=file_id,
		filename=file.filename or 'unknown',
		path=str(file_path),
		is_image=is_image(str(file_path)),
		is_video=is_video(str(file_path))
	)


@router.post('/upload/target', response_model=UploadResponse)
async def upload_target(file: UploadFile = File(...)) -> UploadResponse:
	"""Upload a target image or video file."""
	file_id = str(uuid.uuid4())
	file_extension = Path(file.filename or '').suffix
	file_path = UPLOAD_DIR / f"target_{file_id}{file_extension}"
	
	try:
		with open(file_path, 'wb') as buffer:
			shutil.copyfileobj(file.file, buffer)
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
	
	# Update state manager
	state_manager.set_item('target_path', str(file_path))
	
	return UploadResponse(
		file_id=file_id,
		filename=file.filename or 'unknown',
		path=str(file_path),
		is_image=is_image(str(file_path)),
		is_video=is_video(str(file_path))
	)


@router.get('/state', response_model=StateResponse)
def get_state() -> StateResponse:
	"""Get current processing state."""
	return StateResponse(
		source_paths=state_manager.get_item('source_paths') or [],
		target_path=state_manager.get_item('target_path'),
		output_path=state_manager.get_item('output_path'),
		processors=state_manager.get_item('processors') or ['face_swapper', 'face_enhancer']
	)


@router.post('/process/start', response_model=ProcessResponse)
async def start_process(request: ProcessRequest, background_tasks: BackgroundTasks) -> ProcessResponse:
	"""Start the face swap processing."""
	from facefusion.core import common_pre_check, processors_pre_check, conditional_process
	
	# Set output path if provided
	if request.output_path:
		state_manager.set_item('output_path', request.output_path)
	else:
		# Generate default output path
		target_path = state_manager.get_item('target_path')
		if target_path:
			output_dir = UPLOAD_DIR / 'outputs'
			output_dir.mkdir(exist_ok=True)
			output_path = output_dir / f"output_{uuid.uuid4()}{Path(target_path).suffix}"
			state_manager.set_item('output_path', str(output_path))
	
	# Set processors
	if request.processors:
		state_manager.set_item('processors', request.processors)
	
	# Set trim frame range if provided
	if request.trim_frame_start is not None:
		state_manager.set_item('trim_frame_start', request.trim_frame_start)
	if request.trim_frame_end is not None:
		state_manager.set_item('trim_frame_end', request.trim_frame_end)
	
	# Check prerequisites
	if not common_pre_check() or not processors_pre_check():
		raise HTTPException(status_code=400, detail="Pre-check failed")
	
	# Run processing in background
	def run_processing():
		try:
			conditional_process()
		except Exception as e:
			import traceback
			from facefusion import logger
			error_msg = f"Processing failed: {str(e)}\n{traceback.format_exc()}"
			logger.error(error_msg, __name__)
	
	background_tasks.add_task(run_processing)
	
	return ProcessResponse(
		status='started',
		output_path=state_manager.get_item('output_path')
	)


@router.get('/output/{file_id}')
async def get_output(file_id: str):
	"""Get the processed output file."""
	output_path = state_manager.get_item('output_path')
	if output_path and os.path.exists(output_path):
		return FileResponse(output_path)
	raise HTTPException(status_code=404, detail="Output file not found")


@router.post('/detect-faces', response_model=FaceDetectionResponse)
async def detect_faces(request: FaceDetectionRequest) -> FaceDetectionResponse:
	"""Detect faces in the target image/video at specified frame."""
	target_path = state_manager.get_item('target_path')
	if not target_path:
		raise HTTPException(status_code=400, detail="No target file uploaded")
	
	frame_number = request.frame_number or 0
	
	# Read frame from image or video
	if is_image(target_path):
		vision_frame = read_static_image(target_path)
	elif is_video(target_path):
		vision_frame = read_video_frame(target_path, frame_number)
	else:
		raise HTTPException(status_code=400, detail="Invalid target file type")
	
	if vision_frame is None:
		raise HTTPException(status_code=500, detail="Failed to read frame")
	
	# Detect faces
	faces = get_many_faces([vision_frame])
	faces = sort_and_filter_faces(faces)
	
	# Extract cropped face images
	detected_faces = []
	for idx, face in enumerate(faces):
		start_x, start_y, end_x, end_y = map(int, face.bounding_box)
		padding_x = int((end_x - start_x) * 0.25)
		padding_y = int((end_y - start_y) * 0.25)
		start_x = max(0, start_x - padding_x)
		start_y = max(0, start_y - padding_y)
		end_x = min(vision_frame.shape[1], end_x + padding_x)
		end_y = min(vision_frame.shape[0], end_y + padding_y)
		
		crop_frame = vision_frame[start_y:end_y, start_x:end_x]
		crop_frame = fit_cover_frame(crop_frame, (128, 128))
		crop_frame = cv2.cvtColor(crop_frame, cv2.COLOR_BGR2RGB)
		
		# Encode to base64
		_, buffer = cv2.imencode('.jpg', cv2.cvtColor(crop_frame, cv2.COLOR_RGB2BGR))
		image_base64 = base64.b64encode(buffer).decode('utf-8')
		
		detected_faces.append(DetectedFace(
			index=idx,
			bounding_box=list(face.bounding_box),
			image_base64=image_base64
		))
	
	return FaceDetectionResponse(
		faces=detected_faces,
		frame_number=frame_number,
		total_faces=len(detected_faces)
	)


@router.post('/preview-frame', response_model=PreviewFrameResponse)
async def get_preview_frame(request: PreviewFrameRequest) -> PreviewFrameResponse:
	"""Generate a preview frame with face swap applied."""
	from facefusion.processors.core import get_processors_modules
	from facefusion.audio import create_empty_audio_frame
	from facefusion.vision import read_static_images, restrict_frame, unpack_resolution
	
	target_path = state_manager.get_item('target_path')
	source_paths = state_manager.get_item('source_paths') or []
	
	if not target_path:
		raise HTTPException(status_code=400, detail="No target file uploaded")
	
	frame_number = request.frame_number or 0
	reference_face_position = request.reference_face_position or 0
	
	# Update state for reference face position
	state_manager.set_item('reference_face_position', reference_face_position)
	state_manager.set_item('reference_frame_number', frame_number)
	
	# Read source frames
	source_vision_frames = read_static_images(source_paths) if source_paths else []
	source_audio_frame = create_empty_audio_frame()
	source_voice_frame = create_empty_audio_frame()
	
	# Read target frame
	if is_image(target_path):
		target_vision_frame = read_static_image(target_path)
		reference_vision_frame = target_vision_frame.copy()
	elif is_video(target_path):
		target_vision_frame = read_video_frame(target_path, frame_number)
		reference_vision_frame = read_video_frame(target_path, frame_number)
	else:
		raise HTTPException(status_code=400, detail="Invalid target file type")
	
	if target_vision_frame is None:
		raise HTTPException(status_code=500, detail="Failed to read frame")
	
	has_face_swap = len(source_vision_frames) > 0
	temp_vision_frame = target_vision_frame.copy()
	
	# Apply processors if source is available
	if has_face_swap:
		processors = state_manager.get_item('processors') or ['face_swapper']
		for processor_module in get_processors_modules(processors):
			try:
				if processor_module.pre_process('preview'):
					temp_vision_frame, _ = processor_module.process_frame({
						'reference_vision_frame': reference_vision_frame,
						'source_audio_frame': source_audio_frame,
						'source_voice_frame': source_voice_frame,
						'source_vision_frames': source_vision_frames,
						'target_vision_frame': target_vision_frame,
						'temp_vision_frame': temp_vision_frame,
						'temp_vision_mask': None
					})
			except Exception:
				pass
	
	# Convert to RGB and encode
	output_frame = cv2.cvtColor(temp_vision_frame, cv2.COLOR_BGR2RGB)
	_, buffer = cv2.imencode('.jpg', cv2.cvtColor(output_frame, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])
	image_base64 = base64.b64encode(buffer).decode('utf-8')
	
	return PreviewFrameResponse(
		image_base64=image_base64,
		frame_number=frame_number,
		has_face_swap=has_face_swap
	)


@router.get('/video-info', response_model=VideoInfoResponse)
async def get_video_info() -> VideoInfoResponse:
	"""Get video metadata for the target video."""
	target_path = state_manager.get_item('target_path')
	
	if not target_path:
		raise HTTPException(status_code=400, detail="No target file uploaded")
	
	if not is_video(target_path):
		raise HTTPException(status_code=400, detail="Target is not a video file")
	
	frame_count = count_video_frame_total(target_path)
	fps = detect_video_fps(target_path)
	width, height = detect_video_resolution(target_path)
	duration = frame_count / fps if fps > 0 else 0
	
	return VideoInfoResponse(
		frame_count=frame_count,
		fps=fps,
		duration=duration,
		width=width,
		height=height
	)

