import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react'
import { Play, Copy, Check, Activity, Trash2 } from 'lucide-react'
import { cellAPI } from '../services/api'
import { Cell, CellStatusResponse, CellType } from '../types'
import EnhancedCodeEditor from './EnhancedCodeEditor'
import ReRunDropdown from './ReRunDropdown'
import MarkdownRenderer from './MarkdownRenderer'
import GuidedRerunModal from './GuidedRerunModal'
import DeleteCellConfirmModal from './DeleteCellConfirmModal'

interface PromptEditorProps {
  cell: Cell
  onUpdateCell: (updates: Partial<Cell>) => void
  onDeleteCell?: (cellId: string) => Promise<void>
  onExecuteCell: (
    cellId: string,
    action: 'execute' | 'regenerate',
    options?: { autofix?: boolean; clean_rerun?: boolean; rerun_comment?: string }
  ) => void
  onDirectExecuteCell?: (
    cellId: string,
    action: 'execute' | 'regenerate',
    options?: { autofix?: boolean; clean_rerun?: boolean; rerun_comment?: string }
  ) => void // Direct execution without dependency check
  onInvalidateCells?: (cellId: string) => void // New callback for cell invalidation
  onViewTraces?: (cellId: string) => void // View LLM execution traces
  isExecuting?: boolean
}

