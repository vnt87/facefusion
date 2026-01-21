import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface ProgressBarProps {
    progress: number
    status: string
    isConnected: boolean
    className?: string
}

export function ProgressBar({ progress, status, isConnected, className }: ProgressBarProps) {
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
                <CardDescription>{status}</CardDescription>
            </CardHeader>
            <CardContent>
                <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">Processing</span>
                        <span className="font-medium">{Math.round(progress)}%</span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
                        <div
                            className="h-full bg-gradient-to-r from-red-500 to-orange-500 transition-all duration-300 ease-out"
                            style={{ width: `${progress}%` }}
                        />
                    </div>
                </div>
            </CardContent>
        </Card>
    )
}
