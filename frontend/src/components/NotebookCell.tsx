import React, { useCallback } from 'react'
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