const PromptEditor: React.FC<PromptEditorProps> = ({
  cell,
  onUpdateCell,
  onDeleteCell,
  onExecuteCell,
  onDirectExecuteCell,
  onInvalidateCells,
  onViewTraces,
  isExecuting = false
}) => {
  const [isEditing, setIsEditing] = useState(false)
  const [guidedRerunOpen, setGuidedRerunOpen] = useState(false)
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [localContent, setLocalContent] = useState(
    cell.cell_type === CellType.PROMPT ? cell.prompt :
    cell.cell_type === CellType.METHODOLOGY ? (cell.scientific_explanation || '') :
    cell.cell_type === CellType.CODE ? cell.code :
    cell.markdown
  )
  const [copySuccess, setCopySuccess] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [liveStatus, setLiveStatus] = useState<CellStatusResponse | null>(null)

  // Auto-resize textarea
  const adjustTextareaHeight = useCallback(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.max(100, textarea.scrollHeight)}px`
    }
  }, [])

  useEffect(() => {
    adjustTextareaHeight()
  }, [localContent, adjustTextareaHeight])

  // Auto-enter editing mode for prompt cells only (methodology is read-only)
  useEffect(() => {
    if (cell.cell_type === CellType.PROMPT) {
      setIsEditing(true)
    } else {
      setIsEditing(false) // Code, methodology and other types don't need editing mode
    }
    
    // Update local content when cell type changes
    const newContent = 
      cell.cell_type === CellType.PROMPT ? (cell.prompt || '') : 
      cell.cell_type === CellType.METHODOLOGY ? (cell.scientific_explanation || '') :
      cell.cell_type === CellType.CODE ? (cell.code || '') :
      (cell.markdown || '')
    setLocalContent(newContent)
  }, [cell.cell_type, cell.prompt, cell.code, cell.markdown, cell.scientific_explanation])

  const handleSave = useCallback(() => {
    const updates: Partial<Cell> = {}
    
    if (cell.cell_type === CellType.PROMPT) {
      updates.prompt = localContent
    } else if (cell.cell_type === CellType.METHODOLOGY) {
      updates.markdown = localContent
    } else if (cell.cell_type === CellType.CODE) {
      updates.code = localContent
    } else {
      updates.markdown = localContent
    }
    
    onUpdateCell(updates)
    setIsEditing(false)
  }, [cell.cell_type, localContent, onUpdateCell])

  const handleCancel = useCallback(() => {
    setLocalContent(
      cell.cell_type === CellType.PROMPT ? cell.prompt : 
      cell.cell_type === CellType.METHODOLOGY ? (cell.scientific_explanation || '') :
      cell.cell_type === CellType.CODE ? cell.code :
      cell.markdown
    )
    setIsEditing(false)
  }, [cell])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey || e.shiftKey)) {
      e.preventDefault()
      if (cell.cell_type === CellType.PROMPT || cell.cell_type === CellType.CODE) {
        handleSave()
        onExecuteCell(cell.id, 'execute')
      } else {
        handleSave()
      }
    } else if (e.key === 'Escape') {
      handleCancel()
    }
  }, [cell.cell_type, cell.id, handleSave, handleCancel, onExecuteCell])


  // Determine what content to show based on cell type
  const currentContent = (() => {
    if (cell.cell_type === CellType.PROMPT) {
      return isEditing ? localContent : (cell.prompt || '')
    } else if (cell.cell_type === CellType.METHODOLOGY) {
      return isEditing ? localContent : (cell.scientific_explanation || '')
    } else if (cell.cell_type === CellType.CODE) {
      return cell.code || '' // Always show the actual generated code
    } else {
      return isEditing ? localContent : (cell.markdown || '')
    }
  })()

  // Content type name for better user feedback (stable for hooks + tooltips)
  const contentTypeName = useMemo(() => {
    switch (cell.cell_type) {
      case CellType.PROMPT:
        return 'prompt'
      case CellType.CODE:
        return 'code'
      case CellType.METHODOLOGY:
        return 'methodology'
      default:
        return 'content'
    }
  }, [cell.cell_type])

  const handleCopy = useCallback(async () => {
    if (!currentContent.trim()) {
      console.warn('No content to copy')
      return
    }

    try {
      await navigator.clipboard.writeText(currentContent)
      setCopySuccess(true)
      setTimeout(() => setCopySuccess(false), 2000) // Reset after 2 seconds
      console.log(`Copied ${contentTypeName} to clipboard (${currentContent.length} characters)`)
    } catch (err) {
      console.error('Failed to copy text: ', err)
      // Fallback for older browsers
      try {
        const textArea = document.createElement('textarea')
        textArea.value = currentContent
        document.body.appendChild(textArea)
        textArea.select()
        document.execCommand('copy')
        document.body.removeChild(textArea)
        setCopySuccess(true)
        setTimeout(() => setCopySuccess(false), 2000)
        console.log(`Copied ${contentTypeName} to clipboard using fallback (${currentContent.length} characters)`)
      } catch (fallbackErr) {
        console.error('Fallback copy failed: ', fallbackErr)
      }
    }
  }, [currentContent, contentTypeName])

  // Poll backend cell status while execution is in-flight.
  // This lets the UI reflect multi-step backend phases (generation, retries, methodology, etc.)
  // even though /cells/execute is a single long-lived request.
  useEffect(() => {
    if (!isExecuting) {
      setLiveStatus(null)
      return
    }

    let cancelled = false
    let intervalId: number | null = null

    const poll = async () => {
      try {
        const status = await cellAPI.getStatus(cell.id)
        if (cancelled) return
        setLiveStatus(status)
      } catch (e) {
        // Non-fatal: status polling should never block execution UX.
        if (cancelled) return
      }
    }

    // Poll immediately, then at a modest cadence.
    poll()
    intervalId = window.setInterval(poll, 600)

    return () => {
      cancelled = true
      if (intervalId) window.clearInterval(intervalId)
    }
  }, [cell.id, isExecuting])

  const liveMessage = liveStatus?.execution_message?.trim()
  const isLiveRetrying = Boolean(liveStatus?.is_retrying)
  const isLiveMethodology = Boolean(liveStatus?.is_writing_methodology)
  const shouldShowStatus = Boolean(isExecuting)

  const statusTone = isLiveRetrying
    ? 'yellow'
    : isLiveMethodology
      ? 'green'
      : 'blue'

  const statusTextClass =
    statusTone === 'yellow'
      ? 'text-yellow-700'
      : statusTone === 'green'
        ? 'text-green-600'
        : 'text-blue-600'

  const spinnerBorderClass =
    statusTone === 'yellow'
      ? 'border-yellow-600'
      : statusTone === 'green'
        ? 'border-green-600'
        : 'border-blue-600'

  const statusMessage = liveMessage
    ? liveMessage
    : isExecuting
      ? 'Generating and executing code…'
      : ''

  return (
    <div className="w-full">
      <GuidedRerunModal
        isOpen={guidedRerunOpen}
        isExecuting={isExecuting}
        onClose={() => setGuidedRerunOpen(false)}
        onConfirm={(comment) => {
          setGuidedRerunOpen(false)
          // Guided rerun always invalidates downstream cells; we rebuild upstream-only context on the backend.
          onExecuteCell(cell.id, 'regenerate', { clean_rerun: true, rerun_comment: comment })
        }}
      />

      <DeleteCellConfirmModal
        isOpen={deleteConfirmOpen}
        isDeleting={isDeleting}
        onClose={() => {
          if (!isDeleting) setDeleteConfirmOpen(false)
        }}
        onConfirm={async () => {
          if (!onDeleteCell) return
          try {
            setIsDeleting(true)
            await onDeleteCell(cell.id)
            setDeleteConfirmOpen(false)
          } finally {
            setIsDeleting(false)
          }
        }}
      />

      {/* Cell Type Tabs with Run Button */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex space-x-1">
          <button
            onClick={() => onUpdateCell({ cell_type: CellType.PROMPT })}
            className={`px-4 py-2 rounded-t-lg font-medium text-sm transition-colors ${
              cell.cell_type === CellType.PROMPT
                ? 'bg-blue-500 text-white shadow-md'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Prompt
          </button>
          <button
            onClick={() => onUpdateCell({ cell_type: CellType.CODE })}
            className={`px-4 py-2 rounded-t-lg font-medium text-sm transition-colors ${
              cell.cell_type === CellType.CODE
                ? 'bg-purple-500 text-white shadow-md'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Code
          </button>
          <button
            onClick={() => onUpdateCell({ cell_type: CellType.METHODOLOGY })}
            className={`px-4 py-2 rounded-t-lg font-medium text-sm transition-colors ${
              cell.cell_type === CellType.METHODOLOGY
                ? 'bg-green-500 text-white shadow-md'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Methodology
          </button>
        </div>

        {/* Controls on the right */}
        <div className="flex items-center space-x-2">
          {/* Generation Metadata - iPhone style */}
          {(cell.last_execution_timestamp || cell.last_generation_time_ms) && (
            <div className="text-xs text-gray-400 flex items-center space-x-1">
              {cell.last_execution_timestamp && (
                <span>
                  {new Date(cell.last_execution_timestamp).toLocaleTimeString([], { 
                    hour: '2-digit', 
                    minute: '2-digit' 
                  })}
                </span>
              )}
              {cell.last_execution_timestamp && cell.last_generation_time_ms && (
                <span>|</span>
              )}
              {cell.last_generation_time_ms && (
                <span>
                  {cell.last_generation_time_ms < 1000 
                    ? `${Math.round(cell.last_generation_time_ms)}ms`
                    : `${(cell.last_generation_time_ms / 1000).toFixed(1)}s`
                  }
                </span>
              )}
            </div>
          )}

          {/* View LLM Traces Button - Show if cell has been executed OR has traces */}
          {onViewTraces && (cell.execution_count > 0 || (cell.llm_traces && cell.llm_traces.length > 0)) && (
            <button
              onClick={() => onViewTraces(cell.id)}
              className="text-xs bg-blue-50 px-2 py-1 rounded text-blue-600 hover:bg-blue-100 hover:text-blue-700 transition-all duration-200 cursor-pointer hover:shadow-sm flex items-center space-x-1"
              title={cell.llm_traces && cell.llm_traces.length > 0
                ? `View ${cell.llm_traces.length} LLM trace${cell.llm_traces.length > 1 ? 's' : ''}`
                : 'View execution details'}
            >
              <Activity className="h-3 w-3" />
              <span>{cell.llm_traces?.length || 0}</span>
            </button>
          )}

          {/* Copy Button */}
          <button
            onClick={handleCopy}
            className={`p-1 text-gray-500 hover:text-gray-700 rounded copy-button ${copySuccess ? 'copy-success' : ''}`}
            title={copySuccess ? `Copied ${contentTypeName}!` : `Copy ${contentTypeName} to clipboard`}
          >
            {copySuccess ? (
              <Check className="h-4 w-4 text-green-600" />
            ) : (
              <Copy className="h-4 w-4" />
            )}
          </button>

          {/* Delete Cell Button */}
          {onDeleteCell && (
            <button
              onClick={() => setDeleteConfirmOpen(true)}
              disabled={isExecuting || isDeleting}
              className="p-1 text-gray-500 hover:text-gray-700 rounded copy-button disabled:opacity-50 disabled:cursor-not-allowed"
              title="Delete cell"
              aria-label="Delete cell"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}

          {/* Execute Button - Adaptive */}
          {(cell.cell_type === CellType.PROMPT || cell.cell_type === CellType.CODE || cell.cell_type === CellType.METHODOLOGY) && (
            <>
              {/* Show simple Run button for fresh cells */}
              {(!cell.code && !cell.scientific_explanation) ? (
                <button
                  onClick={() => onExecuteCell(cell.id, 'execute')}
                  disabled={isExecuting}
                  className="btn btn-primary flex items-center space-x-2 text-sm px-4 py-2 font-medium"
                  title="Execute Cell (Shift+Enter or Ctrl+Enter)"
                >
                  <Play className="h-4 w-4" />
                  <span>{isExecuting ? 'Running...' : 'Run'}</span>
                </button>
              ) : (
                /* Show Re-run dropdown for cells with content */
                <ReRunDropdown
                  onExecuteCode={() => {
                    console.log('🔄 ReRunDropdown onExecuteCode called for cell:', cell.id)
                    console.log('🔄 onDirectExecuteCell available:', !!onDirectExecuteCell)
                    console.log('🔄 Cell type:', cell.cell_type)
                    if (onDirectExecuteCell) {
                      console.log('🔄 Using onDirectExecuteCell')
                      onDirectExecuteCell(cell.id, 'execute')
                    } else {
                      console.log('🔄 Falling back to onExecuteCell')
                      onExecuteCell(cell.id, 'execute')
                    }
                  }}
                  onExecuteCodeWithoutAutofix={() => {
                    if (onDirectExecuteCell) {
                      onDirectExecuteCell(cell.id, 'execute', { autofix: false })
                    } else {
                      onExecuteCell(cell.id, 'execute', { autofix: false })
                    }
                  }}
                  onRegenerateAndExecute={() => {
                    console.log('🔄 ReRunDropdown onRegenerateAndExecute called for cell:', cell.id)
                    onExecuteCell(cell.id, 'regenerate')
                  }}
                  onRegenerateAndExecuteWithoutAutofix={() => {
                    onExecuteCell(cell.id, 'regenerate', { autofix: false })
                  }}
                  onGuidedRegenerateAndExecute={() => {
                    setGuidedRerunOpen(true)
                  }}
                  onCleanRegenerateAndExecute={() => {
                    onExecuteCell(cell.id, 'regenerate', { clean_rerun: true })
                  }}
                  onCleanRegenerateAndExecuteWithoutAutofix={() => {
                    onExecuteCell(cell.id, 'regenerate', { clean_rerun: true, autofix: false })
                  }}
                  isExecuting={isExecuting}
                />
              )}
            </>
          )}
        </div>
      </div>

      {/* Content Editor - DEBUG: Always show textarea for prompt cells */}
      <div className="relative">
        {cell.cell_type === CellType.PROMPT ? (
          <div className="space-y-2">
            <textarea
              ref={textareaRef}
              value={localContent}
              onChange={(e) => setLocalContent(e.target.value)}
              onKeyDown={handleKeyDown}
              onBlur={handleSave}
              placeholder="Describe what you want to analyze in natural language..."
              className="prompt-editor w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
              style={{ minHeight: '120px' }}
              autoFocus
            />
          </div>
        ) : (isEditing && cell.cell_type !== CellType.CODE) ? (
          <div className="space-y-2">
            <textarea
              ref={textareaRef}
              value={localContent}
              onChange={(e) => setLocalContent(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                cell.cell_type === CellType.METHODOLOGY
                  ? "Describe your methodology and approach..."
                  : "Enter markdown content..."
              }
              className={`prompt-editor ${cell.show_code && cell.code ? 'code-editor' : ''}`}
              style={{ minHeight: '100px' }}
              autoFocus
            />
          </div>
        ) : (
          <div
            className={`
              border border-gray-200 rounded-md
              ${cell.cell_type === CellType.CODE ? 'p-0' : 'p-4 bg-white'}
            `}
          >
            {cell.cell_type === CellType.CODE ? (
              <EnhancedCodeEditor 
                key={`code-${cell.id}-${cell.cell_type}`}
                cell={cell}
                onUpdateCell={onUpdateCell}
                onInvalidateCells={onInvalidateCells}
              />
            ) : cell.cell_type === CellType.METHODOLOGY ? (
              currentContent ? (
                <MarkdownRenderer content={currentContent} variant="default" />
              ) : (
                <span className="text-gray-400 italic">
                  Scientific explanation will appear here after code execution...
                </span>
              )
            ) : (
              <div className="whitespace-pre-wrap">
                {currentContent || (
                  <span className="text-gray-400 italic">
                    Click to add markdown...
                  </span>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Status Indicator */}
      {shouldShowStatus && (
        <div className={`mt-2 flex items-center space-x-2 text-sm ${statusTextClass}`}>
          <div className={`animate-spin h-4 w-4 border-2 ${spinnerBorderClass} border-t-transparent rounded-full`} />
          <span>{statusMessage}</span>
        </div>
      )}
    </div>
  )
}

export default PromptEditor
