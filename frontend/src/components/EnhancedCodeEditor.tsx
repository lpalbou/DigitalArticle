import React, { useState, useCallback, useRef, useEffect } from 'react'
import { 
  Edit3, 
  Wand2, 
  RotateCcw, 
  Check, 
  X, 
  Loader2,
  GitCompare
} from 'lucide-react'
import Editor from '@monaco-editor/react'
import { Cell } from '../types'

interface EnhancedCodeEditorProps {
  cell: Cell
  onUpdateCell: (updates: Partial<Cell>) => void
  onInvalidateCells?: (cellId: string) => void // New callback for cell invalidation
  readOnly?: boolean
}

interface CodeVersion {
  content: string
  timestamp: Date
  type: 'original' | 'manual' | 'ai_fix'
  description?: string
}

interface DiffLine {
  type: 'added' | 'removed' | 'modified' | 'unchanged'
  content: string
  lineNumber?: number
  oldLineNumber?: number
  newLineNumber?: number
}

const EnhancedCodeEditor: React.FC<EnhancedCodeEditorProps> = ({
  cell,
  onUpdateCell,
  onInvalidateCells,
  readOnly = false
}) => {
  const [editMode, setEditMode] = useState<'view' | 'manual' | 'ai_fix'>('view')
  const [currentCode, setCurrentCode] = useState(cell.code || '')
  const [originalCode, setOriginalCode] = useState(cell.code || '')
  const [aiFixPrompt, setAiFixPrompt] = useState('')
  const [isProcessingAIFix, setIsProcessingAIFix] = useState(false)
  const [showDiff, setShowDiff] = useState(false)
  const [selectedLines, setSelectedLines] = useState<{start: number, end: number, text: string} | null>(null)
  const [versions, setVersions] = useState<CodeVersion[]>([
    {
      content: cell.code || '',
      timestamp: new Date(),
      type: 'original',
      description: 'Original generated code'
    }
  ])
  
  const editorRef = useRef<any>(null)
  const monacoRef = useRef<any>(null)
  const aiPromptRef = useRef<HTMLTextAreaElement>(null)
  const [decorations, setDecorations] = useState<string[]>([])

  // Initialize original code when cell code changes (from AI generation)
  useEffect(() => {
    if (cell.code && cell.code !== originalCode) {
      setOriginalCode(cell.code)
      setCurrentCode(cell.code)
      setVersions([{
        content: cell.code,
        timestamp: new Date(),
        type: 'original',
        description: 'Original generated code'
      }])
    }
  }, [cell.code, originalCode])

  // Calculate diff between original and current code
  const calculateDiff = useCallback((): DiffLine[] => {
    const originalLines = originalCode.split('\n')
    const currentLines = currentCode.split('\n')
    const diff: DiffLine[] = []
    
    // Simple diff algorithm - can be enhanced with proper diff library
    const maxLines = Math.max(originalLines.length, currentLines.length)
    
    for (let i = 0; i < maxLines; i++) {
      const originalLine = originalLines[i] || ''
      const currentLine = currentLines[i] || ''
      
      if (originalLine === currentLine) {
        diff.push({
          type: 'unchanged',
          content: currentLine,
          lineNumber: i + 1,
          oldLineNumber: i + 1,
          newLineNumber: i + 1
        })
      } else if (!originalLine && currentLine) {
        diff.push({
          type: 'added',
          content: currentLine,
          lineNumber: i + 1,
          newLineNumber: i + 1
        })
      } else if (originalLine && !currentLine) {
        diff.push({
          type: 'removed',
          content: originalLine,
          lineNumber: i + 1,
          oldLineNumber: i + 1
        })
      } else {
        diff.push({
          type: 'modified',
          content: currentLine,
          lineNumber: i + 1,
          oldLineNumber: i + 1,
          newLineNumber: i + 1
        })
      }
    }
    
    return diff
  }, [originalCode, currentCode])

  const hasChanges = currentCode !== originalCode

  // Apply inline diff decorations to the editor
  const applyInlineDiff = useCallback(() => {
    if (!editorRef.current || !hasChanges) {
      // Clear decorations if no changes
      if (decorations.length > 0) {
        editorRef.current.deltaDecorations(decorations, [])
        setDecorations([])
      }
      return
    }

    const monaco = monacoRef.current
    if (!monaco) return

    const originalLines = originalCode.split('\n')
    const currentLines = currentCode.split('\n')
    const newDecorations: any[] = []

    // Simple line-by-line diff for inline highlighting
    const maxLines = Math.max(originalLines.length, currentLines.length)
    
    for (let i = 0; i < maxLines; i++) {
      const originalLine = originalLines[i] || ''
      const currentLine = currentLines[i] || ''
      const lineNumber = i + 1

      if (originalLine !== currentLine) {
        if (!originalLine && currentLine) {
          // Added line - green background
          newDecorations.push({
            range: new monaco.Range(lineNumber, 1, lineNumber, currentLine.length + 1),
            options: {
              isWholeLine: true,
              className: 'diff-line-added',
              glyphMarginClassName: 'diff-glyph-added',
              minimap: {
                color: '#28a745',
                position: 1
              }
            }
          })
        } else if (originalLine && !currentLine) {
          // This case is handled by showing the line as removed in a different way
          // Since we can't show removed lines in the current code, we'll mark the previous line
          if (i > 0) {
            newDecorations.push({
              range: new monaco.Range(lineNumber - 1, 1, lineNumber - 1, 1),
              options: {
                glyphMarginClassName: 'diff-glyph-removed',
                minimap: {
                  color: '#dc3545',
                  position: 1
                }
              }
            })
          }
        } else {
          // Modified line - blue background
          newDecorations.push({
            range: new monaco.Range(lineNumber, 1, lineNumber, currentLine.length + 1),
            options: {
              isWholeLine: true,
              className: 'diff-line-modified',
              glyphMarginClassName: 'diff-glyph-modified',
              minimap: {
                color: '#007acc',
                position: 1
              }
            }
          })
        }
      }
    }

    // Apply decorations
    const newDecorationIds = editorRef.current.deltaDecorations(decorations, newDecorations)
    setDecorations(newDecorationIds)
  }, [originalCode, currentCode, hasChanges, decorations])

  // Apply diff decorations when code changes
  useEffect(() => {
    if (editMode === 'view' && hasChanges) {
      // Small delay to ensure editor is ready
      const timer = setTimeout(applyInlineDiff, 100)
      return () => clearTimeout(timer)
    }
  }, [editMode, hasChanges, applyInlineDiff])

  // Capture current selection when user selects text
  const captureSelection = useCallback(() => {
    if (editorRef.current) {
      const selection = editorRef.current.getSelection()
      if (selection && !selection.isEmpty()) {
        const model = editorRef.current.getModel()
        const selectedText = model.getValueInRange(selection)
        const startLine = selection.startLineNumber
        const endLine = selection.endLineNumber
        
        setSelectedLines({
          start: startLine,
          end: endLine,
          text: selectedText
        })
      } else {
        setSelectedLines(null)
      }
    }
  }, [])

  const handleManualEdit = useCallback(() => {
    setEditMode('manual')
  }, [])

  const handleAIFix = useCallback(() => {
    setEditMode('ai_fix')
    
    // If there's a selection, pre-populate the prompt with context
    if (selectedLines) {
      const contextPrompt = `Focus on lines ${selectedLines.start}-${selectedLines.end}:\n\`\`\`python\n${selectedLines.text}\n\`\`\`\n\nPlease help me with: `
      setAiFixPrompt(contextPrompt)
    }
    
    // Focus on AI prompt input
    setTimeout(() => {
      aiPromptRef.current?.focus()
      // Position cursor at the end if we pre-populated
      if (selectedLines && aiPromptRef.current) {
        aiPromptRef.current.setSelectionRange(aiPromptRef.current.value.length, aiPromptRef.current.value.length)
      }
    }, 100)
  }, [selectedLines])

  const handleResetCode = useCallback(() => {
    setCurrentCode(originalCode)
    setEditMode('view')
    setShowDiff(false)
  }, [originalCode])

  const handleAcceptChanges = useCallback(() => {
    // Update the cell with new code and make it the new original
    onUpdateCell({ code: currentCode })
    setOriginalCode(currentCode)
    
    // Add to version history
    setVersions(prev => [...prev, {
      content: currentCode,
      timestamp: new Date(),
      type: editMode === 'manual' ? 'manual' : 'ai_fix',
      description: editMode === 'manual' ? 'Manual edit' : `AI fix: ${aiFixPrompt.slice(0, 50)}...`
    }])
    
    // Clear decorations since there are no more changes
    if (editorRef.current && decorations.length > 0) {
      editorRef.current.deltaDecorations(decorations, [])
      setDecorations([])
    }
    
    // Invalidate this cell and all cells below since code has changed
    if (onInvalidateCells) {
      onInvalidateCells(cell.id)
    }
    
    setEditMode('view')
    setShowDiff(false)
    setAiFixPrompt('')
    setSelectedLines(null)
  }, [currentCode, editMode, aiFixPrompt, onUpdateCell, decorations, onInvalidateCells, cell.id])

  const handleCancelEdit = useCallback(() => {
    setCurrentCode(originalCode)
    setEditMode('view')
    setShowDiff(false)
    setAiFixPrompt('')
    setSelectedLines(null)
    
    // Clear decorations
    if (editorRef.current && decorations.length > 0) {
      editorRef.current.deltaDecorations(decorations, [])
      setDecorations([])
    }
  }, [originalCode, decorations])

  const handleCodeChange = useCallback((value: string | undefined) => {
    setCurrentCode(value || '')
  }, [])

  const handleAIFixSubmit = useCallback(async () => {
    if (!aiFixPrompt.trim()) return
    
    setIsProcessingAIFix(true)
    
    try {
      // Call backend API for AI code fixing
      const response = await fetch('/api/cells/ai-fix', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          original_code: originalCode,
          current_code: currentCode,
          fix_request: aiFixPrompt,
          cell_id: cell.id,
          selected_lines: selectedLines // Include selection context
        }),
      })
      
      if (!response.ok) {
        throw new Error('Failed to get AI fix')
      }
      
      const data = await response.json()
      setCurrentCode(data.fixed_code)
      setShowDiff(true)
      
      // Auto-close the AI fix UI and switch to view mode with diff
      setEditMode('view')
      setAiFixPrompt('')
      setSelectedLines(null) // Clear selection after fix
      
    } catch (error) {
      console.error('AI fix failed:', error)
      // Handle error - could show toast notification
    } finally {
      setIsProcessingAIFix(false)
    }
  }, [aiFixPrompt, originalCode, currentCode, cell.id, selectedLines])

  const renderDiffView = () => {
    const diff = calculateDiff()
    
    return (
      <div className="border border-gray-200 rounded-md overflow-hidden">
        <div className="bg-gray-50 px-3 py-2 border-b flex items-center space-x-2">
          <GitCompare className="h-4 w-4 text-gray-600" />
          <span className="text-sm font-medium text-gray-700">Code Changes</span>
        </div>
        <div className="max-h-96 overflow-y-auto">
          {diff.map((line, index) => (
            <div
              key={index}
              className={`px-3 py-1 text-sm font-mono flex ${
                line.type === 'added' ? 'bg-green-50 border-l-4 border-green-500' :
                line.type === 'removed' ? 'bg-red-50 border-l-4 border-red-500' :
                line.type === 'modified' ? 'bg-blue-50 border-l-4 border-blue-500' :
                'bg-white'
              }`}
            >
              <span className="w-12 text-gray-400 text-right mr-3 select-none">
                {line.lineNumber}
              </span>
              <span className={`w-4 mr-2 ${
                line.type === 'added' ? 'text-green-600' :
                line.type === 'removed' ? 'text-red-600' :
                line.type === 'modified' ? 'text-blue-600' :
                'text-gray-400'
              }`}>
                {line.type === 'added' ? '+' :
                 line.type === 'removed' ? '-' :
                 line.type === 'modified' ? '~' : ' '}
              </span>
              <span className="flex-1">{line.content || ' '}</span>
            </div>
          ))}
        </div>
      </div>
    )
  }

  const renderActionButtons = () => {
    if (editMode === 'view') {
      return (
        <div className="flex items-center space-x-2">
          <button
            onClick={handleManualEdit}
            className="flex items-center space-x-1 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            <Edit3 className="h-3 w-3" />
            <span>Edit</span>
          </button>
          <button
            onClick={handleAIFix}
            className="flex items-center space-x-1 px-3 py-1.5 text-sm bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors"
          >
            <Wand2 className="h-3 w-3" />
            <span>AI Assist</span>
            {selectedLines && (
              <span className="text-xs bg-purple-500 px-1 py-0.5 rounded">
                L{selectedLines.start}-{selectedLines.end}
              </span>
            )}
          </button>
          {hasChanges && (
            <button
              onClick={() => setShowDiff(!showDiff)}
              className="flex items-center space-x-1 px-3 py-1.5 text-sm bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
            >
              <GitCompare className="h-3 w-3" />
              <span>{showDiff ? 'Hide' : 'Show'} Side Diff</span>
            </button>
          )}
        </div>
      )
    }

    return (
      <div className="flex items-center space-x-2">
        <button
          onClick={handleAcceptChanges}
          disabled={!hasChanges}
          className="flex items-center space-x-1 px-3 py-1.5 text-sm bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Check className="h-3 w-3" />
          <span>Accept</span>
        </button>
        <button
          onClick={handleResetCode}
          disabled={!hasChanges}
          className="flex items-center space-x-1 px-3 py-1.5 text-sm bg-orange-600 text-white rounded-md hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <RotateCcw className="h-3 w-3" />
          <span>Reset</span>
        </button>
        <button
          onClick={handleCancelEdit}
          className="flex items-center space-x-1 px-3 py-1.5 text-sm bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
        >
          <X className="h-3 w-3" />
          <span>Cancel</span>
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Header with Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium text-gray-700">
            {editMode === 'manual' ? 'Manual Edit Mode' :
             editMode === 'ai_fix' ? 'AI Assist Mode' : 'Code View'}
          </span>
          {hasChanges && (
            <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded">
              Modified
            </span>
          )}
          {selectedLines && editMode === 'view' && (
            <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded">
              Lines {selectedLines.start}-{selectedLines.end} selected
            </span>
          )}
          {hasChanges && editMode === 'view' && (
            <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded">
              ✨ Inline diff active
            </span>
          )}
        </div>
        {renderActionButtons()}
      </div>

      {/* AI Fix Prompt Input */}
      {editMode === 'ai_fix' && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="block text-sm font-medium text-gray-700">
              Describe the fix you need:
            </label>
            {selectedLines && (
              <span className="text-xs text-purple-600 bg-purple-50 px-2 py-1 rounded">
                ✨ Focusing on lines {selectedLines.start}-{selectedLines.end}
              </span>
            )}
          </div>
          <div className="flex space-x-2">
            <textarea
              ref={aiPromptRef}
              value={aiFixPrompt}
              onChange={(e) => setAiFixPrompt(e.target.value)}
              placeholder={selectedLines 
                ? "The AI will focus on your selected lines. Describe what you want to fix or improve..."
                : "e.g., Fix the syntax error on line 5, optimize the loop performance, add error handling..."
              }
              className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
              rows={selectedLines ? 3 : 2}
            />
            <button
              onClick={handleAIFixSubmit}
              disabled={!aiFixPrompt.trim() || isProcessingAIFix}
              className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-1"
            >
              {isProcessingAIFix ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Wand2 className="h-4 w-4" />
              )}
              <span>{isProcessingAIFix ? 'Processing...' : 'Apply Fix'}</span>
            </button>
          </div>
        </div>
      )}

      {/* Code Editor */}
      <div className="border border-gray-200 rounded-md overflow-hidden">
        <Editor
          height="300px"
          language="python"
          value={currentCode}
          onChange={handleCodeChange}
          theme="vs-light"
          options={{
            readOnly: editMode === 'view' || readOnly,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            fontSize: 13,
            lineNumbers: 'on',
            glyphMargin: true, // Enable glyph margin for diff symbols
            folding: true,
            lineDecorationsWidth: 10,
            lineNumbersMinChars: 4,
            renderLineHighlight: editMode !== 'view' ? 'line' : 'none',
            scrollbar: {
              vertical: 'auto',
              horizontal: 'auto',
              verticalScrollbarSize: 8,
              horizontalScrollbarSize: 8
            },
            wordWrap: 'on',
            automaticLayout: true,
            padding: { top: 8, bottom: 8 },
            contextmenu: editMode !== 'view',
            selectOnLineNumbers: editMode !== 'view'
          }}
          onMount={(editor, monaco) => {
            editorRef.current = editor
            monacoRef.current = monaco
            
            // Listen for selection changes
            editor.onDidChangeCursorSelection(() => {
              captureSelection()
            })
          }}
          loading={
            <div className="flex items-center justify-center h-full bg-white text-gray-600">
              <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full mr-2" />
              Loading editor...
            </div>
          }
        />
      </div>

      {/* Diff View */}
      {showDiff && hasChanges && renderDiffView()}

      {/* Version History (collapsed by default) */}
      {versions.length > 1 && (
        <details className="border border-gray-200 rounded-md">
          <summary className="px-3 py-2 bg-gray-50 cursor-pointer text-sm font-medium text-gray-700 hover:bg-gray-100">
            Version History ({versions.length} versions)
          </summary>
          <div className="p-3 space-y-2">
            {versions.slice().reverse().map((version, index) => (
              <div key={index} className="flex items-center justify-between text-sm">
                <div className="flex items-center space-x-2">
                  <span className={`w-2 h-2 rounded-full ${
                    version.type === 'original' ? 'bg-gray-400' :
                    version.type === 'manual' ? 'bg-blue-500' :
                    'bg-purple-500'
                  }`} />
                  <span className="font-medium">
                    {version.type === 'original' ? 'Original' :
                     version.type === 'manual' ? 'Manual Edit' : 'AI Fix'}
                  </span>
                  <span className="text-gray-500">
                    {version.timestamp.toLocaleString()}
                  </span>
                </div>
                {version.description && (
                  <span className="text-gray-600 text-xs max-w-xs truncate">
                    {version.description}
                  </span>
                )}
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  )
}

export default EnhancedCodeEditor
