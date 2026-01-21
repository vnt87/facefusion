import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface ProgressBarProps {
    progress: number
    status: string
    isConnected: boolean
    isError?: boolean
    currentFrame?: number
    totalFrames?: number
    speed?: number
    executionProviders?: string
    className?: string
}

export function ProgressBar({
    progress,
    status,
    isConnected,
    isError,
    currentFrame = 0,
    totalFrames = 0,
    speed = 0,
    executionProviders = '',
    className
}: ProgressBarProps) {
    const hasExtendedInfo = totalFrames > 0

    return (
        <Card className={cn('overflow-hidden', className)}>
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">Progress</CardTitle>
                    <div className="flex items-center gap-2">
                        <div className={cn(
                            'h-2 w-2 rounded-full',
                            isConnected ? 'bg-green-500' : 'bg-red-500'
                        )} />
                        <span className="text-xs text-muted-foreground">
                            {isConnected ? 'Connected' : 'Disconnected'}
                        </span>
                    </div>
                </div>
                <CardDescription className={cn(isError && 'text-red-500 font-medium')}>
                    {status}
                </CardDescription>
            </CardHeader>
            <CardContent>
                <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">
                            {hasExtendedInfo
                                ? `Frame ${currentFrame}/${totalFrames}`
                                : 'Processing'}
                        </span>
                        <span className={cn('font-medium', isError && 'text-red-500')}>
                            {Math.round(progress)}%
                        </span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
                        <div
                            className={cn(
                                'h-full transition-all duration-300 ease-out',
                                isError
                                    ? 'bg-red-500'
                                    : 'bg-gradient-to-r from-red-500 to-orange-500'
                            )}
                            style={{ width: `${progress}%` }}
                        />
                    </div>
                    {hasExtendedInfo && (
                        <div className="flex items-center justify-between text-xs text-muted-foreground pt-1">
                            <span>
                                {speed > 0 ? `${speed.toFixed(2)} frames/s` : ''}
                            </span>
                            <span>
                                {executionProviders ? executionProviders.toUpperCase() : ''}
                            </span>
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    )
}

