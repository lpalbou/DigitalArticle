import React, { useCallback } from 'react'
import { RotateCcw, AlertTriangle } from 'lucide-react'
import PromptEditor from './PromptEditor'
import ResultPanel from './ResultPanel'
import { Cell, CellType } from '../types'

interface NotebookCellProps {
  cell: Cell
  onUpdateCell: (cellId: string, updates: Partial<Cell>) => void
  onDeleteCell: (cellId: string) => void
  onExecuteCell: (cellId: string, forceRegenerate?: boolean) => void
  onAddCellBelow: (cellId: string, cellType: CellType) => void
  isExecuting?: boolean
}

const NotebookCell: React.FC<NotebookCellProps> = ({
  cell,
  onUpdateCell,
  onDeleteCell: _onDeleteCell,
  onExecuteCell,
  onAddCellBelow: _onAddCellBelow,
  isExecuting = false
}) => {
  const handleUpdateCell = useCallback((updates: Partial<Cell>) => {
    onUpdateCell(cell.id, updates)
  }, [cell.id, onUpdateCell])

  const handleExecuteCell = useCallback((cellId: string, forceRegenerate?: boolean) => {
    onExecuteCell(cellId, forceRegenerate)
  }, [onExecuteCell])

  const isRunning = isExecuting || cell.is_executing

  return (
    <div className="cell-container">
      {/* Auto-Retry Status Indicator */}
      {cell.is_retrying && (
        <div className="mb-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="flex items-center space-x-2 text-yellow-800">
            <RotateCcw className="h-4 w-4 animate-spin" />
            <span className="text-sm font-medium">
              Auto-fixing execution error (attempt #{cell.retry_count})...
            </span>
          </div>
          <p className="text-xs text-yellow-700 mt-1">
            The AI is analyzing the error and generating corrected code.
          </p>
        </div>
      )}

      {/* Error with Retry Count Indicator */}
      {cell.last_result?.status === 'error' && cell.retry_count > 0 && !cell.is_retrying && (
        <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center space-x-2 text-red-800">
            <AlertTriangle className="h-4 w-4" />
            <span className="text-sm font-medium">
              Execution failed after {cell.retry_count} auto-retry attempt{cell.retry_count > 1 ? 's' : ''}
            </span>
          </div>
          <p className="text-xs text-red-700 mt-1">
            The AI attempted to fix the code automatically but was unsuccessful.
          </p>
        </div>
      )}

      {/* Cell Content */}
      <div className="cell-content">
        <PromptEditor
          cell={cell}
          onUpdateCell={handleUpdateCell}
          onExecuteCell={handleExecuteCell}
          isExecuting={isRunning}
        />

        {/* Results Display */}
        {cell.last_result && (
          <ResultPanel result={cell.last_result} />
        )}
      </div>
    </div>
  )
}

export default NotebookCell
