import { useState, useEffect, useCallback } from 'react'
import { QueryClient, QueryClientProvider, useMutation } from '@tanstack/react-query'
import { MainLayout } from '@/components/layout/MainLayout'
import { FileUploader } from '@/components/custom/FileUploader'
import { Preview } from '@/components/custom/Preview'
import { Terminal } from '@/components/custom/Terminal'
import { ProgressBar } from '@/components/custom/ProgressBar'
import { FaceSelector } from '@/components/custom/FaceSelector'
import { FrameTrimmer } from '@/components/custom/FrameTrimmer'
import { Button } from '@/components/ui/button'
import {
  uploadSource,
  uploadTarget,
  startProcess,
  detectFaces,
  getPreviewFrame,
  getVideoInfo,
  type UploadResponse,
  type DetectedFace,
  type VideoInfoResponse
} from '@/lib/api'
import { useWebSocket } from '@/hooks/useWebSocket'
import { Play, Loader2, RotateCcw, Sparkles } from 'lucide-react'

const queryClient = new QueryClient()

function Dashboard() {
  // File state
  const [sourceFile, setSourceFile] = useState<UploadResponse | null>(null)
  const [targetFile, setTargetFile] = useState<UploadResponse | null>(null)
  const [sourceLocalFile, setSourceLocalFile] = useState<File | null>(null)
  const [targetLocalFile, setTargetLocalFile] = useState<File | null>(null)

  // Face detection state
  const [detectedFaces, setDetectedFaces] = useState<DetectedFace[]>([])
  const [selectedFaceIndex, setSelectedFaceIndex] = useState(0)
  const [isDetectingFaces, setIsDetectingFaces] = useState(false)

  // Video/frame state
  const [videoInfo, setVideoInfo] = useState<VideoInfoResponse | null>(null)
  const [currentFrame, setCurrentFrame] = useState(0)
  const [trimStart, setTrimStart] = useState(0)
  const [trimEnd, setTrimEnd] = useState(0)

  // Preview state
  const [previewImage, setPreviewImage] = useState<string | null>(null)
  const [isLoadingPreview, setIsLoadingPreview] = useState(false)

  // Processing state
  const [isProcessing, setIsProcessing] = useState(false)

  const { logs, progress, status, isConnected, isComplete, clearLogs } = useWebSocket()

  // Upload mutations
  const uploadSourceMutation = useMutation({
    mutationFn: uploadSource,
    onSuccess: (data) => {
      setSourceFile(data)
    },
  })

  const uploadTargetMutation = useMutation({
    mutationFn: uploadTarget,
    onSuccess: async (data) => {
      setTargetFile(data)
      setDetectedFaces([])
      setSelectedFaceIndex(0)
      setCurrentFrame(0)
      setPreviewImage(null)

      // Detect faces in the target
      setIsDetectingFaces(true)
      try {
        const faceResult = await detectFaces(0)
        setDetectedFaces(faceResult.faces)
        if (faceResult.faces.length > 0) {
          setSelectedFaceIndex(0)
        }
      } catch (error) {
        console.error('Face detection failed:', error)
      } finally {
        setIsDetectingFaces(false)
      }

      // Get video info if target is video
      if (data.is_video) {
        try {
          const info = await getVideoInfo()
          setVideoInfo(info)
          setTrimStart(0)
          setTrimEnd(info.frame_count)
        } catch (error) {
          console.error('Failed to get video info:', error)
        }
      } else {
        setVideoInfo(null)
      }
    },
  })

  const processMutation = useMutation({
    mutationFn: startProcess,
    onMutate: () => {
      setIsProcessing(true)
    },
    onSuccess: () => {
      // Processing started, WebSocket will handle updates
    },
    onError: () => {
      setIsProcessing(false)
    },
  })

  // Reset processing state when complete
  useEffect(() => {
    if (isComplete && isProcessing) {
      setIsProcessing(false)
    }
  }, [isComplete, isProcessing])

  // Generate preview when conditions are met
  const updatePreview = useCallback(async () => {
    if (!sourceFile || !targetFile || detectedFaces.length === 0) {
      setPreviewImage(null)
      return
    }

    setIsLoadingPreview(true)
    try {
      const result = await getPreviewFrame(currentFrame, selectedFaceIndex)
      setPreviewImage(`data:image/jpeg;base64,${result.image_base64}`)
    } catch (error) {
      console.error('Preview generation failed:', error)
      setPreviewImage(null)
    } finally {
      setIsLoadingPreview(false)
    }
  }, [sourceFile, targetFile, detectedFaces.length, currentFrame, selectedFaceIndex])

  // Update preview when dependencies change
  useEffect(() => {
    if (sourceFile && targetFile && detectedFaces.length > 0) {
      const debounceTimer = setTimeout(() => {
        updatePreview()
      }, 300)
      return () => clearTimeout(debounceTimer)
    }
  }, [sourceFile, targetFile, detectedFaces.length, currentFrame, selectedFaceIndex, updatePreview])

  const handleSourceSelect = (file: File) => {
    setSourceLocalFile(file)
    uploadSourceMutation.mutate(file)
  }

  const handleTargetSelect = (file: File) => {
    setTargetLocalFile(file)
    uploadTargetMutation.mutate(file)
  }

  const handleProcess = () => {
    if (sourceFile && targetFile) {
      const options: { trimFrameStart?: number; trimFrameEnd?: number } = {}
      if (targetFile.is_video && videoInfo) {
        if (trimStart > 0) options.trimFrameStart = trimStart
        if (trimEnd < videoInfo.frame_count) options.trimFrameEnd = trimEnd
      }
      processMutation.mutate(options)
    }
  }

  const handleReset = () => {
    setSourceFile(null)
    setTargetFile(null)
    setSourceLocalFile(null)
    setTargetLocalFile(null)
    setDetectedFaces([])
    setSelectedFaceIndex(0)
    setVideoInfo(null)
    setCurrentFrame(0)
    setTrimStart(0)
    setTrimEnd(0)
    setPreviewImage(null)
    setIsProcessing(false)
    clearLogs()
  }

  const handleClearSource = () => {
    setSourceFile(null)
    setSourceLocalFile(null)
    setPreviewImage(null)
  }

  const handleClearTarget = () => {
    setTargetFile(null)
    setTargetLocalFile(null)
    setDetectedFaces([])
    setSelectedFaceIndex(0)
    setVideoInfo(null)
    setCurrentFrame(0)
    setPreviewImage(null)
  }

  const handleFaceSelect = async (index: number) => {
    setSelectedFaceIndex(index)
  }

  const handleFrameChange = (frame: number) => {
    setCurrentFrame(frame)
  }

  const handleTrimChange = (start: number, end: number) => {
    setTrimStart(start)
    setTrimEnd(end)
  }

  const canProcess = sourceFile && targetFile && !isProcessing

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-red-500 to-orange-500 shadow-lg shadow-red-500/25">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold tracking-tight text-white">Face Swap Studio</h2>
              <p className="text-sm text-zinc-400">
                Upload your source and target files to begin
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={handleReset}
              className="gap-2 border-zinc-700 bg-zinc-800/50 text-zinc-300 hover:bg-zinc-700 hover:text-white"
            >
              <RotateCcw className="h-4 w-4" />
              Reset
            </Button>
            <Button
              size="lg"
              onClick={handleProcess}
              disabled={!canProcess}
              className="gap-2 bg-gradient-to-r from-red-500 to-orange-500 text-white shadow-lg shadow-red-500/25 hover:from-red-600 hover:to-orange-600"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Start Processing
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Progress Bar */}
        <ProgressBar
          progress={progress}
          status={status}
          isConnected={isConnected}
        />

        {/* File Uploaders */}
        <div className="grid gap-4 md:grid-cols-2">
          <FileUploader
            title="Source"
            description="Upload the face you want to use"
            onFileSelect={handleSourceSelect}
            isLoading={uploadSourceMutation.isPending}
            uploadedFile={sourceFile}
            localFile={sourceLocalFile}
            onClear={handleClearSource}
          />
          <div className="space-y-4">
            <FileUploader
              title="Target"
              description="Upload the image/video to swap faces in"
              onFileSelect={handleTargetSelect}
              isLoading={uploadTargetMutation.isPending}
              uploadedFile={targetFile}
              localFile={targetLocalFile}
              onClear={handleClearTarget}
            />
            {/* Face Selector - shown when faces are detected */}
            {(isDetectingFaces || detectedFaces.length > 0) && (
              <FaceSelector
                faces={detectedFaces}
                selectedIndex={selectedFaceIndex}
                onSelect={handleFaceSelect}
                isLoading={isDetectingFaces}
              />
            )}
          </div>
        </div>

        {/* Frame Trimmer - shown for videos */}
        {targetFile?.is_video && videoInfo && (
          <FrameTrimmer
            frameCount={videoInfo.frame_count}
            trimStart={trimStart}
            trimEnd={trimEnd}
            onTrimChange={handleTrimChange}
            fps={videoInfo.fps}
          />
        )}

        {/* Preview and Terminal */}
        <div className="grid gap-4 lg:grid-cols-2">
          <Preview
            previewImage={previewImage}
            isLoading={isLoadingPreview}
            isVideo={targetFile?.is_video}
            frameCount={videoInfo?.frame_count || 0}
            currentFrame={currentFrame}
            onFrameChange={handleFrameChange}
          />
          <Terminal logs={logs} />
        </div>
      </div>
    </MainLayout>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="dark">
        <Dashboard />
      </div>
    </QueryClientProvider>
  )
}

export default App

