import React, { useState, useEffect } from 'react'
import { X, FileText, Image as ImageIcon, Table, Code, Eye, FileSpreadsheet } from 'lucide-react'
import { filesAPI } from '../services/api'
import { FileInfo } from '../types'
import H5FileViewer from './H5FileViewer'
import ExcelFileViewer from './ExcelFileViewer'
import MarkdownRenderer from './MarkdownRenderer'

interface FileViewerModalProps {
  isOpen: boolean
  onClose: () => void
  notebookId: string
  file: FileInfo | null
}

interface FileContent {
  content: string
  error?: string
  contentType?: string
  isBase64?: boolean
}

const FileViewerModal: React.FC<FileViewerModalProps> = ({ isOpen, onClose, notebookId, file }) => {
  const [fileContent, setFileContent] = useState<FileContent | null>(null)
  const [loading, setLoading] = useState(false)
  const [viewMode, setViewMode] = useState<'raw' | 'formatted'>('formatted')

  // Determine file type from extension
  const getFileExtension = (filename: string): string => {
    return filename.split('.').pop()?.toLowerCase() || ''
  }

  const getFileTypeFromName = (filename: string): string => {
    const ext = getFileExtension(filename)
    switch (ext) {
      case 'csv': return 'csv'
      case 'tsv': return 'tsv'
      case 'txt': return 'txt'
      case 'md': return 'markdown'
      case 'json': return 'json'
      case 'yaml': case 'yml': return 'yaml'
      case 'xlsx': case 'xls': return 'excel'
      case 'h5': case 'hdf5': case 'h5ad': return 'h5'
      case 'jpg': case 'jpeg': case 'png': case 'gif': case 'webp': case 'tif': case 'tiff': return 'image'
      default: return 'text'
    }
  }

  // Handle keyboard events
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        onClose()
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      // Prevent body scroll when modal is open
      document.body.style.overflow = 'hidden'
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'unset'
    }
  }, [isOpen, onClose])

  // Load file content
  useEffect(() => {
    if (!isOpen || !file || !notebookId) {
      setFileContent(null)
      return
    }

    const loadFileContent = async () => {
      setLoading(true)
      try {
        // Call the real API to get file content
        const response = await filesAPI.getContent(notebookId, file.path)
        
        // Handle base64 encoded content for images
        if (response.content_type?.startsWith('image/')) {
          setFileContent({ 
            content: response.content, 
            contentType: response.content_type,
            isBase64: true 
          })
        } else {
          setFileContent({ 
            content: response.content,
            contentType: response.content_type 
          })
        }
      } catch (error) {
        console.error('Failed to load file content:', error)
        setFileContent({ 
          content: '', 
          error: `Failed to load file: ${error instanceof Error ? error.message : 'Unknown error'}` 
        })
      } finally {
        setLoading(false)
      }
    }

    loadFileContent()
  }, [isOpen, file, notebookId])

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  // Parse CSV content
  const parseCSV = (content: string): string[][] => {
    const lines = content.trim().split('\n')
    return lines.map(line => {
      // Simple CSV parsing - in production, use a proper CSV parser
      const cells = []
      let current = ''
      let inQuotes = false
      
      for (let i = 0; i < line.length; i++) {
        const char = line[i]
        if (char === '"') {
          inQuotes = !inQuotes
        } else if (char === ',' && !inQuotes) {
          cells.push(current.trim())
          current = ''
        } else {
          current += char
        }
      }
      cells.push(current.trim())
      return cells
    })
  }

  // Parse TSV content
  const parseTSV = (content: string): string[][] => {
    const lines = content.trim().split('\n')
    return lines.map(line => line.split('\t'))
  }


  // Simple JSON syntax highlighter
  const highlightJson = (jsonString: string): string => {
    return jsonString
      .replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g, (match) => {
        let cls = 'text-gray-800'
        if (/^"/.test(match)) {
          if (/:$/.test(match)) {
            cls = 'text-blue-600 font-medium' // Keys
          } else {
            cls = 'text-green-600' // String values
          }
        } else if (/true|false/.test(match)) {
          cls = 'text-purple-600 font-medium' // Booleans
        } else if (/null/.test(match)) {
          cls = 'text-red-500 font-medium' // Null
        } else if (/^-?\d/.test(match)) {
          cls = 'text-orange-600' // Numbers
        }
        return `<span class="${cls}">${match}</span>`
      })
      .replace(/([{}[\],])/g, '<span class="text-gray-500 font-medium">$1</span>') // Brackets and commas
  }

  // Render file content based on type
  const renderContent = () => {
    if (loading) {
      return (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full"></div>
          <span className="ml-3 text-gray-600">Loading file...</span>
        </div>
      )
    }

    if (!fileContent) return null

    if (fileContent.error) {
      return (
        <div className="text-center py-8">
          <div className="text-red-600 mb-2">Error loading file</div>
          <div className="text-sm text-gray-500">{fileContent.error}</div>
        </div>
      )
    }

    const fileType = getFileTypeFromName(file?.name || '')
    const content = fileContent.content

    // H5 files - use specialized viewer
    if (file && (file.is_h5_file || ['h5', 'hdf5', 'h5ad'].includes(fileType))) {
      // For H5 files, the content is the processed metadata as JSON
      let h5Data = file.preview
      if (content && fileContent.contentType === 'application/json') {
        try {
          h5Data = JSON.parse(content)
        } catch (e) {
          console.warn('Failed to parse H5 metadata from content:', e)
        }
      }
      
      return (
        <div className="h-96">
          <H5FileViewer fileInfo={{
            ...file,
            preview: h5Data
          }} />
        </div>
      )
    }

    // Image files
    if (fileType === 'image') {
      if (fileContent.isBase64) {
        const imageSrc = `data:${fileContent.contentType};base64,${content}`
        return (
          <div className="text-center py-4">
            <img 
              src={imageSrc} 
              alt={file?.name || 'Image'} 
              className="max-w-full max-h-96 mx-auto rounded-lg shadow-sm"
              style={{ objectFit: 'contain' }}
            />
            <p className="text-sm text-gray-500 mt-2">{file?.name}</p>
          </div>
        )
      } else {
        return (
          <div className="text-center py-8">
            <ImageIcon className="h-16 w-16 mx-auto text-gray-400 mb-4" />
            <p className="text-gray-600">Unable to display image</p>
            <p className="text-sm text-gray-500 mt-2">{file?.name}</p>
          </div>
        )
      }
    }

    // CSV files
    if (fileType === 'csv' && viewMode === 'formatted') {
      const rows = parseCSV(content)
      const headers = rows[0] || []
      const dataRows = rows.slice(1)

      return (
        <div className="overflow-auto max-h-96 border border-gray-200 rounded-md">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  {headers.map((header, index) => (
                    <th
                      key={index}
                      className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap"
                    >
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {dataRows.map((row, rowIndex) => (
                  <tr key={rowIndex} className="hover:bg-gray-50">
                    {row.map((cell, cellIndex) => (
                      <td
                        key={cellIndex}
                        className="px-4 py-2 whitespace-nowrap text-sm text-gray-900"
                      >
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )
    }

    // TSV files
    if (fileType === 'tsv' && viewMode === 'formatted') {
      const rows = parseTSV(content)
      const headers = rows[0] || []
      const dataRows = rows.slice(1)

      return (
        <div className="overflow-auto max-h-96 border border-gray-200 rounded-md">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  {headers.map((header, index) => (
                    <th
                      key={index}
                      className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap"
                    >
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {dataRows.map((row, rowIndex) => (
                  <tr key={rowIndex} className="hover:bg-gray-50">
                    {row.map((cell, cellIndex) => (
                      <td
                        key={cellIndex}
                        className="px-4 py-2 whitespace-nowrap text-sm text-gray-900"
                      >
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )
    }

    // Excel files - use dedicated viewer
    if (fileType === 'excel') {
      try {
        const excelData = JSON.parse(content)
        return (
          <div className="h-[450px]">
            <ExcelFileViewer data={excelData} fileName={file?.name || 'Excel File'} />
          </div>
        )
      } catch (e) {
        // JSON parsing failed - show error with details
        console.error('Excel JSON parse error:', e)
        return (
          <div className="p-4">
            <div className="bg-red-100 border border-red-300 rounded-lg p-4 mb-4">
              <h3 className="text-red-800 font-medium mb-2">Failed to parse Excel data</h3>
              <p className="text-red-600 text-sm">{String(e)}</p>
            </div>
            <pre className="bg-gray-50 p-4 rounded-md overflow-auto max-h-80 text-xs whitespace-pre-wrap font-mono">
              {content}
            </pre>
          </div>
        )
      }
    }

    // Markdown files
    if (fileType === 'markdown' && viewMode === 'formatted') {
      return (
        <div className="overflow-auto max-h-96 p-4">
          <MarkdownRenderer content={content} variant="default" />
        </div>
      )
    }

    // JSON files
    if (fileType === 'json' && viewMode === 'formatted') {
      try {
        const parsed = JSON.parse(content)
        const prettyJson = JSON.stringify(parsed, null, 2)
        const highlightedJson = highlightJson(prettyJson)
        
        // Count properties recursively
        const countProperties = (obj: any): number => {
          if (Array.isArray(obj)) return obj.length
          if (typeof obj === 'object' && obj !== null) return Object.keys(obj).length
          return 0
        }
        
        const topLevelCount = countProperties(parsed)
        
        return (
          <div className="overflow-auto max-h-96 border border-gray-200 rounded-md">
            <div className="bg-gray-50 px-4 py-2 border-b border-gray-200 flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">JSON Structure</span>
              <div className="flex items-center space-x-3 text-xs text-gray-500">
                <span>
                  {topLevelCount} {Array.isArray(parsed) ? 'items' : topLevelCount === 1 ? 'property' : 'properties'}
                </span>
                <span>•</span>
                <span>{prettyJson.split('\n').length} lines</span>
              </div>
            </div>
            <pre className="bg-white p-4 overflow-x-auto text-sm font-mono leading-relaxed json-content">
              <code 
                className="language-json"
                dangerouslySetInnerHTML={{ __html: highlightedJson }}
              />
            </pre>
          </div>
        )
      } catch (error) {
        return (
          <div className="overflow-auto max-h-96 border border-red-200 rounded-md">
            <div className="bg-red-50 px-4 py-2 border-b border-red-200 flex items-center">
              <span className="text-sm font-medium text-red-700">Invalid JSON</span>
            </div>
            <div className="bg-white p-4">
              <p className="text-red-600 text-sm mb-2">Failed to parse JSON:</p>
              <p className="text-red-500 text-xs font-mono">{error instanceof Error ? error.message : 'Unknown error'}</p>
              <div className="mt-3">
                <p className="text-gray-600 text-sm mb-2">Raw content:</p>
                <pre className="bg-gray-50 p-3 rounded text-xs overflow-x-auto">{content}</pre>
              </div>
            </div>
          </div>
        )
      }
    }

    // YAML files - syntax highlighting
    if (fileType === 'yaml' && viewMode === 'formatted') {
      // Simple YAML syntax highlighter
      const highlightYaml = (yamlString: string): string => {
        return yamlString
          // Comments
          .replace(/(#.*)$/gm, '<span class="text-gray-500 italic">$1</span>')
          // Keys (before colon)
          .replace(/^(\s*)([^:\n#]+)(:)/gm, '$1<span class="text-blue-600 font-medium">$2</span><span class="text-gray-500">$3</span>')
          // Strings in quotes
          .replace(/("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')/g, '<span class="text-green-600">$1</span>')
          // Booleans
          .replace(/\b(true|false|yes|no|on|off)\b/gi, '<span class="text-purple-600 font-medium">$1</span>')
          // Null
          .replace(/\b(null|~)\b/gi, '<span class="text-red-500 font-medium">$1</span>')
          // Numbers
          .replace(/\b(-?\d+\.?\d*(?:e[+-]?\d+)?)\b/gi, '<span class="text-orange-600">$1</span>')
          // YAML document markers
          .replace(/^(---|\.\.\.)/gm, '<span class="text-gray-400 font-bold">$1</span>')
      }

      const highlightedYaml = highlightYaml(content)
      const lineCount = content.split('\n').length

      return (
        <div className="overflow-auto max-h-96 border border-gray-200 rounded-md">
          <div className="bg-yellow-50 px-4 py-2 border-b border-yellow-200 flex items-center justify-between">
            <span className="text-sm font-medium text-yellow-800">YAML Configuration</span>
            <div className="flex items-center space-x-3 text-xs text-yellow-700">
              <span>{lineCount} lines</span>
            </div>
          </div>
          <pre className="bg-white p-4 overflow-x-auto text-sm font-mono leading-relaxed yaml-content">
            <code 
              className="language-yaml"
              dangerouslySetInnerHTML={{ __html: highlightedYaml }}
            />
          </pre>
        </div>
      )
    }

    // Raw text or fallback
    return (
      <pre className="bg-gray-50 p-4 rounded-md overflow-auto max-h-96 text-sm whitespace-pre-wrap font-mono">
        {content}
      </pre>
    )
  }

  // Get file type icon
  const getFileIcon = () => {
    const fileType = getFileTypeFromName(file?.name || '')
    switch (fileType) {
      case 'csv':
      case 'tsv':
        return <Table className="h-5 w-5 text-green-600" />
      case 'excel':
        return <FileSpreadsheet className="h-5 w-5 text-green-600" />
      case 'image':
        return <ImageIcon className="h-5 w-5 text-purple-600" />
      case 'markdown':
        return <FileText className="h-5 w-5 text-blue-600" />
      case 'json':
        return <Code className="h-5 w-5 text-orange-600" />
      case 'yaml':
        return <Code className="h-5 w-5 text-yellow-600" />
      case 'h5':
        return <Code className="h-5 w-5 text-indigo-600" />
      default:
        return <FileText className="h-5 w-5 text-gray-600" />
    }
  }

  if (!isOpen || !file) return null

  const fileType = getFileTypeFromName(file.name)
  const supportsFormatting = ['csv', 'tsv', 'markdown', 'json', 'yaml', 'excel'].includes(fileType)

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div 
          className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          onClick={onClose}
        />

        {/* Modal panel */}
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
          {/* Header */}
          <div className="bg-white px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                {getFileIcon()}
                <div>
                  <h3 className="text-lg font-medium text-gray-900">{file.name}</h3>
                  <p className="text-sm text-gray-500">
                    {formatFileSize(file.size)} • Modified {new Date(file.lastModified).toLocaleDateString()}
                  </p>
                </div>
              </div>
              
              <div className="flex items-center space-x-2">
                {/* View mode toggle */}
                {supportsFormatting && (
                  <div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1">
                    <button
                      onClick={() => setViewMode('formatted')}
                      className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                        viewMode === 'formatted'
                          ? 'bg-white text-gray-900 shadow-sm'
                          : 'text-gray-600 hover:text-gray-900'
                      }`}
                    >
                      <Eye className="h-4 w-4 mr-1 inline" />
                      Formatted
                    </button>
                    <button
                      onClick={() => setViewMode('raw')}
                      className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                        viewMode === 'raw'
                          ? 'bg-white text-gray-900 shadow-sm'
                          : 'text-gray-600 hover:text-gray-900'
                      }`}
                    >
                      <Code className="h-4 w-4 mr-1 inline" />
                      Raw
                    </button>
                  </div>
                )}

                {/* Close button */}
                <button
                  onClick={onClose}
                  className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="bg-white px-6 py-4 max-h-[70vh] overflow-hidden">
            {renderContent()}
          </div>

          {/* Footer */}
          <div className="bg-gray-50 px-6 py-3 border-t border-gray-200">
            <div className="flex items-center justify-between text-sm text-gray-500">
              <span>File type: {fileType.toUpperCase()}</span>
              <span>Path: {file.path}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default FileViewerModal
