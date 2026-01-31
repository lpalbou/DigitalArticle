import React, { useState, useRef, useEffect } from 'react'
import { RefreshCw, ChevronDown, Zap, Bot, Bug, Eraser } from 'lucide-react'

interface ReRunDropdownProps {
  onExecuteCode: () => void
  onExecuteCodeWithoutAutofix?: () => void
  onRegenerateAndExecute: () => void
  onRegenerateAndExecuteWithoutAutofix?: () => void
  onCleanRegenerateAndExecute?: () => void
  onCleanRegenerateAndExecuteWithoutAutofix?: () => void
  isExecuting?: boolean
}

const ReRunDropdown: React.FC<ReRunDropdownProps> = ({
  onExecuteCode,
  onExecuteCodeWithoutAutofix,
  onRegenerateAndExecute,
  onRegenerateAndExecuteWithoutAutofix,
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

  const handleRegenerateAndExecute = () => {
    setIsOpen(false)
    onRegenerateAndExecute()
  }

  const handleExecuteCodeWithoutAutofix = () => {
    setIsOpen(false)
    onExecuteCodeWithoutAutofix?.()
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
            {/* Execute existing code */}
            <button
              onClick={handleExecuteCode}
              className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0"
            >
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 mt-0.5">
                  <Zap className="h-4 w-4 text-blue-500" />
                </div>
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-900">Execute existing code</div>
                  <div className="text-xs text-gray-500 mt-1">
                    Run current code (safe auto-fix is enabled by default)
                  </div>
                </div>
              </div>
            </button>

            {/* Execute existing code without safe autofix */}
            {onExecuteCodeWithoutAutofix && (
              <button
                onClick={handleExecuteCodeWithoutAutofix}
                className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0"
              >
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 mt-0.5">
                    <Bug className="h-4 w-4 text-purple-600" />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900">Execute without safe auto-fix</div>
                    <div className="text-xs text-gray-500 mt-1">
                      Bypass deterministic safe fixes (advanced debugging)
                    </div>
                  </div>
                </div>
              </button>
            )}

            {/* Regenerate code and execute */}
            <button
              onClick={handleRegenerateAndExecute}
              className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0"
            >
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 mt-0.5">
                  <Bot className="h-4 w-4 text-purple-500" />
                </div>
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-900">Regenerate code & execute</div>
                  <div className="text-xs text-gray-500 mt-1">
                    Generate new code from prompt and execute (safe auto-fix enabled by default)
                  </div>
                </div>
              </div>
            </button>

            {/* Regenerate code and execute without safe autofix */}
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
                    <div className="text-sm font-medium text-gray-900">Regenerate & execute without safe auto-fix</div>
                    <div className="text-xs text-gray-500 mt-1">
                      Generate new code and run without deterministic safe fixes (advanced debugging)
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
