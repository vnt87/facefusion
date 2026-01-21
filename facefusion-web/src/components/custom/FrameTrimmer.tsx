import { useCallback } from 'react'
import { cn } from '@/lib/utils'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Slider } from '@/components/ui/slider'

interface FrameTrimmerProps {
    frameCount: number
    trimStart: number
    trimEnd: number
    onTrimChange: (start: number, end: number) => void
    fps?: number
    className?: string
}

function formatTime(frames: number, fps: number): string {
    const totalSeconds = frames / fps
    const minutes = Math.floor(totalSeconds / 60)
    const seconds = Math.floor(totalSeconds % 60)
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

export function FrameTrimmer({
    frameCount,
    trimStart,
    trimEnd,
    onTrimChange,
    fps = 30,
    className
}: FrameTrimmerProps) {
    const handleStartChange = useCallback((value: number[]) => {
        const newStart = value[0]
        if (newStart < trimEnd) {
            onTrimChange(newStart, trimEnd)
        }
    }, [trimEnd, onTrimChange])

    const handleEndChange = useCallback((value: number[]) => {
        const newEnd = value[0]
        if (newEnd > trimStart) {
            onTrimChange(trimStart, newEnd)
        }
    }, [trimStart, onTrimChange])

    const startPercent = (trimStart / frameCount) * 100
    const endPercent = (trimEnd / frameCount) * 100

    return (
        <Card className={cn('overflow-hidden', className)}>
            <CardHeader className="pb-3">
                <CardTitle className="text-lg">Frame Range</CardTitle>
                <CardDescription>
                    Select the frame range to process
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* Visual range indicator */}
                <div className="relative h-2 rounded-full bg-zinc-700">
                    <div
                        className="absolute h-full rounded-full bg-gradient-to-r from-red-500 to-orange-500"
                        style={{
                            left: `${startPercent}%`,
                            width: `${endPercent - startPercent}%`
                        }}
                    />
                </div>

                {/* Start frame slider */}
                <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                        <span className="text-zinc-400">Start Frame</span>
                        <span className="text-white font-mono">
                            {trimStart} ({formatTime(trimStart, fps)})
                        </span>
                    </div>
                    <Slider
                        value={[trimStart]}
                        min={0}
                        max={frameCount - 1}
                        step={1}
                        onValueChange={handleStartChange}
                        className="cursor-pointer"
                    />
                </div>

                {/* End frame slider */}
                <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                        <span className="text-zinc-400">End Frame</span>
                        <span className="text-white font-mono">
                            {trimEnd} ({formatTime(trimEnd, fps)})
                        </span>
                    </div>
                    <Slider
                        value={[trimEnd]}
                        min={1}
                        max={frameCount}
                        step={1}
                        onValueChange={handleEndChange}
                        className="cursor-pointer"
                    />
                </div>

                {/* Summary */}
                <div className="flex justify-between text-xs text-zinc-500 border-t border-zinc-800 pt-3">
                    <span>Total: {frameCount} frames</span>
                    <span>Selected: {trimEnd - trimStart} frames</span>
                    <span>Duration: {formatTime(trimEnd - trimStart, fps)}</span>
                </div>
            </CardContent>
        </Card>
    )
}
