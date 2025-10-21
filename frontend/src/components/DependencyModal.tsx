import React from 'react'
import { AlertTriangle, Zap, AlertCircle, Meh } from 'lucide-react'

interface DependencyModalProps {
  isOpen: boolean
  onClose: () => void
  onReRunAll: () => void
  onMarkStale: () => void
  onDoNothing: () => void
  affectedCellsCount: number
}

const DependencyModal: React.FC<DependencyModalProps> = ({
  isOpen,
  onClose,
  onReRunAll,
  onMarkStale,
  onDoNothing,
  affectedCellsCount
}) => {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div 
          className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          onClick={onClose}
        />

        {/* Modal panel */}
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          {/* Header */}
          <div className="bg-white px-6 py-4">
            <div className="flex items-center space-x-3">
              <div className="flex-shrink-0">
                <AlertTriangle className="h-6 w-6 text-orange-500" />
              </div>
              <div>
                <h3 className="text-lg font-medium text-gray-900">
                  Re-running this cell
                </h3>
                <p className="text-sm text-gray-500 mt-1">
                  This may affect {affectedCellsCount} cell{affectedCellsCount !== 1 ? 's' : ''} below that use data from this analysis.
                </p>
              </div>
            </div>
          </div>

          {/* Options */}
          <div className="bg-gray-50 px-6 py-4">
            <div className="space-y-3">
              {/* Re-run all */}
              <button
                onClick={() => {
                  onReRunAll()
                  onClose()
                }}
                className="w-full text-left p-4 bg-white border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-colors group"
              >
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 mt-0.5">
                    <Zap className="h-5 w-5 text-blue-500 group-hover:text-blue-600" />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900">
                      Re-run all affected cells
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      Automatically execute all {affectedCellsCount} cells below to keep results current
                    </div>
                  </div>
                </div>
              </button>

              {/* Mark as stale */}
              <button
                onClick={() => {
                  onMarkStale()
                  onClose()
                }}
                className="w-full text-left p-4 bg-white border border-gray-200 rounded-lg hover:border-amber-300 hover:bg-amber-50 transition-colors group"
              >
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 mt-0.5">
                    <AlertCircle className="h-5 w-5 text-amber-500 group-hover:text-amber-600" />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900">
                      Mark cells below as outdated
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      Show visual indicators that results may be stale (I'll decide later)
                    </div>
                  </div>
                </div>
              </button>

              {/* Do nothing */}
              <button
                onClick={() => {
                  onDoNothing()
                  onClose()
                }}
                className="w-full text-left p-4 bg-white border border-gray-200 rounded-lg hover:border-gray-300 hover:bg-gray-50 transition-colors group"
              >
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 mt-0.5">
                    <Meh className="h-5 w-5 text-gray-500 group-hover:text-gray-600" />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900">
                      Do nothing (I'll handle it)
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      Keep everything as is, I know what I'm doing
                    </div>
                  </div>
                </div>
              </button>
            </div>
          </div>

          {/* Footer */}
          <div className="bg-gray-50 px-6 py-3 border-t border-gray-200">
            <div className="flex justify-end">
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default DependencyModal
