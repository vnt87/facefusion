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


class ProcessResponse(BaseModel):
	status: str
	output_path: Optional[str]
