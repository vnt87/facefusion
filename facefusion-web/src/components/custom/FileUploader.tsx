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

    const hasPreview = previewUrl && uploadedFile

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept,
        multiple: false,
        noClick: !!hasPreview // Disable click on root if preview exists
    })

    const handleClear = () => {
        setPreviewUrl(null)
        if (videoRef.current) {
            videoRef.current.pause()
            videoRef.current.src = ''
        }
        onClear?.()
    }

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
                    <div
                        {...getRootProps()}
                        className="relative rounded-lg overflow-hidden bg-zinc-800 cursor-pointer group"
                    >
                        <input {...getInputProps()} />
                        {uploadedFile.is_image && (
                            <img
                                src={previewUrl}
                                alt={uploadedFile.filename}
                                className="w-full h-96 object-contain"
                            />
                        )}
                        {uploadedFile.is_video && (
                            <video
                                ref={videoRef}
                                src={previewUrl}
                                controls
                                className="w-full h-96 object-contain"
                                preload="metadata"
                            />
                        )}
                        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-2 pointer-events-none">
                            <p className="text-xs text-white truncate">{uploadedFile.filename}</p>
                        </div>

                        {/* Drag Overlay */}
                        {isDragActive && (
                            <div className="absolute inset-0 bg-black/60 flex flex-col items-center justify-center text-white border-2 border-primary border-dashed rounded-lg z-10 pointer-events-none">
                                <Upload className="h-10 w-10 mb-2 text-primary" />
                                <p className="font-medium">Drop to replace</p>
                            </div>
                        )}

                        {/* Hover Overlay (optional hint) */}
                        {!isDragActive && (
                            <div className="absolute inset-0 bg-black/0 hover:bg-black/10 transition-colors flex items-center justify-center opacity-0 hover:opacity-100 pointer-events-none">
                                <div className="bg-black/50 px-3 py-1 rounded-full text-xs text-white backdrop-blur-sm">
                                    Drop to replace
                                </div>
                            </div>
                        )}
                    </div>
                ) : (
                    <div
                        {...getRootProps()}
                        className={cn(
                            'flex h-32 cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed transition-colors',
                            isDragActive
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
