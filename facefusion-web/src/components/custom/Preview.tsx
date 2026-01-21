import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface PreviewProps {
    imageSrc?: string | null
    isLoading?: boolean
    className?: string
}

export function Preview({ imageSrc, isLoading = false, className }: PreviewProps) {
    return (
        <Card className={cn('overflow-hidden', className)}>
            <CardHeader className="pb-3">
                <CardTitle className="text-lg">Preview</CardTitle>
                <CardDescription>Live preview of face swap result</CardDescription>
            </CardHeader>
            <CardContent>
                <div className={cn(
                    'flex aspect-video items-center justify-center rounded-lg bg-muted/50 overflow-hidden',
                    isLoading && 'animate-pulse'
                )}>
                    {imageSrc ? (
                        <img
                            src={imageSrc}
                            alt="Preview"
                            className="h-full w-full object-contain"
                        />
                    ) : (
                        <div className="text-center">
                            <div className="mb-2 text-4xl">🎭</div>
                            <p className="text-sm text-muted-foreground">
                                {isLoading ? 'Processing...' : 'Upload source and target to see preview'}
                            </p>
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    )
}
