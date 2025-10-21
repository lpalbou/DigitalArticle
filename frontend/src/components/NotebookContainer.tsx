import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Plus, AlertCircle, Edit2, Check, X } from 'lucide-react'
import Header from './Header'
import FileContextPanel from './FileContextPanel'
import NotebookCell from './NotebookCell'
import PDFGenerationModal from './PDFGenerationModal'
import LLMStatusFooter from './LLMStatusFooter'
import LLMSettingsModal from './LLMSettingsModal'
import Toast, { ToastType } from './Toast'
import { notebookAPI, cellAPI, llmAPI, handleAPIError, downloadFile, getCurrentUser } from '../services/api'
import { 
  Notebook, 
  Cell, 
  CellType, 
  NotebookCreateRequest, 
  CellCreateRequest,
  CellUpdateRequest,
  ExecutionStatus 
} from '../types'

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

const NotebookContainer: React.FC = () => {
  const { notebookId } = useParams<{ notebookId: string }>()
  const navigate = useNavigate()

  // State
  const [notebook, setNotebook] = useState<Notebook | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [toast, setToast] = useState<{ message: string; type: ToastType } | null>(null)
  const [executingCells, setExecutingCells] = useState<Set<string>>(new Set())
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [, setContextFiles] = useState<FileInfo[]>([])
  const [fileRefreshTrigger, setFileRefreshTrigger] = useState(0)
  const [editingTitle, setEditingTitle] = useState(false)
  const [editingDescription, setEditingDescription] = useState(false)
  const [tempTitle, setTempTitle] = useState('')
  const [tempDescription, setTempDescription] = useState('')
  
  // PDF generation state
  const [isGeneratingPDF, setIsGeneratingPDF] = useState(false)
  const [pdfGenerationStage, setPdfGenerationStage] = useState<'analyzing' | 'generating_content' | 'creating_pdf' | 'complete'>('analyzing')

  // LLM settings modal state
  const [showSettingsModal, setShowSettingsModal] = useState(false)

  // Load notebook on component mount or ID change
  useEffect(() => {
    if (notebookId) {
      loadNotebook(notebookId)
    } else {
      // Only create a new notebook if we don't have one and aren't already loading
      if (!notebook && !loading) {
        createNewNotebook()
      }
    }
  }, [notebookId]) // Only depend on notebookId to prevent infinite loops

  // Auto-save functionality
  useEffect(() => {
    if (hasUnsavedChanges && notebook) {
      const timeoutId = setTimeout(() => {
        saveNotebook()
      }, 2000) // Auto-save after 2 seconds of inactivity

      return () => clearTimeout(timeoutId)
    }
  }, [notebook, hasUnsavedChanges])

  const loadNotebook = useCallback(async (id: string) => {
    setLoading(true)
    setError(null)
    
    try {
      const loadedNotebook = await notebookAPI.get(id)
      setNotebook(loadedNotebook)
      setHasUnsavedChanges(false)
    } catch (err) {
      const apiError = handleAPIError(err)
      setError(apiError.message)
    } finally {
      setLoading(false)
    }
  }, [])

  const createNewNotebook = useCallback(async () => {
    // Prevent multiple simultaneous calls
    if (loading) return
    
    setLoading(true)
    setError(null)

    try {
      // Get the current user
      const currentUser = await getCurrentUser()

      // Try to get global LLM config, use defaults if it fails
      let llmProvider = 'lmstudio'
      let llmModel = 'qwen/qwen3-next-80b'

      try {
        const llmConfig = await llmAPI.getConfig()
        llmProvider = llmConfig.provider
        llmModel = llmConfig.model
      } catch (configError) {
        console.warn('Failed to fetch LLM config, using defaults:', configError)
        // Continue with defaults - don't fail notebook creation
      }

      const request: NotebookCreateRequest = {
        title: 'Untitled Digital Article',
        description: 'A new digital article',
        author: currentUser,
        llm_provider: llmProvider,
        llm_model: llmModel
      }

      const newNotebook = await notebookAPI.create(request)
      setNotebook(newNotebook)
      setHasUnsavedChanges(false)

      // Navigate to the new notebook URL
      navigate(`/notebook/${newNotebook.id}`, { replace: true })
    } catch (err) {
      const apiError = handleAPIError(err)
      setError(apiError.message)
    } finally {
      setLoading(false)
    }
  }, [loading, navigate])

  const saveNotebook = useCallback(async () => {
    if (!notebook) return

    try {
      // Update notebook metadata if needed
      await notebookAPI.update(notebook.id, {
        title: notebook.title,
        description: notebook.description,
        author: notebook.author
      })
      
      setHasUnsavedChanges(false)
      console.log('Digital Article saved successfully')

      // Show success toast
      setError(null)
      setToast({
        message: `Digital Article "${notebook.title}" has been saved`,
        type: 'success'
      })
    } catch (err) {
      const apiError = handleAPIError(err)
      console.error('Failed to save notebook:', apiError.message)
      setError(`Save failed: ${apiError.message}`)
    }
  }, [notebook])

  const exportNotebook = useCallback(async () => {
    if (!notebook) return

    try {
      const jsonContent = await notebookAPI.export(notebook.id, 'json')
      downloadFile(jsonContent, `${notebook.title}.json`, 'application/json')

      setError(null)
      setToast({
        message: `Digital Article "${notebook.title}" exported as JSON successfully`,
        type: 'success'
      })
    } catch (err) {
      const apiError = handleAPIError(err)
      setError(`Export failed: ${apiError.message}`)
    }
  }, [notebook])

  const exportNotebookPDF = useCallback(async (includeCode: boolean) => {
    if (!notebook) return

    try {
      setIsGeneratingPDF(true)
      setError(null)
      
      // Stage 1: Analyzing
      setPdfGenerationStage('analyzing')
      await new Promise(resolve => setTimeout(resolve, 1000)) // Simulate analysis time
      
      // Stage 2: Generating content
      setPdfGenerationStage('generating_content')
      await new Promise(resolve => setTimeout(resolve, 1500)) // Simulate LLM processing
      
      // Stage 3: Creating PDF
      setPdfGenerationStage('creating_pdf')
      const pdfBlob = await notebookAPI.exportPDF(notebook.id, includeCode)
      
      // Stage 4: Complete
      setPdfGenerationStage('complete')
      
      // Create download link
      const url = window.URL.createObjectURL(pdfBlob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${notebook.title.replace(/[^a-z0-9]/gi, '_')}_scientific.pdf`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      setToast({
        message: `Scientific PDF generated successfully${includeCode ? ' (with code)' : ''}`,
        type: 'success'
      })
      setTimeout(() => {
        setIsGeneratingPDF(false)
      }, 2000)

    } catch (err) {
      const apiError = handleAPIError(err)
      setError(`PDF generation failed: ${apiError.message}`)
      setIsGeneratingPDF(false)
    }
  }, [notebook])

  const addCell = useCallback(async (cellType: CellType = CellType.PROMPT, afterCellId?: string) => {
    if (!notebook) return

    try {
      const request: CellCreateRequest = {
        cell_type: cellType,
        content: '',
        notebook_id: notebook.id
      }

      const newCell = await cellAPI.create(request)
      
      setNotebook(prev => {
        if (!prev) return prev

        const newCells = [...prev.cells]
        
        if (afterCellId) {
          // Insert after specific cell
          const afterIndex = newCells.findIndex(cell => cell.id === afterCellId)
          if (afterIndex !== -1) {
            newCells.splice(afterIndex + 1, 0, newCell)
          } else {
            newCells.push(newCell)
          }
        } else {
          // Add to end
          newCells.push(newCell)
        }

        return { ...prev, cells: newCells }
      })

      setHasUnsavedChanges(true)
    } catch (err) {
      const apiError = handleAPIError(err)
      setError(`Failed to add cell: ${apiError.message}`)
    }
  }, [notebook])

  const updateCell = useCallback(async (cellId: string, updates: Partial<Cell>) => {
    if (!notebook) return

    // IMMEDIATE UI update for better UX
    setNotebook(prev => {
      if (!prev) return prev
      const newCells = prev.cells.map(cell => 
        cell.id === cellId ? { ...cell, ...updates } : cell
      )
      return { ...prev, cells: newCells }
    })

    // Then sync with backend (don't block UI)
    try {
      const request: CellUpdateRequest = {
        prompt: updates.prompt,
        code: updates.code,
        markdown: updates.markdown,
        show_code: updates.show_code,
        tags: updates.tags,
        metadata: updates.metadata,
        cell_type: updates.cell_type
      }

      await cellAPI.update(notebook.id, cellId, request)
      setHasUnsavedChanges(true)
    } catch (err) {
      console.error('Backend sync failed:', err)
      // Keep UI change for better UX, just log the error
    }
  }, [notebook])

  const deleteCell = useCallback(async (cellId: string) => {
    if (!notebook) return

    try {
      await cellAPI.delete(notebook.id, cellId)
      
      setNotebook(prev => {
        if (!prev) return prev

        const newCells = prev.cells.filter(cell => cell.id !== cellId)
        return { ...prev, cells: newCells }
      })

      setHasUnsavedChanges(true)
    } catch (err) {
      const apiError = handleAPIError(err)
      setError(`Failed to delete cell: ${apiError.message}`)
    }
  }, [notebook])


  const executeCell = useCallback(async (cellId: string, forceRegenerate: boolean = false) => {
    if (!notebook) return

    // Mark cell as executing
    setExecutingCells(prev => new Set(prev).add(cellId))
    
    // Update cell state to show it's executing
    setNotebook(prev => {
      if (!prev) return prev
      
      const newCells = prev.cells.map(cell => 
        cell.id === cellId ? { ...cell, is_executing: true } : cell
      )
      
      return { ...prev, cells: newCells }
    })

    try {
      const response = await cellAPI.execute({
        cell_id: cellId,
        force_regenerate: forceRegenerate
      })

      // Check if we should auto-switch to methodology tab
      const shouldSwitchToMethodology = response.cell.scientific_explanation && 
                                       response.cell.scientific_explanation.trim()

      // Log the response to debug methodology
      console.log('🔬 EXECUTION RESPONSE:', response)
      console.log('🔬 CELL DATA:', response.cell)
      console.log('🔬 SCIENTIFIC EXPLANATION:', response.cell.scientific_explanation)
      console.log('🔬 SHOULD SWITCH TO METHODOLOGY:', shouldSwitchToMethodology)

      // Update cell with both the updated cell data AND execution result
      setNotebook(prev => {
        if (!prev) return prev

        const newCells = prev.cells.map(cell => 
          cell.id === cellId 
            ? { 
                ...response.cell, // Use the updated cell from the backend (includes generated code!)
                is_executing: false,
                last_result: response.result,
                execution_count: cell.execution_count + 1,
                // Auto-switch to Methodology tab if scientific explanation was generated
                cell_type: shouldSwitchToMethodology ? CellType.METHODOLOGY : response.cell.cell_type
              }
            : cell
        )

        return { ...prev, cells: newCells }
      })

      // Refresh files after successful execution (files might have been created/modified)
      setFileRefreshTrigger(prev => prev + 1)

      if (shouldSwitchToMethodology) {
        console.log('🔬 Auto-switched to Methodology tab')
      }

    } catch (err) {
      const apiError = handleAPIError(err)
      
      // Update cell with error state
      setNotebook(prev => {
        if (!prev) return prev

        const newCells = prev.cells.map(cell => 
          cell.id === cellId 
            ? { 
                ...cell, 
                is_executing: false,
                last_result: {
                  status: ExecutionStatus.ERROR,
                  stdout: '',
                  stderr: '',
                  execution_time: 0,
                  timestamp: new Date().toISOString(),
                  plots: [],
                  tables: [],
                  images: [],
                  interactive_plots: [],
                  error_type: 'APIError',
                  error_message: apiError.message,
                  traceback: apiError.message
                }
              }
            : cell
        )

        return { ...prev, cells: newCells }
      })
    } finally {
      // Remove from executing cells
      setExecutingCells(prev => {
        const newSet = new Set(prev)
        newSet.delete(cellId)
        return newSet
      })
    }
  }, [notebook])

  const addCellBelow = useCallback((cellId: string, cellType: CellType) => {
    addCell(cellType, cellId)
  }, [addCell])

  const handleTitleEdit = useCallback(() => {
    if (!notebook) return
    setTempTitle(notebook.title)
    setEditingTitle(true)
  }, [notebook])

  const handleDescriptionEdit = useCallback(() => {
    if (!notebook) return
    setTempDescription(notebook.description)
    setEditingDescription(true)
  }, [notebook])

  const saveTitleEdit = useCallback(async () => {
    if (!notebook || !tempTitle.trim()) return
    
    setNotebook(prev => prev ? { ...prev, title: tempTitle.trim() } : prev)
    setEditingTitle(false)
    setHasUnsavedChanges(true)
  }, [notebook, tempTitle])

  const saveDescriptionEdit = useCallback(async () => {
    if (!notebook || !tempDescription.trim()) return
    
    setNotebook(prev => prev ? { ...prev, description: tempDescription.trim() } : prev)
    setEditingDescription(false)
    setHasUnsavedChanges(true)
  }, [notebook, tempDescription])

  const cancelTitleEdit = useCallback(() => {
    setEditingTitle(false)
    setTempTitle('')
  }, [])

  const cancelDescriptionEdit = useCallback(() => {
    setEditingDescription(false)
    setTempDescription('')
  }, [])

  const selectNotebook = useCallback((notebookId: string) => {
    navigate(`/notebook/${notebookId}`)
  }, [navigate])

  const deleteNotebook = useCallback(async (notebookId: string) => {
    try {
      await notebookAPI.delete(notebookId)
      // If we're deleting the current notebook, navigate to home
      if (notebookId === notebook?.id) {
        navigate('/')
      }
    } catch (err) {
      const apiError = handleAPIError(err)
      setError(`Failed to delete notebook: ${apiError.message}`)
    }
  }, [notebook?.id, navigate])

  // Memoized values
  const hasCells = useMemo(() => notebook?.cells && notebook.cells.length > 0, [notebook])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="animate-spin h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full" />
        <span className="ml-3 text-gray-600">Loading notebook...</span>
      </div>
    )
  }

  if (error && !notebook) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="error-message">
          <div className="flex items-center space-x-2 mb-2">
            <AlertCircle className="h-5 w-5" />
            <span className="font-medium">Error Loading Digital Article</span>
          </div>
          <p>{error}</p>
          <div className="mt-4">
            <button
              onClick={() => navigate('/')}
              className="btn btn-primary"
            >
              Go Back
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (!notebook) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <span className="text-gray-600">No notebook found</span>
      </div>
    )
  }

  return (
    <>
      {/* Header */}
      <Header
        onNewNotebook={createNewNotebook}
        onSaveNotebook={saveNotebook}
        onExportNotebook={exportNotebook}
        onExportPDF={exportNotebookPDF}
        onSelectNotebook={selectNotebook}
        onDeleteNotebook={deleteNotebook}
        isGeneratingPDF={isGeneratingPDF}
        currentNotebookId={notebook?.id}
        currentNotebookTitle={notebook?.title}
      />

      {/* PDF Generation Modal */}
      <PDFGenerationModal
        isVisible={isGeneratingPDF}
        stage={pdfGenerationStage}
      />

      {/* Content with top padding for header and bottom padding for footer */}
      <div className="pt-16 pb-16">
        {/* Files in Context Panel - constrained to same width as notebook */}
        <div className="max-w-6xl mx-auto">
          <FileContextPanel
            notebookId={notebook?.id}
            onFilesChange={setContextFiles}
            refreshTrigger={fileRefreshTrigger}
          />
        </div>

      <div className="max-w-6xl mx-auto">

      {/* Error Display */}
      {error && (
        <div className="error-message mb-4">
          <div className="flex items-center space-x-2 mb-2">
            <AlertCircle className="h-5 w-5" />
            <span className="font-medium">Error</span>
          </div>
          <p>{error}</p>
          <button
            onClick={() => setError(null)}
            className="mt-2 text-sm text-red-700 underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Toast Notification */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}

      {/* Digital Article Metadata */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-6 p-6">
        {/* Title Section */}
        <div className="mb-2">
          {editingTitle ? (
            <div className="flex items-center space-x-2 edit-mode-enter">
              <input
                type="text"
                value={tempTitle}
                onChange={(e) => setTempTitle(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') saveTitleEdit()
                  if (e.key === 'Escape') cancelTitleEdit()
                }}
                className="text-2xl font-bold bg-white border-2 border-blue-500 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-200 flex-1 shadow-sm"
                autoFocus
                placeholder="Enter title..."
              />
              <button
                onClick={saveTitleEdit}
                className="bg-green-600 hover:bg-green-700 text-white p-2 rounded-md shadow-sm edit-action-button"
                title="Save title (Enter)"
              >
                <Check className="h-4 w-4" />
              </button>
              <button
                onClick={cancelTitleEdit}
                className="bg-gray-500 hover:bg-gray-600 text-white p-2 rounded-md shadow-sm edit-action-button"
                title="Cancel editing (Escape)"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <div 
              className="group cursor-pointer rounded-lg hover:bg-gray-50 transition-all duration-300 p-3 -m-3"
              onClick={handleTitleEdit}
              title="Click to edit title"
            >
              <div className="flex items-center space-x-2">
                <h1 className="text-2xl font-bold flex-1 text-gray-900 group-hover:text-gray-700 transition-colors editable-field">
                  {notebook.title}
                </h1>
                <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-70 transition-all duration-300">
                  <Edit2 className="h-4 w-4 text-gray-500" />
                  <span className="text-xs text-gray-500 font-medium">Click to edit</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Description Section */}
        <div className="mb-4">
          {editingDescription ? (
            <div className="flex items-start space-x-2 edit-mode-enter">
              <textarea
                value={tempDescription}
                onChange={(e) => setTempDescription(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && e.ctrlKey) saveDescriptionEdit()
                  if (e.key === 'Escape') cancelDescriptionEdit()
                }}
                className="text-gray-700 bg-white border-2 border-blue-500 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-200 flex-1 resize-none shadow-sm"
                autoFocus
                placeholder="Enter description..."
                rows={3}
              />
              <div className="flex flex-col space-y-1">
                <button
                  onClick={saveDescriptionEdit}
                  className="bg-green-600 hover:bg-green-700 text-white p-2 rounded-md shadow-sm edit-action-button"
                  title="Save description (Ctrl+Enter)"
                >
                  <Check className="h-4 w-4" />
                </button>
                <button
                  onClick={cancelDescriptionEdit}
                  className="bg-gray-500 hover:bg-gray-600 text-white p-2 rounded-md shadow-sm edit-action-button"
                  title="Cancel editing (Escape)"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
          ) : (
            <div 
              className="group cursor-pointer rounded-lg hover:bg-gray-50 transition-all duration-300 p-3 -m-3"
              onClick={handleDescriptionEdit}
              title="Click to edit description"
            >
              <div className="flex items-start space-x-2">
                <p className="text-gray-600 flex-1 group-hover:text-gray-500 transition-colors leading-relaxed editable-field">
                  {notebook.description}
                </p>
                <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-70 transition-all duration-300 mt-0.5">
                  <Edit2 className="h-4 w-4 text-gray-500" />
                  <span className="text-xs text-gray-500 font-medium">Click to edit</span>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between text-sm text-gray-500">
          <span>Author: {notebook.author}</span>
          <span>
            {hasUnsavedChanges && <span className="text-orange-600 mr-2">• Unsaved changes</span>}
            Last updated: {new Date(notebook.updated_at).toLocaleDateString()}
          </span>
        </div>
      </div>

      {/* Cells */}
      <div className="space-y-4">
        {hasCells ? (
          notebook.cells.map((cell) => (
            <NotebookCell
              key={cell.id}
              cell={cell}
              onUpdateCell={updateCell}
              onDeleteCell={deleteCell}
              onExecuteCell={executeCell}
              onAddCellBelow={addCellBelow}
              isExecuting={executingCells.has(cell.id)}
            />
          ))
        ) : (
          <div className="text-center py-12 bg-white rounded-lg border-2 border-dashed border-gray-300">
            <p className="text-gray-500 mb-4">This notebook has no cells yet.</p>
            <button
              onClick={() => addCell(CellType.PROMPT)}
              className="btn btn-primary"
            >
              Add First Cell
            </button>
          </div>
        )}

        {/* Add Cell Button */}
        {hasCells && (
          <div className="flex justify-center pt-4">
            <button
              onClick={() => addCell(CellType.PROMPT)}
              className="btn btn-secondary flex items-center space-x-2"
            >
              <Plus className="h-4 w-4" />
              <span>Add Cell</span>
            </button>
          </div>
        )}
      </div>
      </div>
      </div>

      {/* LLM Status Footer */}
      <LLMStatusFooter
        onSettingsClick={() => setShowSettingsModal(true)}
        notebookId={notebook?.id}
      />

      {/* LLM Settings Modal */}
      {showSettingsModal && (
        <LLMSettingsModal
          isOpen={showSettingsModal}
          onClose={() => setShowSettingsModal(false)}
        />
      )}
    </>
  )
}

export default NotebookContainer
