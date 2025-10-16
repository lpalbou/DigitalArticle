import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Plus, AlertCircle, Edit2, Check, X } from 'lucide-react'
import Header from './Header'
import FileContextPanel from './FileContextPanel'
import NotebookCell from './NotebookCell'
import { notebookAPI, cellAPI, handleAPIError, downloadFile } from '../services/api'
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
  const [executingCells, setExecutingCells] = useState<Set<string>>(new Set())
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [, setContextFiles] = useState<FileInfo[]>([])
  const [fileRefreshTrigger, setFileRefreshTrigger] = useState(0)
  const [editingTitle, setEditingTitle] = useState(false)
  const [editingDescription, setEditingDescription] = useState(false)
  const [tempTitle, setTempTitle] = useState('')
  const [tempDescription, setTempDescription] = useState('')

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
      const request: NotebookCreateRequest = {
        title: 'Untitled Digital Article',
        description: 'A new digital article',
        author: 'User'
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
      console.log('Notebook saved successfully')
    } catch (err) {
      const apiError = handleAPIError(err)
      console.error('Failed to save notebook:', apiError.message)
    }
  }, [notebook])

  const exportNotebook = useCallback(async () => {
    if (!notebook) return

    try {
      const jsonContent = await notebookAPI.export(notebook.id, 'json')
      downloadFile(jsonContent, `${notebook.title}.json`, 'application/json')
    } catch (err) {
      const apiError = handleAPIError(err)
      setError(`Export failed: ${apiError.message}`)
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
      />

      {/* Content with top padding to account for fixed header */}
      <div className="pt-16">
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

      {/* Digital Article Metadata */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-6 p-6">
        {/* Title Section */}
        <div className="mb-2 group">
          {editingTitle ? (
            <div className="flex items-center space-x-2">
              <input
                type="text"
                value={tempTitle}
                onChange={(e) => setTempTitle(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') saveTitleEdit()
                  if (e.key === 'Escape') cancelTitleEdit()
                }}
                className="text-2xl font-bold bg-transparent border-b-2 border-blue-500 focus:outline-none flex-1"
                autoFocus
                placeholder="Enter title..."
              />
              <button
                onClick={saveTitleEdit}
                className="text-green-600 hover:text-green-700 p-1"
                title="Save title"
              >
                <Check className="h-4 w-4" />
              </button>
              <button
                onClick={cancelTitleEdit}
                className="text-red-600 hover:text-red-700 p-1"
                title="Cancel editing"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <div className="flex items-center space-x-2">
              <h1 className="text-2xl font-bold flex-1">{notebook.title}</h1>
              <button
                onClick={handleTitleEdit}
                className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-blue-600 p-1 transition-all"
                title="Edit title"
              >
                <Edit2 className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>

        {/* Description Section */}
        <div className="mb-4 group">
          {editingDescription ? (
            <div className="flex items-start space-x-2">
              <textarea
                value={tempDescription}
                onChange={(e) => setTempDescription(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && e.ctrlKey) saveDescriptionEdit()
                  if (e.key === 'Escape') cancelDescriptionEdit()
                }}
                className="text-gray-600 bg-transparent border-b-2 border-blue-500 focus:outline-none flex-1 resize-none"
                autoFocus
                placeholder="Enter description..."
                rows={2}
              />
              <div className="flex flex-col space-y-1">
                <button
                  onClick={saveDescriptionEdit}
                  className="text-green-600 hover:text-green-700 p-1"
                  title="Save description (Ctrl+Enter)"
                >
                  <Check className="h-4 w-4" />
                </button>
                <button
                  onClick={cancelDescriptionEdit}
                  className="text-red-600 hover:text-red-700 p-1"
                  title="Cancel editing"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-start space-x-2">
              <p className="text-gray-600 flex-1">{notebook.description}</p>
              <button
                onClick={handleDescriptionEdit}
                className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-blue-600 p-1 transition-all"
                title="Edit description"
              >
                <Edit2 className="h-4 w-4" />
              </button>
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
    </>
  )
}

export default NotebookContainer
