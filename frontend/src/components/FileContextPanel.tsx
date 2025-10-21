import React, { useState, useEffect, useCallback } from 'react'
import { Upload, File, X, Database, BarChart3, FileText } from 'lucide-react'
import { filesAPI, handleAPIError } from '../services/api'
import FileViewerModal from './FileViewerModal'

interface FileInfo {
  name: string
  path: string
  size: number
  type: 'csv' | 'json' | 'xlsx' | 'txt' | 'other'
  lastModified: string
  preview?: {
    rows: number
    columns: string[]
    shape: [number, number]
  }
}

interface FileContextPanelProps {
  notebookId?: string
  onFilesChange: (files: FileInfo[]) => void
  refreshTrigger?: number
}

const FileContextPanel: React.FC<FileContextPanelProps> = ({ notebookId, onFilesChange, refreshTrigger }) => {
  const [contextFiles, setContextFiles] = useState<FileInfo[]>([])
  const [isExpanded, setIsExpanded] = useState(true)
  const [isDragOver, setIsDragOver] = useState(false)
  const [selectedFile, setSelectedFile] = useState<FileInfo | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  // Load available files on component mount and when notebook ID or refresh trigger changes
  useEffect(() => {
    loadAvailableFiles()
  }, [notebookId, refreshTrigger])

  const loadAvailableFiles = useCallback(async () => {
    if (!notebookId) {
      // No notebook ID, show empty state
      setContextFiles([])
      onFilesChange([])
      return
    }

    try {
      const files = await filesAPI.list(notebookId)
      const formattedFiles: FileInfo[] = files.map(file => ({
        name: file.name,
        path: file.path,
        size: file.size,
        type: file.type as FileInfo['type'],
        lastModified: file.lastModified,
        preview: file.preview
      }))
      
      setContextFiles(formattedFiles)
      onFilesChange(formattedFiles)
    } catch (error) {
      const apiError = handleAPIError(error)
      console.error('Failed to load files:', apiError.message)
      // Show empty state on error
      setContextFiles([])
      onFilesChange([])
    }
  }, [notebookId, onFilesChange])

  const handleFileUpload = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!notebookId) {
      console.error('No notebook ID available for file upload')
      return
    }

    const files = Array.from(event.target.files || [])
    
    // Reset input immediately
    event.target.value = ''
    
    // Upload each file to the backend
    for (const file of files) {
      try {
        console.log(`Uploading file: ${file.name}`)
        await filesAPI.upload(notebookId, file)
        console.log(`Successfully uploaded: ${file.name}`)
      } catch (error) {
        const apiError = handleAPIError(error)
        console.error(`Failed to upload ${file.name}:`, apiError.message)
        // TODO: Show user-friendly error message
      }
    }
    
    // Refresh the file list after uploads
    await loadAvailableFiles()
  }, [notebookId, loadAvailableFiles])

  const handleDrop = useCallback(async (event: React.DragEvent) => {
    event.preventDefault()
    setIsDragOver(false)
    
    if (!notebookId) {
      console.error('No notebook ID available for file upload')
      return
    }
    
    const files = Array.from(event.dataTransfer.files)
    
    // Upload each file to the backend
    for (const file of files) {
      try {
        console.log(`Uploading file via drag & drop: ${file.name}`)
        await filesAPI.upload(notebookId, file)
        console.log(`Successfully uploaded: ${file.name}`)
      } catch (error) {
        const apiError = handleAPIError(error)
        console.error(`Failed to upload ${file.name}:`, apiError.message)
        // TODO: Show user-friendly error message
      }
    }
    
    // Refresh the file list after uploads
    await loadAvailableFiles()
  }, [notebookId, loadAvailableFiles])

  const removeFile = useCallback(async (filePath: string) => {
    if (!notebookId) {
      console.error('No notebook ID available for file deletion')
      return
    }

    // Extract filename from path (e.g., "data/file.csv" -> "file.csv")
    const fileName = filePath.split('/').pop()
    if (!fileName) {
      console.error('Invalid file path:', filePath)
      return
    }

    try {
      console.log(`Deleting file: ${fileName}`)
      await filesAPI.delete(notebookId, fileName)
      console.log(`Successfully deleted: ${fileName}`)
      
      // Refresh the file list after deletion
      await loadAvailableFiles()
    } catch (error) {
      const apiError = handleAPIError(error)
      console.error(`Failed to delete ${fileName}:`, apiError.message)
      // TODO: Show user-friendly error message
    }
  }, [notebookId, loadAvailableFiles])

  const handleFileClick = useCallback((file: FileInfo) => {
    setSelectedFile(file)
    setIsModalOpen(true)
  }, [])

  const handleCloseModal = useCallback(() => {
    setIsModalOpen(false)
    setSelectedFile(null)
  }, [])

  const getFileType = (filename: string): FileInfo['type'] => {
    const ext = filename.split('.').pop()?.toLowerCase()
    switch (ext) {
      case 'csv': return 'csv'
      case 'json': return 'json'
      case 'xlsx': case 'xls': return 'xlsx'
      case 'txt': return 'txt'
      default: return 'other'
    }
  }

  const getFileIcon = (type: FileInfo['type']) => {
    switch (type) {
      case 'csv': return <BarChart3 className="h-4 w-4 text-green-600" />
      case 'json': return <Database className="h-4 w-4 text-blue-600" />
      case 'xlsx': return <FileText className="h-4 w-4 text-orange-600" />
      default: return <File className="h-4 w-4 text-gray-600" />
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return (
    <div className="bg-white border-b border-gray-200 shadow-sm">
      {/* Header */}
      <div 
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center space-x-3">
          <Database className="h-5 w-5 text-blue-600" />
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Files in Context</h3>
            <p className="text-sm text-gray-600">
              {contextFiles.length} file{contextFiles.length !== 1 ? 's' : ''} available for analysis
            </p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          {/* Upload Button - Improved UI/UX with blue styling */}
          <label className="inline-flex items-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors cursor-pointer shadow-sm">
            <Upload className="h-4 w-4 mr-2" />
            Upload Files
            <input
              type="file"
              multiple
              className="hidden"
              onChange={handleFileUpload}
              accept=".csv,.json,.xlsx,.xls,.txt"
            />
          </label>
          
        </div>
      </div>

      {/* Files Grid */}
      {isExpanded && (
        <div 
          className={`p-4 pt-0 ${isDragOver ? 'bg-blue-50 border-2 border-blue-300 border-dashed' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
        >
          {contextFiles.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Database className="h-12 w-12 mx-auto text-gray-300 mb-2" />
              <p className="text-sm">No files in context</p>
              <p className="text-xs">Drag & drop files here or use the upload button</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-2">
              {contextFiles.map((file) => (
                <div 
                  key={file.path}
                  className="bg-gray-50 border border-gray-200 rounded-md p-2 hover:bg-gray-100 transition-colors group"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2 flex-1 min-w-0">
                      {getFileIcon(file.type)}
                      <div 
                        className="flex-1 min-w-0 cursor-pointer hover:text-blue-600 hover:bg-blue-50 p-1 rounded transition-colors"
                        onClick={() => handleFileClick(file)}
                        title="Click to view file content"
                      >
                        <h4 className="text-xs font-medium text-gray-900 truncate">
                          {file.name}
                        </h4>
                        <div className="flex items-center space-x-1 text-xs text-gray-500">
                          <span>{formatFileSize(file.size)}</span>
                          {file.preview && (
                            <>
                              <span>•</span>
                              <span>{file.preview.shape[0]}×{file.preview.shape[1]}</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    <button
                      onClick={() => removeFile(file.path)}
                      className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-600 transition-all flex-shrink-0"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
          
          {/* Drag & Drop Overlay */}
          {isDragOver && (
            <div className="absolute inset-0 bg-blue-100 bg-opacity-50 flex items-center justify-center">
              <div className="text-blue-600 text-center">
                <Upload className="h-8 w-8 mx-auto mb-2" />
                <p className="font-medium">Drop files to add to context</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* File Viewer Modal */}
      <FileViewerModal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        notebookId={notebookId || ''}
        file={selectedFile}
      />
    </div>
  )
}

export default FileContextPanel
