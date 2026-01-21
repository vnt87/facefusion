import { useEffect, useRef, useState, useCallback } from 'react';

const WS_URL = 'ws://localhost:8000/ws';

interface WebSocketMessage {
    type: 'log' | 'progress' | 'complete' | 'pong';
    message?: string;
    progress?: number;
    status?: string;
    output_path?: string;
}

interface UseWebSocketReturn {
    logs: string[];
    progress: number;
    status: string;
    isComplete: boolean;
    outputPath: string | null;
    isConnected: boolean;
    clearLogs: () => void;
}

export function useWebSocket(): UseWebSocketReturn {
    const [logs, setLogs] = useState<string[]>([]);
    const [progress, setProgress] = useState(0);
    const [status, setStatus] = useState('Idle');
    const [isComplete, setIsComplete] = useState(false);
    const [outputPath, setOutputPath] = useState<string | null>(null);
    const [isConnected, setIsConnected] = useState(false);
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
                        }
                        break;
                    case 'progress':
                        setProgress(data.progress ?? 0);
                        setStatus(data.status ?? 'Processing');
                        setIsComplete(false);
                        break;
                    case 'complete':
                        setIsComplete(true);
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
        setOutputPath(null);
    }, []);

    return {
        logs,
        progress,
        status,
        isComplete,
        outputPath,
        isConnected,
        clearLogs,
    };
}
