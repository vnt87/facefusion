import { useEffect, useRef, useState, useCallback } from 'react';

const WS_URL = 'ws://localhost:8000/ws';

interface WebSocketMessage {
    type: 'log' | 'progress' | 'complete' | 'pong';
    message?: string;
    progress?: number;
    status?: string;
    output_path?: string;
    current_frame?: number;
    total_frames?: number;
    speed?: number;
    execution_providers?: string;
}

interface UseWebSocketReturn {
    logs: string[];
    progress: number;
    status: string;
    isComplete: boolean;
    isError: boolean;
    outputPath: string | null;
    isConnected: boolean;
    currentFrame: number;
    totalFrames: number;
    speed: number;
    executionProviders: string;
    clearLogs: () => void;
}

export function useWebSocket(): UseWebSocketReturn {
    const [logs, setLogs] = useState<string[]>([]);
    const [progress, setProgress] = useState(0);
    const [status, setStatus] = useState('Idle');
    const [isComplete, setIsComplete] = useState(false);
    const [isError, setIsError] = useState(false);
    const [outputPath, setOutputPath] = useState<string | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const [currentFrame, setCurrentFrame] = useState(0);
    const [totalFrames, setTotalFrames] = useState(0);
    const [speed, setSpeed] = useState(0);
    const [executionProviders, setExecutionProviders] = useState('');
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        const ws = new WebSocket(WS_URL);

        ws.onopen = () => {
            setIsConnected(true);
            console.log('WebSocket connected');
        };

        ws.onclose = () => {
            setIsConnected(false);
            console.log('WebSocket disconnected, reconnecting in 3s...');
            reconnectTimeoutRef.current = setTimeout(connect, 3000);
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        ws.onmessage = (event) => {
            try {
                const data: WebSocketMessage = JSON.parse(event.data);

                switch (data.type) {
                    case 'log':
                        if (data.message) {
                            setLogs((prev) => [...prev.slice(-99), data.message!]);
                            // Detect processing failures in logs
                            const lowerMessage = data.message.toLowerCase();
                            if (lowerMessage.includes('failed') ||
                                lowerMessage.includes('error:') ||
                                lowerMessage.includes('exception')) {
                                setIsError(true);
                                setStatus('Error');
                            }
                        }
                        break;
                    case 'progress':
                        setProgress(data.progress ?? 0);
                        setStatus(data.status ?? 'Processing');
                        setCurrentFrame(data.current_frame ?? 0);
                        setTotalFrames(data.total_frames ?? 0);
                        setSpeed(data.speed ?? 0);
                        setExecutionProviders(data.execution_providers ?? '');
                        setIsComplete(false);
                        setIsError(false);
                        break;
                    case 'complete':
                        setIsComplete(true);
                        setIsError(false);
                        setProgress(100);
                        setStatus('Complete');
                        setOutputPath(data.output_path ?? null);
                        break;
                }
            } catch (e) {
                console.error('Failed to parse WebSocket message:', e);
            }
        };

        wsRef.current = ws;
    }, []);

    useEffect(() => {
        connect();

        return () => {
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, [connect]);

    const clearLogs = useCallback(() => {
        setLogs([]);
        setProgress(0);
        setStatus('Idle');
        setIsComplete(false);
        setIsError(false);
        setOutputPath(null);
        setCurrentFrame(0);
        setTotalFrames(0);
        setSpeed(0);
        setExecutionProviders('');
    }, []);

    return {
        logs,
        progress,
        status,
        isComplete,
        isError,
        outputPath,
        isConnected,
        currentFrame,
        totalFrames,
        speed,
        executionProviders,
        clearLogs,
    };
}

