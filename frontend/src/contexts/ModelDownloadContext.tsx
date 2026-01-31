import { createContext, useContext } from 'react'

export interface DownloadProgress {
  status: 'idle' | 'starting' | 'downloading' | 'verifying' | 'complete' | 'error'
  progress: number  // 0-100
  currentSize?: string
  totalSize?: string
  message?: string
  model?: string
  provider?: string
}

export interface ModelDownloadContextValue {
  downloadProgress: DownloadProgress
  isDownloading: boolean
  startDownload: (provider: string, model: string, authToken?: string) => void
  cancelDownload: () => void
}

export const ModelDownloadContext = createContext<ModelDownloadContextValue | undefined>(undefined)

export const useModelDownload = (): ModelDownloadContextValue => {
  const context = useContext(ModelDownloadContext)
  if (!context) {
    throw new Error('useModelDownload must be used within a ModelDownloadProvider')
  }
  return context
}

export default ModelDownloadContext
