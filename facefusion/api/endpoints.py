import os
import uuid
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from facefusion import state_manager
from facefusion.filesystem import is_image, is_video
from .schemas import HealthResponse, UploadResponse, ProcessRequest, ProcessResponse, StateResponse

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
	
	# Update state manager
	current_sources = state_manager.get_item('source_paths') or []
	current_sources.append(str(file_path))
	state_manager.set_item('source_paths', current_sources)
	
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
	from facefusion.jobs import job_manager, job_helper
	from facefusion.args import reduce_step_args, collect_job_args, apply_args
	
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
	
	# Check prerequisites
	if not common_pre_check() or not processors_pre_check():
		raise HTTPException(status_code=400, detail="Pre-check failed")
	
	# Run processing in background
	def run_processing():
		conditional_process()
	
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
