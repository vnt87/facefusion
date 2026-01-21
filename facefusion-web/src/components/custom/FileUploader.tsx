import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, X, Image, Video } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

interface FileUploaderProps {
    title: string
    description: string
    accept?: Record<string, string[]>
    onFileSelect: (file: File) => void
    isLoading?: boolean
    uploadedFile?: {
        filename: string
        is_image: boolean
        is_video: boolean
    } | null
    onClear?: () => void
}

export function FileUploader({
    title,
    description,
    accept = {
        'image/*': ['.jpg', '.jpeg', '.png', '.webp'],
        'video/*': ['.mp4', '.avi', '.mov', '.mkv']
    },
    onFileSelect,
    isLoading = false,
    uploadedFile,
    onClear
}: FileUploaderProps) {
    const [dragActive, setDragActive] = useState(false)

    const onDrop = useCallback((acceptedFiles: File[]) => {
        if (acceptedFiles.length > 0) {
            onFileSelect(acceptedFiles[0])
        }
    }, [onFileSelect])

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept,
        multiple: false,
        onDragEnter: () => setDragActive(true),
        onDragLeave: () => setDragActive(false)
    })

    return (
        <Card className="overflow-hidden">
            <CardHeader className="pb-3">
                <CardTitle className="text-lg">{title}</CardTitle>
                <CardDescription>{description}</CardDescription>
            </CardHeader>
            <CardContent>
                {uploadedFile ? (
                    <div className="relative flex items-center gap-3 rounded-lg border bg-muted/50 p-4">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                            {uploadedFile.is_image ? (
                                <Image className="h-5 w-5 text-primary" />
                            ) : (
                                <Video className="h-5 w-5 text-primary" />
                            )}
                        </div>
                        <div className="flex-1 truncate">
                            <p className="truncate text-sm font-medium">{uploadedFile.filename}</p>
                            <p className="text-xs text-muted-foreground">
                                {uploadedFile.is_image ? 'Image' : 'Video'}
                            </p>
                        </div>
                        {onClear && (
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8"
                                onClick={onClear}
                            >
                                <X className="h-4 w-4" />
                            </Button>
                        )}
                    </div>
                ) : (
                    <div
                        {...getRootProps()}
                        className={cn(
                            'flex h-32 cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed transition-colors',
                            isDragActive || dragActive
                                ? 'border-primary bg-primary/5'
                                : 'border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50',
                            isLoading && 'pointer-events-none opacity-50'
                        )}
                    >
                        <input {...getInputProps()} />
                        <Upload className={cn(
                            'mb-2 h-8 w-8',
                            isDragActive ? 'text-primary' : 'text-muted-foreground'
                        )} />
                        <p className="text-sm text-muted-foreground">
                            {isDragActive ? 'Drop file here' : 'Drag & drop or click to upload'}
                        </p>
                    </div>
                )}
            </CardContent>
        </Card>
    )
}
