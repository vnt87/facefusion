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
export const startProcess = async (options?: { outputPath?: string; processors?: string[] }) => {
    const response = await api.post('/process/start', {
        output_path: options?.outputPath,
        processors: options?.processors,
    });
    return response.data;
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
}

export interface ProcessResponse {
    status: string;
    output_path: string | null;
}
