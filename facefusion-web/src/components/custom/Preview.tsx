import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Slider } from '@/components/ui/slider'
import { cn } from '@/lib/utils'
import { Loader2 } from 'lucide-react'

interface PreviewProps {
    previewImage?: string | null
    isLoading?: boolean
    isVideo?: boolean
    frameCount?: number
    currentFrame?: number
    onFrameChange?: (frame: number) => void
    className?: string
}

export function Preview({
    previewImage,
    isLoading = false,
    isVideo = false,
    frameCount = 0,
    currentFrame = 0,
    onFrameChange,
    className
}: PreviewProps) {
    return (
        <Card className={cn('overflow-hidden', className)}>
            <CardHeader className="pb-3">
                <CardTitle className="text-lg">Preview</CardTitle>
                <CardDescription>Live preview of face swap result</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className={cn(
                    'flex aspect-video items-center justify-center rounded-lg bg-zinc-800 overflow-hidden relative'
                )}>
                    {isLoading && (
                        <div className="absolute inset-0 flex items-center justify-center bg-zinc-900/80 z-10">
                            <div className="flex flex-col items-center gap-2">
                                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                                <span className="text-sm text-zinc-400">Generating preview...</span>
                            </div>
                        </div>
                    )}
                    {previewImage ? (
                        <img
                            src={previewImage}
                            alt="Preview"
                            className="h-full w-full object-contain"
                        />
                    ) : (
                        <div className="text-center">
                            <div className="mb-2 text-4xl">🎭</div>
                            <p className="text-sm text-muted-foreground">
                                Upload source and target to see preview
                            </p>
                        </div>
                    )}
                </div>


                {/* Frame slider for videos */}
                {isVideo && frameCount > 0 && (
                    <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                            <span className="text-zinc-400">Frame</span>
                            <span className="text-white font-mono">
                                {currentFrame} / {frameCount}
                            </span>
                        </div>
                        <Slider
                            value={[currentFrame]}
                            min={0}
                            max={frameCount - 1}
                            step={1}
                            onValueChange={(value) => onFrameChange?.(value[0])}
                            className="cursor-pointer"
                        />
                    </div>
                )}
            </CardContent>
        </Card>
    )
}

