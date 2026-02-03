import React, { useState, useRef, useEffect } from 'react'
import { RefreshCw, ChevronDown, Zap, Bot, Bug, Eraser, MessageSquare, Play } from 'lucide-react'

interface ReRunDropdownProps {
  onExecuteCode: () => void
  onExecuteCodeWithAutofix?: () => void
  onExecuteAllFromHere?: () => void
  onRegenerateAndExecute: () => void
  onRegenerateAllFromHere?: () => void
  onRegenerateAndExecuteWithoutAutofix?: () => void
  onGuidedRegenerateAndExecute?: () => void
  onCleanRegenerateAndExecute?: () => void
  onCleanRegenerateAndExecuteWithoutAutofix?: () => void
  isExecuting?: boolean
}

const ReRunDropdown: React.FC<ReRunDropdownProps> = ({
  onExecuteCode,
  onExecuteCodeWithAutofix,
  onExecuteAllFromHere,
  onRegenerateAndExecute,
  onRegenerateAllFromHere,
  onRegenerateAndExecuteWithoutAutofix,
  onGuidedRegenerateAndExecute,
  onCleanRegenerateAndExecute,
  onCleanRegenerateAndExecuteWithoutAutofix,
  isExecuting = false
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleExecuteCode = () => {
    setIsOpen(false)
    onExecuteCode()
  }

  const handleExecuteCodeWithAutofix = () => {
    setIsOpen(false)
    onExecuteCodeWithAutofix?.()
  }

  const handleRegenerateAndExecute = () => {
    setIsOpen(false)
    onRegenerateAndExecute()
  }

  const handleRegenerateAllFromHere = () => {
    setIsOpen(false)
    onRegenerateAllFromHere?.()
  }

  const handleGuidedRegenerateAndExecute = () => {
    setIsOpen(false)
    onGuidedRegenerateAndExecute?.()
  }

  const handleExecuteAllFromHere = () => {
    setIsOpen(false)
    onExecuteAllFromHere?.()
  }

  const handleRegenerateAndExecuteWithoutAutofix = () => {
    setIsOpen(false)
    onRegenerateAndExecuteWithoutAutofix?.()
  }

  const handleCleanRegenerateAndExecute = () => {
    setIsOpen(false)
    onCleanRegenerateAndExecute?.()
  }

  const handleCleanRegenerateAndExecuteWithoutAutofix = () => {
    setIsOpen(false)
    onCleanRegenerateAndExecuteWithoutAutofix?.()
  }

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Main Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isExecuting}
        className={`
          flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors
          ${isExecuting 
            ? 'bg-gray-100 text-gray-400 cursor-not-allowed' 
            : 'bg-green-600 hover:bg-green-700 text-white shadow-sm hover:shadow-md'
          }
        `}
        title="Re-run options"
      >
        {isExecuting ? (
          <div className="animate-spin h-4 w-4 border-2 border-gray-400 border-t-transparent rounded-full" />
        ) : (
          <RefreshCw className="h-4 w-4" />
        )}
        <span>{isExecuting ? 'Running...' : 'Re-run'}</span>
        <ChevronDown className={`h-4 w-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && !isExecuting && (
        <div className="absolute top-full right-0 mt-1 w-80 bg-white border border-gray-200 rounded-md shadow-lg z-50">
          <div className="py-1">
            {/* Execute current cell code */}
            <button
              onClick={handleExecuteCode}
              className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0"
            >
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 mt-0.5">
                  <Zap className="h-4 w-4 text-blue-500" />
                </div>
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-900">Execute current cell code</div>
                  <div className="text-xs text-gray-500 mt-1">
                    Run current code (no auto-fix - code should already work)
                  </div>
                </div>
              </div>
            </button>

            {/* Execute current cell code WITH auto-fix (no regeneration) */}
            {onExecuteCodeWithAutofix && (
              <button
                onClick={handleExecuteCodeWithAutofix}
                className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0"
              >
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 mt-0.5">
                    <Bug className="h-4 w-4 text-orange-600" />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900">Execute current cell code (with auto-fix)</div>
                    <div className="text-xs text-gray-500 mt-1">
                      Execute current code and allow runtime + logic auto-corrections (no regeneration)
                    </div>
                  </div>
                </div>
              </button>
            )}

            {/* Execute all cells code from here */}
            {onExecuteAllFromHere && (
              <button
                onClick={handleExecuteAllFromHere}
                className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0"
              >
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 mt-0.5">
                    <Play className="h-4 w-4 text-green-600" />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900">Execute all cells code from here</div>
                    <div className="text-xs text-gray-500 mt-1">
                      Execute this cell and all downstream cells sequentially
                    </div>
                  </div>
                </div>
              </button>
            )}

            {/* Regenerate current cell */}
            <button
              onClick={handleRegenerateAndExecute}
              className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0"
            >
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 mt-0.5">
                  <Bot className="h-4 w-4 text-purple-500" />
                </div>
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-900">Regenerate current cell</div>
                  <div className="text-xs text-gray-500 mt-1">
                    Generate new code from prompt and execute (safe auto-fix enabled by default)
                  </div>
                </div>
              </div>
            </button>

            {/* Regenerate all cells from here */}
            {onRegenerateAllFromHere && (
              <button
                onClick={handleRegenerateAllFromHere}
                className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0"
              >
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 mt-0.5">
                    <Bot className="h-4 w-4 text-purple-600" />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900">Regenerate all cells from here</div>
                    <div className="text-xs text-gray-500 mt-1">
                      Regenerate and execute this cell and all downstream cells sequentially
                    </div>
                  </div>
                </div>
              </button>
            )}

            {/* Regenerate current cell without safe autofix */}
            {onRegenerateAndExecuteWithoutAutofix && (
              <button
                onClick={handleRegenerateAndExecuteWithoutAutofix}
                className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0"
              >
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 mt-0.5">
                    <Bug className="h-4 w-4 text-purple-600" />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900">Regenerate current cell without safe auto-fix</div>
                    <div className="text-xs text-gray-500 mt-1">
                      Generate new code and run without deterministic safe fixes (advanced debugging)
                    </div>
                  </div>
                </div>
              </button>
            )}

            {/* Guided rerun (keep context + user comment) */}
            {onGuidedRegenerateAndExecute && (
              <button
                onClick={handleGuidedRegenerateAndExecute}
                className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0"
              >
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 mt-0.5">
                    <MessageSquare className="h-4 w-4 text-blue-600" />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900">Guided rerun (keep context + comment)</div>
                    <div className="text-xs text-gray-500 mt-1">
                      Provide a short delta request to partially rewrite results; downstream cells will be invalidated
                    </div>
                  </div>
                </div>
              </button>
            )}

            {/* Clean rerun (rebuild context from upstream only) */}
            {onCleanRegenerateAndExecute && (
              <button
                onClick={handleCleanRegenerateAndExecute}
                className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0"
              >
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 mt-0.5">
                    <Eraser className="h-4 w-4 text-emerald-600" />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900">Clean rerun (restart from prompt)</div>
                    <div className="text-xs text-gray-500 mt-1">
                      Rebuild context from upstream cells only, regenerate code, then execute (safe auto-fix enabled by default)
                    </div>
                  </div>
                </div>
              </button>
            )}

            {/* Clean rerun without safe autofix */}
            {onCleanRegenerateAndExecuteWithoutAutofix && (
              <button
                onClick={handleCleanRegenerateAndExecuteWithoutAutofix}
                className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0"
              >
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 mt-0.5">
                    <Bug className="h-4 w-4 text-emerald-700" />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900">Clean rerun without safe auto-fix</div>
                    <div className="text-xs text-gray-500 mt-1">
                      Rebuild upstream-only context, regenerate code, and run without deterministic safe fixes (advanced debugging)
                    </div>
                  </div>
                </div>
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default ReRunDropdown
