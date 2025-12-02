import React, { createContext, useContext, useState, useCallback, useRef, ReactNode } from 'react'
import { useToaster } from './ToasterContext'

interface DownloadProgress {
  status: 'idle' | 'starting' | 'downloading' | 'verifying' | 'complete' | 'error'
  progress: number  // 0-100
  currentSize?: string
  totalSize?: string
  message?: string
  model?: string
  provider?: string
}

interface ModelDownloadContextValue {
  downloadProgress: DownloadProgress
  isDownloading: boolean
  startDownload: (provider: string, model: string, authToken?: string) => void
  cancelDownload: () => void
}

const ModelDownloadContext = createContext<ModelDownloadContextValue | undefined>(undefined)

export const useModelDownload = (): ModelDownloadContextValue => {
  const context = useContext(ModelDownloadContext)
  if (!context) {
    throw new Error('useModelDownload must be used within a ModelDownloadProvider')
  }
  return context
}

interface ModelDownloadProviderProps {
  children: ReactNode
}

export const ModelDownloadProvider: React.FC<ModelDownloadProviderProps> = ({ children }) => {
  const [downloadProgress, setDownloadProgress] = useState<DownloadProgress>({
    status: 'idle',
    progress: 0,
  })
  
  const abortControllerRef = useRef<AbortController | null>(null)
  const toaster = useToaster()

  const startDownload = useCallback((provider: string, model: string, authToken?: string) => {
    // Cancel any existing download
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }

    // Create new abort controller
    abortControllerRef.current = new AbortController()

    // Set initial state
    setDownloadProgress({
      status: 'starting',
      progress: 0,
      message: `Starting download of ${model}...`,
      model,
      provider,
    })

    // Start SSE connection
    const fetchDownload = async () => {
      try {
        const requestBody: { provider: string; model: string; auth_token?: string } = { provider, model }
        if (authToken) {
          requestBody.auth_token = authToken
        }
        
        const response = await fetch('/api/models/pull', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(requestBody),
          signal: abortControllerRef.current?.signal,
        })

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
          throw new Error(errorData.detail || `HTTP ${response.status}`)
        }

        const reader = response.body?.getReader()
        if (!reader) {
          throw new Error('No response body')
        }

        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          
          // Process SSE messages
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''  // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                
                // Update progress state
                setDownloadProgress({
                  status: data.status || 'downloading',
                  progress: data.progress || 0,
                  currentSize: data.current_size,
                  totalSize: data.total_size,
                  message: data.message,
                  model,
                  provider,
                })

                // Show toaster notification on completion or error
                if (data.status === 'complete') {
                  toaster.success(`Model ${model} is ready to use`)
                  abortControllerRef.current = null

                  // Trigger provider list refresh so new model appears in dropdown
                  window.dispatchEvent(new CustomEvent('model-download-complete', {
                    detail: { provider, model }
                  }))

                  return
                } else if (data.status === 'error') {
                  toaster.error(data.message || `Failed to download ${model}`)
                  abortControllerRef.current = null
                  return
                }
              } catch (e) {
                // Ignore parse errors
              }
            }
          }
        }
      } catch (error: any) {
        if (error.name === 'AbortError') {
          setDownloadProgress({
            status: 'idle',
            progress: 0,
            message: 'Download cancelled',
            model,
            provider,
          })
        } else {
          setDownloadProgress({
            status: 'error',
            progress: 0,
            message: error.message || 'Download failed',
            model,
            provider,
          })
          toaster.error(error.message || `Failed to download ${model}`)
        }
      }
    }

    fetchDownload()
  }, [toaster])

  const cancelDownload = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setDownloadProgress({
      status: 'idle',
      progress: 0,
    })
    toaster.info('Download cancelled')
  }, [toaster])

  const isDownloading = downloadProgress.status === 'downloading' || 
                        downloadProgress.status === 'starting' || 
                        downloadProgress.status === 'verifying'

  return (
    <ModelDownloadContext.Provider value={{ downloadProgress, isDownloading, startDownload, cancelDownload }}>
      {children}
    </ModelDownloadContext.Provider>
  )
}

export default ModelDownloadContext
