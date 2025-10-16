import React, { useCallback } from 'react'
import { MoreHorizontal, Trash2, Plus } from 'lucide-react'
import PromptEditor from './PromptEditor'
import ResultPanel from './ResultPanel'
import { Cell, CellType, ExecutionStatus } from '../types'

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
  onDeleteCell,
  onExecuteCell,
  onAddCellBelow,
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
      {/* Cell Header */}
      <div className="cell-header">
        <div className="flex items-center space-x-2">
        </div>

        {/* Cell Actions */}
        <div className="flex items-center space-x-2">

          {/* More Actions Menu */}
          <div className="relative group">
            <button className="p-1 text-gray-400 hover:text-gray-600 rounded">
              <MoreHorizontal className="h-4 w-4" />
            </button>
            
            {/* Dropdown Menu */}
            <div className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-md shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-10">
              <div className="py-1 min-w-48">
                <button
                  onClick={() => onAddCellBelow(cell.id, CellType.PROMPT)}
                  className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center space-x-2"
                >
                  <Plus className="h-4 w-4" />
                  <span>Add Prompt Below</span>
                </button>
                
                <button
                  onClick={() => onAddCellBelow(cell.id, CellType.CODE)}
                  className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center space-x-2"
                >
                  <Plus className="h-4 w-4" />
                  <span>Add Code Below</span>
                </button>
                
                <button
                  onClick={() => onAddCellBelow(cell.id, CellType.MARKDOWN)}
                  className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center space-x-2"
                >
                  <Plus className="h-4 w-4" />
                  <span>Add Markdown Below</span>
                </button>
                
                <div className="border-t border-gray-100 my-1" />
                
                <button
                  onClick={() => handleExecuteCell(cell.id, true)}
                  disabled={isRunning || cell.cell_type === CellType.MARKDOWN}
                  className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Force Regenerate & Run
                </button>
                
                <div className="border-t border-gray-100 my-1" />
                
                <button
                  onClick={() => onDeleteCell(cell.id)}
                  className="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center space-x-2"
                >
                  <Trash2 className="h-4 w-4" />
                  <span>Delete Cell</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

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
