from typing import List, Optional
from pydantic import BaseModel


class HealthResponse(BaseModel):
	status: str


class UploadResponse(BaseModel):
	file_id: str
	filename: str
	path: str
	is_image: bool
	is_video: bool


class StateResponse(BaseModel):
	source_paths: List[str]
	target_path: Optional[str]
	output_path: Optional[str]
	processors: List[str]


class ProcessRequest(BaseModel):
	output_path: Optional[str] = None
	processors: Optional[List[str]] = None
	trim_frame_start: Optional[int] = None
	trim_frame_end: Optional[int] = None


class ProcessResponse(BaseModel):
	status: str
	output_path: Optional[str]


# Face Detection schemas
class DetectedFace(BaseModel):
	index: int
	bounding_box: List[float]
	image_base64: str  # Cropped face image as base64


class FaceDetectionRequest(BaseModel):
	frame_number: Optional[int] = 0


class FaceDetectionResponse(BaseModel):
	faces: List[DetectedFace]
	frame_number: int
	total_faces: int


# Preview Frame schemas
class PreviewFrameRequest(BaseModel):
	frame_number: Optional[int] = 0
	reference_face_position: Optional[int] = 0


class PreviewFrameResponse(BaseModel):
	image_base64: str
	frame_number: int
	has_face_swap: bool


# Video Info schemas
class VideoInfoResponse(BaseModel):
	frame_count: int
	fps: float
	duration: float
	width: int
	height: int
