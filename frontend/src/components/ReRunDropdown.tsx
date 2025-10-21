import React, { useState, useRef, useEffect } from 'react'
import { Play, RefreshCw, ChevronDown, Zap, Bot } from 'lucide-react'

interface ReRunDropdownProps {
  onExecuteCode: () => void
  onRegenerateAndExecute: () => void
  isExecuting?: boolean
}

const ReRunDropdown: React.FC<ReRunDropdownProps> = ({
  onExecuteCode,
  onRegenerateAndExecute,
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
                    Run current code and regenerate methodology
                  </div>
                </div>
              </div>
            </button>

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
                    Generate new code from prompt and execute
                  </div>
                </div>
              </div>
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default ReRunDropdown
