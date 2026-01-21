import { useState } from 'react'
import { QueryClient, QueryClientProvider, useMutation } from '@tanstack/react-query'
import { MainLayout } from '@/components/layout/MainLayout'
import { FileUploader } from '@/components/custom/FileUploader'
import { Preview } from '@/components/custom/Preview'
import { Terminal } from '@/components/custom/Terminal'
import { ProgressBar } from '@/components/custom/ProgressBar'
import { Button } from '@/components/ui/button'
import { uploadSource, uploadTarget, startProcess, type UploadResponse } from '@/lib/api'
import { useWebSocket } from '@/hooks/useWebSocket'
import { Play, Loader2, RotateCcw, Sparkles } from 'lucide-react'

const queryClient = new QueryClient()

function Dashboard() {
  const [sourceFile, setSourceFile] = useState<UploadResponse | null>(null)
  const [targetFile, setTargetFile] = useState<UploadResponse | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)

  const { logs, progress, status, isConnected, isComplete, clearLogs } = useWebSocket()

  const uploadSourceMutation = useMutation({
    mutationFn: uploadSource,
    onSuccess: (data) => {
      setSourceFile(data)
    },
  })

  const uploadTargetMutation = useMutation({
    mutationFn: uploadTarget,
    onSuccess: (data) => {
      setTargetFile(data)
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
    onSettled: () => {
      // Don't reset isProcessing here, wait for WebSocket complete
    }
  })

  // Reset processing state when complete
  if (isComplete && isProcessing) {
    setIsProcessing(false)
  }

  const handleProcess = () => {
    if (sourceFile && targetFile) {
      processMutation.mutate({})
    }
  }

  const handleReset = () => {
    setSourceFile(null)
    setTargetFile(null)
    setIsProcessing(false)
    clearLogs()
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
            onFileSelect={(file) => uploadSourceMutation.mutate(file)}
            isLoading={uploadSourceMutation.isPending}
            uploadedFile={sourceFile}
            onClear={() => setSourceFile(null)}
          />
          <FileUploader
            title="Target"
            description="Upload the image/video to swap faces in"
            onFileSelect={(file) => uploadTargetMutation.mutate(file)}
            isLoading={uploadTargetMutation.isPending}
            uploadedFile={targetFile}
            onClear={() => setTargetFile(null)}
          />
        </div>

        {/* Preview and Terminal */}
        <div className="grid gap-4 lg:grid-cols-2">
          <Preview isLoading={isProcessing} />
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
