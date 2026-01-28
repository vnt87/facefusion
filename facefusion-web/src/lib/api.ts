import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Health check
export const checkHealth = async () => {
    const response = await api.get('/health');
    return response.data;
};

// Upload source file
export const uploadSource = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/upload/source', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
};

// Upload target file
export const uploadTarget = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/upload/target', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
};

// Get current state
export const getState = async () => {
    const response = await api.get('/state');
    return response.data;
};

// Start processing
export const startProcess = async (options?: {
    outputPath?: string;
    processors?: string[];
    trimFrameStart?: number;
    trimFrameEnd?: number;
    modal?: boolean;
}) => {
    const response = await api.post('/process/start', {
        output_path: options?.outputPath,
        processors: options?.processors,
        trim_frame_start: options?.trimFrameStart,
        trim_frame_end: options?.trimFrameEnd,
        modal: options?.modal,
    });
    return response.data;
};

// Detect faces in target
export const detectFaces = async (frameNumber: number = 0): Promise<FaceDetectionResponse> => {
    const response = await api.post('/detect-faces', { frame_number: frameNumber });
    return response.data;
};

// Get preview frame with face swap
export const getPreviewFrame = async (
    frameNumber: number = 0,
    referenceFacePosition: number = 0
): Promise<PreviewFrameResponse> => {
    const response = await api.post('/preview-frame', {
        frame_number: frameNumber,
        reference_face_position: referenceFacePosition
    });
    return response.data;
};

// Get video info
export const getVideoInfo = async (): Promise<VideoInfoResponse> => {
    const response = await api.get('/video-info');
    return response.data;
};

// Get output file URL
export const getOutputFileUrl = (outputPath: string): string => {
    const filename = outputPath.split(/[\\/]/).pop() || 'output';
    return `${API_BASE_URL}/output/${filename}`;
};

// Types
export interface UploadResponse {
    file_id: string;
    filename: string;
    path: string;
    is_image: boolean;
    is_video: boolean;
}

export interface StateResponse {
    source_paths: string[];
    target_path: string | null;
    output_path: string | null;
    processors: string[];
    modal: boolean;
}

export interface ProcessResponse {
    status: string;
    output_path: string | null;
}

export interface DetectedFace {
    index: number;
    bounding_box: number[];
    image_base64: string;
}

export interface FaceDetectionResponse {
    faces: DetectedFace[];
    frame_number: number;
    total_faces: number;
}

export interface PreviewFrameResponse {
    image_base64: string;
    frame_number: number;
    has_face_swap: boolean;
}

export interface VideoInfoResponse {
    frame_count: number;
    fps: number;
    duration: number;
    width: number;
    height: number;
}

