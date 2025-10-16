import React, { useState, useEffect, useCallback } from 'react'
import { Upload, File, X, Database, BarChart3, FileText, Eye, Info } from 'lucide-react'

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
  onFilesChange: (files: FileInfo[]) => void
}

const FileContextPanel: React.FC<FileContextPanelProps> = ({ onFilesChange }) => {
  const [contextFiles, setContextFiles] = useState<FileInfo[]>([])
  const [isExpanded, setIsExpanded] = useState(true)
  const [isDragOver, setIsDragOver] = useState(false)

  // Load available files on component mount
  useEffect(() => {
    loadAvailableFiles()
  }, [])

  const loadAvailableFiles = useCallback(async () => {
    try {
      // For now, simulate some sample files
      const sampleFiles: FileInfo[] = [
        {
          name: 'gene_expression.csv',
          path: 'data/gene_expression.csv',
          size: 245760,
          type: 'csv',
          lastModified: new Date().toISOString(),
          preview: {
            rows: 20,
            columns: ['Gene_ID', 'Sample_1', 'Sample_2', 'Sample_3', 'Control_1', 'Control_2', 'Control_3'],
            shape: [20, 7]
          }
        },
        {
          name: 'patient_data.csv',
          path: 'data/patient_data.csv', 
          size: 89234,
          type: 'csv',
          lastModified: new Date().toISOString(),
          preview: {
            rows: 20,
            columns: ['Patient_ID', 'Age', 'Gender', 'Condition', 'Treatment_Response', 'Biomarker_Level'],
            shape: [20, 6]
          }
        },
        {
          name: 'customer_demographics.csv',
          path: 'data/customer_demographics.csv',
          size: 89234,
          type: 'csv',
          lastModified: new Date().toISOString(),
          preview: {
            rows: 100,
            columns: ['Customer_ID', 'Age', 'Gender', 'Income', 'Location', 'Segment'],
            shape: [100, 6]
          }
        },
        {
          name: 'sales_data.csv',
          path: 'data/sales_data.csv',
          size: 156890,
          type: 'csv', 
          lastModified: new Date().toISOString(),
          preview: {
            rows: 200,
            columns: ['Date', 'Product', 'Sales', 'Region', 'Customer_ID'],
            shape: [200, 5]
          }
        }
      ]
      
      setContextFiles(sampleFiles)
      onFilesChange(sampleFiles)
    } catch (error) {
      console.error('Failed to load files:', error)
    }
  }, [onFilesChange])

  const handleFileUpload = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || [])
    
    files.forEach(file => {
      const fileInfo: FileInfo = {
        name: file.name,
        path: `uploads/${file.name}`,
        size: file.size,
        type: getFileType(file.name),
        lastModified: new Date().toISOString()
      }
      
      setContextFiles(prev => [...prev, fileInfo])
    })
    
    // Reset input
    event.target.value = ''
  }, [])

  const handleDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    setIsDragOver(false)
    
    const files = Array.from(event.dataTransfer.files)
    
    files.forEach(file => {
      const fileInfo: FileInfo = {
        name: file.name,
        path: `uploads/${file.name}`,
        size: file.size,
        type: getFileType(file.name),
        lastModified: new Date().toISOString()
      }
      
      setContextFiles(prev => [...prev, fileInfo])
    })
  }, [])

  const removeFile = useCallback((filePath: string) => {
    setContextFiles(prev => prev.filter(f => f.path !== filePath))
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
          {/* Upload Button */}
          <label className="btn btn-secondary text-sm px-3 py-1 cursor-pointer">
            <Upload className="h-4 w-4 mr-1" />
            Upload
            <input
              type="file"
              multiple
              className="hidden"
              onChange={handleFileUpload}
              accept=".csv,.json,.xlsx,.xls,.txt"
            />
          </label>
          
          <button className="text-gray-400 hover:text-gray-600">
            <Eye className="h-4 w-4" />
          </button>
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
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {contextFiles.map((file, index) => (
                <div 
                  key={file.path}
                  className="bg-gray-50 border border-gray-200 rounded-lg p-3 hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-2 flex-1 min-w-0">
                      {getFileIcon(file.type)}
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-medium text-gray-900 truncate">
                          {file.name}
                        </h4>
                        <p className="text-xs text-gray-500 truncate">
                          {file.path}
                        </p>
                        <p className="text-xs text-gray-400">
                          {formatFileSize(file.size)}
                        </p>
                        
                        {/* File Preview Info */}
                        {file.preview && (
                          <div className="mt-2 text-xs text-gray-600 bg-white px-2 py-1 rounded border">
                            <div className="flex items-center space-x-1 mb-1">
                              <Info className="h-3 w-3" />
                              <span>{file.preview.shape[0]} rows × {file.preview.shape[1]} cols</span>
                            </div>
                            <div className="text-gray-500 truncate">
                              Columns: {file.preview.columns.slice(0, 3).join(', ')}
                              {file.preview.columns.length > 3 && `... +${file.preview.columns.length - 3} more`}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                    
                    <button
                      onClick={() => removeFile(file.path)}
                      className="text-gray-400 hover:text-red-600 ml-2 flex-shrink-0"
                    >
                      <X className="h-4 w-4" />
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
    </div>
  )
}

export default FileContextPanel
