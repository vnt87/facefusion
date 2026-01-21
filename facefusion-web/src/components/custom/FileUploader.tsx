import { useCallback, useState, useEffect, useRef } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, X } from 'lucide-react'
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
        file_id?: string
    } | null
    onClear?: () => void
    localFile?: File | null
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
    onClear,
    localFile
}: FileUploaderProps) {
    const [dragActive, setDragActive] = useState(false)
    const [previewUrl, setPreviewUrl] = useState<string | null>(null)
    const videoRef = useRef<HTMLVideoElement>(null)

    // Create preview URL from local file
    useEffect(() => {
        if (localFile) {
            const url = URL.createObjectURL(localFile)
            setPreviewUrl(url)
            return () => URL.revokeObjectURL(url)
        } else {
            setPreviewUrl(null)
        }
    }, [localFile])

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

    const handleClear = () => {
        setPreviewUrl(null)
        if (videoRef.current) {
            videoRef.current.pause()
            videoRef.current.src = ''
        }
        onClear?.()
    }

    const hasPreview = previewUrl && uploadedFile

    return (
        <Card className="overflow-hidden">
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="text-lg">{title}</CardTitle>
                        <CardDescription>{description}</CardDescription>
                    </div>
                    {hasPreview && (
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-zinc-400 hover:text-white"
                            onClick={handleClear}
                        >
                            <X className="h-4 w-4" />
                        </Button>
                    )}
                </div>
            </CardHeader>
            <CardContent>
                {hasPreview ? (
                    <div className="relative rounded-lg overflow-hidden bg-zinc-800">
                        {uploadedFile.is_image && (
                            <img
                                src={previewUrl}
                                alt={uploadedFile.filename}
                                className="w-full h-48 object-contain"
                            />
                        )}
                        {uploadedFile.is_video && (
                            <video
                                ref={videoRef}
                                src={previewUrl}
                                controls
                                className="w-full h-48 object-contain"
                                preload="metadata"
                            />
                        )}
                        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-2">
                            <p className="text-xs text-white truncate">{uploadedFile.filename}</p>
                        </div>
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
                            {isLoading ? 'Uploading...' : isDragActive ? 'Drop file here' : 'Drag & drop or click to upload'}
                        </p>
                    </div>
                )}
            </CardContent>
        </Card>
    )
}
