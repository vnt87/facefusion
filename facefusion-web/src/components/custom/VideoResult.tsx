import { Download, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface VideoResultProps {
    outputPath: string | null;
    isComplete: boolean;
}

export function VideoResult({ outputPath, isComplete }: VideoResultProps) {
    if (!isComplete || !outputPath) {
        return null;
    }

    // Convert server path to URL
    const filename = outputPath.split(/[\\/]/).pop() || 'output';
    const videoUrl = `http://localhost:8000/output/${filename}`;
    const isVideo = filename.endsWith('.mp4') || filename.endsWith('.webm') || filename.endsWith('.avi') || filename.endsWith('.mov');

    const handleDownload = () => {
        const link = document.createElement('a');
        link.href = videoUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    return (
        <div className="rounded-2xl border border-emerald-500/30 bg-gradient-to-br from-emerald-500/10 to-green-500/10 p-6 backdrop-blur-sm">
            <div className="mb-4 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-green-500 shadow-lg shadow-emerald-500/25">
                    <CheckCircle2 className="h-5 w-5 text-white" />
                </div>
                <div>
                    <h3 className="text-lg font-semibold text-white">Processing Complete!</h3>
                    <p className="text-sm text-zinc-400">Your result is ready</p>
                </div>
            </div>

            <div className="relative overflow-hidden rounded-xl bg-black/50">
                {isVideo ? (
                    <video
                        src={videoUrl}
                        controls
                        className="w-full rounded-xl"
                        autoPlay
                        loop
                    />
                ) : (
                    <img
                        src={videoUrl}
                        alt="Processed result"
                        className="w-full rounded-xl"
                    />
                )}
            </div>

            <div className="mt-4 flex gap-2">
                <Button
                    onClick={handleDownload}
                    className="flex-1 gap-2 bg-gradient-to-r from-emerald-500 to-green-500 text-white shadow-lg shadow-emerald-500/25 hover:from-emerald-600 hover:to-green-600"
                >
                    <Download className="h-4 w-4" />
                    Download Result
                </Button>
            </div>
        </div>
    );
}
