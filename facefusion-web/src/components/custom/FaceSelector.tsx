import { cn } from '@/lib/utils'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Loader2 } from 'lucide-react'
import type { DetectedFace } from '@/lib/api'

interface FaceSelectorProps {
    faces: DetectedFace[]
    selectedIndex: number
    onSelect: (index: number) => void
    isLoading?: boolean
    className?: string
}

export function FaceSelector({
    faces,
    selectedIndex,
    onSelect,
    isLoading = false,
    className
}: FaceSelectorProps) {
    if (isLoading) {
        return (
            <Card className={cn('overflow-hidden', className)}>
                <CardHeader className="pb-3">
                    <CardTitle className="text-lg">Reference Face</CardTitle>
                    <CardDescription>Detecting faces in target...</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="flex h-24 items-center justify-center">
                        <Loader2 className="h-6 w-6 animate-spin text-primary" />
                    </div>
                </CardContent>
            </Card>
        )
    }

    if (faces.length === 0) {
        return null
    }

    return (
        <Card className={cn('overflow-hidden', className)}>
            <CardHeader className="pb-3">
                <CardTitle className="text-lg">Reference Face</CardTitle>
                <CardDescription>
                    Select the face to swap ({faces.length} detected)
                </CardDescription>
            </CardHeader>
            <CardContent>
                <div className="grid grid-cols-7 gap-2">
                    {faces.map((face) => (
                        <button
                            key={face.index}
                            onClick={() => onSelect(face.index)}
                            className={cn(
                                'relative aspect-square overflow-hidden rounded-lg border-2 transition-all hover:scale-105',
                                selectedIndex === face.index
                                    ? 'border-primary ring-2 ring-primary ring-offset-2 ring-offset-zinc-900'
                                    : 'border-zinc-700 hover:border-zinc-500'
                            )}
                        >
                            <img
                                src={`data:image/jpeg;base64,${face.image_base64}`}
                                alt={`Face ${face.index + 1}`}
                                className="h-full w-full object-cover"
                            />
                            {selectedIndex === face.index && (
                                <div className="absolute inset-0 bg-primary/20" />
                            )}
                        </button>
                    ))}
                </div>
            </CardContent>
        </Card>
    )
}
