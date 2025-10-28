import React, { useState, useCallback, useRef, useEffect } from 'react'
import { Play, Copy, Check } from 'lucide-react'
import { Cell, CellType, CellState } from '../types'
import CodeDisplay from './CodeDisplay'
import EnhancedCodeEditor from './EnhancedCodeEditor'
import ReRunDropdown from './ReRunDropdown'

interface PromptEditorProps {
  cell: Cell
  onUpdateCell: (updates: Partial<Cell>) => void
  onExecuteCell: (cellId: string, action: 'execute' | 'regenerate') => void
  onDirectExecuteCell?: (cellId: string, action: 'execute' | 'regenerate') => void // Direct execution without dependency check
  onInvalidateCells?: (cellId: string) => void // New callback for cell invalidation
  isExecuting?: boolean
}

const PromptEditor: React.FC<PromptEditorProps> = ({
  cell,
  onUpdateCell,
  onExecuteCell,
  onDirectExecuteCell,
  onInvalidateCells,
  isExecuting = false
}) => {
  const [isEditing, setIsEditing] = useState(false)
  const [localContent, setLocalContent] = useState(
    cell.cell_type === CellType.PROMPT ? cell.prompt : 
    cell.cell_type === CellType.METHODOLOGY ? (cell.scientific_explanation || '') :
    cell.cell_type === CellType.CODE ? cell.code :
    cell.markdown
  )
  const [copySuccess, setCopySuccess] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

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

  // Get content type name for better user feedback
  const getContentTypeName = () => {
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
  }

  const handleCopy = useCallback(async () => {
    if (!currentContent.trim()) {
      console.warn('No content to copy')
      return
    }

    try {
      await navigator.clipboard.writeText(currentContent)
      setCopySuccess(true)
      setTimeout(() => setCopySuccess(false), 2000) // Reset after 2 seconds
      console.log(`Copied ${getContentTypeName()} to clipboard (${currentContent.length} characters)`)
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
        console.log(`Copied ${getContentTypeName()} to clipboard using fallback (${currentContent.length} characters)`)
      } catch (fallbackErr) {
        console.error('Fallback copy failed: ', fallbackErr)
      }
    }
  }, [currentContent, getContentTypeName])

  return (
    <div className="w-full">
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
          
          {/* Execution Count Badge */}
          {cell.execution_count > 0 && (
            <span className="text-xs bg-gray-100 px-2 py-1 rounded text-gray-600">
              Run {cell.execution_count}
            </span>
          )}

          {/* Copy Button */}
          <button
            onClick={handleCopy}
            className={`p-1 text-gray-500 hover:text-gray-700 rounded copy-button ${copySuccess ? 'copy-success' : ''}`}
            title={copySuccess ? `Copied ${getContentTypeName()}!` : `Copy ${getContentTypeName()} to clipboard`}
          >
            {copySuccess ? (
              <Check className="h-4 w-4 text-green-600" />
            ) : (
              <Copy className="h-4 w-4" />
            )}
          </button>

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
                  onRegenerateAndExecute={() => {
                    console.log('🔄 ReRunDropdown onRegenerateAndExecute called for cell:', cell.id)
                    onExecuteCell(cell.id, 'regenerate')
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
        {(cell.cell_type === CellType.PROMPT || cell.cell_type === 'prompt') ? (
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
                cell.cell_type === CellType.PROMPT 
                  ? "Describe what you want to analyze in natural language..."
                  : cell.cell_type === CellType.METHODOLOGY
                  ? "Describe your methodology and approach..."
                  : cell.cell_type === CellType.CODE
                  ? "Enter Python code..."
                  : "Enter markdown content..."
              }
              className={`prompt-editor ${cell.show_code && cell.code ? 'code-editor' : ''}`}
              style={{ minHeight: '100px' }}
              autoFocus
            />
          </div>
        ) : (
          <div
            onClick={() => cell.cell_type === CellType.PROMPT && setIsEditing(true)}
            className={`
              ${cell.cell_type === CellType.PROMPT ? 'cursor-pointer hover:border-gray-300' : ''} border border-gray-200 rounded-md
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
            ) : (
              <div className="whitespace-pre-wrap">
                {currentContent || (
                  <span className="text-gray-400 italic">
                    {cell.cell_type === CellType.PROMPT 
                      ? "Click to add a prompt..."
                      : cell.cell_type === CellType.METHODOLOGY
                      ? "Scientific explanation will appear here after code execution..."
                      : cell.cell_type === CellType.CODE
                      ? "Click to add code..."
                      : "Click to add markdown..."}
                  </span>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Status Indicator */}
      {isExecuting && (
        <div className="mt-2 flex items-center space-x-2 text-sm text-blue-600">
          <div className="animate-spin h-4 w-4 border-2 border-blue-600 border-t-transparent rounded-full" />
          <span>Generating and executing code...</span>
        </div>
      )}
      
      {/* Methodology Writing Indicator */}
      {cell.is_writing_methodology && (
        <div className="mt-2 flex items-center space-x-2 text-sm text-green-600">
          <div className="animate-spin h-4 w-4 border-2 border-green-600 border-t-transparent rounded-full" />
          <span>Writing methodology...</span>
        </div>
      )}
    </div>
  )
}

export default PromptEditor
