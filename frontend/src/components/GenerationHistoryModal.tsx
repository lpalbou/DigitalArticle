import React, { useState, useEffect } from 'react'
import { X, Zap, ChevronDown, ChevronRight, Clock, Hash, Cpu } from 'lucide-react'

interface Trace {
  trace_id: string
  timestamp: string
  provider: string
  model: string
  system_prompt?: string
  prompt: string
  messages?: any[]
  tools?: any[]
  parameters: {
    temperature?: number
    max_tokens?: number
    seed?: number
    [key: string]: any
  }
  response: {
    content: string
    tool_calls?: any[]
    finish_reason?: string
    usage?: {
      prompt_tokens: number
      completion_tokens: number
      total_tokens: number
    }
    generation_time_ms?: number
  }
  metadata: {
    step_type: string
    attempt_number: number
    notebook_id?: string
    cell_id?: string
  }
}

interface Cell {
  id: string
  execution_count: number
}

interface GenerationHistoryModalProps {
  isOpen: boolean
  onClose: () => void
  cell: Cell
}

const GenerationHistoryModal: React.FC<GenerationHistoryModalProps> = ({ isOpen, onClose, cell }) => {
  const [traces, setTraces] = useState<Trace[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTraceIndex, setActiveTraceIndex] = useState(0)
  const [systemPromptCollapsed, setSystemPromptCollapsed] = useState(true)
  const [parametersCollapsed, setParametersCollapsed] = useState(true)

  useEffect(() => {
    if (isOpen && cell.id) {
      fetchTraces()
    }
  }, [isOpen, cell.id])

  const fetchTraces = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`/api/cells/${cell.id}/traces`)
      if (!response.ok) {
        throw new Error(`Failed to fetch traces: ${response.statusText}`)
      }
      const data = await response.json()
      setTraces(data.traces || [])
    } catch (err) {
      console.error('Error fetching traces:', err)
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  const getStepLabel = (trace: Trace) => {
    const { step_type, attempt_number } = trace.metadata

    if (step_type === 'code_generation') {
      return `Code Generation (Attempt ${attempt_number})`
    } else if (step_type === 'code_fix') {
      return `Code Fix (Attempt ${attempt_number})`
    } else if (step_type === 'methodology_generation') {
      return `Methodology Generation`
    }
    return `${step_type} (Attempt ${attempt_number})`
  }

  const formatTime = (ms?: number) => {
    if (!ms) return 'N/A'
    if (ms < 1000) return `${Math.round(ms)}ms`
    return `${(ms / 1000).toFixed(2)}s`
  }

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const currentTrace = traces[activeTraceIndex]

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div
          className="fixed inset-0 bg-gray-900 bg-opacity-75 transition-opacity"
          onClick={onClose}
        />

        {/* Modal panel */}
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-6xl sm:w-full">
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-600 to-indigo-700 px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <Zap className="h-6 w-6 text-white" />
                <h3 className="text-lg font-semibold text-white">
                  LLM Interaction Traces - Run {cell.execution_count}
                </h3>
              </div>
              <button
                onClick={onClose}
                className="text-white hover:text-gray-200 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Summary Stats */}
            {!loading && traces.length > 0 && (
              <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-white bg-opacity-10 rounded-lg px-3 py-2">
                  <div className="text-xs text-blue-200">Total Steps</div>
                  <div className="text-sm text-white font-bold">{traces.length}</div>
                </div>
                <div className="bg-white bg-opacity-10 rounded-lg px-3 py-2">
                  <div className="text-xs text-blue-200">Total Tokens</div>
                  <div className="text-sm text-white font-bold">
                    {traces.reduce((sum, t) => sum + (t.response.usage?.total_tokens || 0), 0).toLocaleString()}
                  </div>
                </div>
                <div className="bg-white bg-opacity-10 rounded-lg px-3 py-2">
                  <div className="text-xs text-blue-200">Total Time</div>
                  <div className="text-sm text-white font-bold">
                    {formatTime(traces.reduce((sum, t) => sum + (t.response.generation_time_ms || 0), 0))}
                  </div>
                </div>
                <div className="bg-white bg-opacity-10 rounded-lg px-3 py-2">
                  <div className="text-xs text-blue-200">Model</div>
                  <div className="text-sm text-white font-bold truncate">{currentTrace?.model || 'N/A'}</div>
                </div>
              </div>
            )}
          </div>

          {/* Loading State */}
          {loading && (
            <div className="px-6 py-12 text-center">
              <div className="animate-spin h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4" />
              <p className="text-gray-600">Loading traces...</p>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="px-6 py-8">
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-red-800 text-sm">Error: {error}</p>
              </div>
            </div>
          )}

          {/* No Traces */}
          {!loading && !error && traces.length === 0 && (
            <div className="px-6 py-12 text-center">
              <p className="text-gray-600">No traces available for this cell.</p>
              <p className="text-sm text-gray-400 mt-2">Traces are captured when cells are executed.</p>
            </div>
          )}

          {/* Trace Tabs */}
          {!loading && !error && traces.length > 0 && (
            <>
              <div className="border-b border-gray-200 bg-gray-50 overflow-x-auto">
                <div className="flex space-x-1 px-6 min-w-max">
                  {traces.map((trace, index) => (
                    <button
                      key={trace.trace_id}
                      onClick={() => setActiveTraceIndex(index)}
                      className={`px-4 py-3 text-sm font-medium transition-colors whitespace-nowrap ${
                        activeTraceIndex === index
                          ? 'text-blue-600 bg-white border-b-2 border-blue-600'
                          : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                      }`}
                    >
                      Step {index + 1}: {getStepLabel(trace)}
                    </button>
                  ))}
                </div>
              </div>

              {/* Trace Content */}
              {currentTrace && (
                <div className="px-6 py-4 max-h-[600px] overflow-y-auto">
                  <div className="space-y-6">
                    {/* Trace Metadata */}
                    <div className="flex items-center justify-between text-xs text-gray-500 pb-4 border-b">
                      <div className="flex items-center space-x-4">
                        <span>Trace ID: {currentTrace.trace_id}</span>
                        <span>•</span>
                        <span>{formatTimestamp(currentTrace.timestamp)}</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Clock className="h-3 w-3" />
                        <span>{formatTime(currentTrace.response.generation_time_ms)}</span>
                      </div>
                    </div>

                    {/* System Prompt (Collapsible) */}
                    {currentTrace.system_prompt && (
                      <div>
                        <button
                          onClick={() => setSystemPromptCollapsed(!systemPromptCollapsed)}
                          className="flex items-center space-x-2 text-sm font-semibold text-gray-700 hover:text-gray-900 mb-2"
                        >
                          {systemPromptCollapsed ? (
                            <ChevronRight className="h-4 w-4" />
                          ) : (
                            <ChevronDown className="h-4 w-4" />
                          )}
                          <span>System Prompt</span>
                        </button>
                        {!systemPromptCollapsed && (
                          <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                            <pre className="text-xs text-purple-900 whitespace-pre-wrap font-mono">
                              {currentTrace.system_prompt}
                            </pre>
                          </div>
                        )}
                      </div>
                    )}

                    {/* User Prompt */}
                    <div>
                      <div className="text-sm font-semibold text-gray-700 mb-2">User Prompt</div>
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <pre className="text-sm text-blue-900 whitespace-pre-wrap">
                          {currentTrace.prompt}
                        </pre>
                      </div>
                    </div>

                    {/* Parameters (Collapsible) */}
                    <div>
                      <button
                        onClick={() => setParametersCollapsed(!parametersCollapsed)}
                        className="flex items-center space-x-2 text-sm font-semibold text-gray-700 hover:text-gray-900 mb-2"
                      >
                        {parametersCollapsed ? (
                          <ChevronRight className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                        <span>Generation Parameters</span>
                      </button>
                      {!parametersCollapsed && (
                        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                            {Object.entries(currentTrace.parameters).map(([key, value]) => (
                              <div key={key}>
                                <div className="text-xs text-gray-500 font-medium">{key}</div>
                                <div className="text-gray-900 font-mono">{JSON.stringify(value)}</div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* LLM Response */}
                    <div>
                      <div className="text-sm font-semibold text-gray-700 mb-2">LLM Raw Response</div>
                      <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 max-h-96 overflow-y-auto">
                        <pre className="text-xs text-green-400 whitespace-pre-wrap font-mono">
                          {currentTrace.response.content}
                        </pre>
                      </div>
                    </div>

                    {/* Token Usage */}
                    {currentTrace.response.usage && (
                      <div>
                        <div className="text-sm font-semibold text-gray-700 mb-2 flex items-center space-x-2">
                          <Hash className="h-4 w-4" />
                          <span>Token Usage</span>
                        </div>
                        <div className="grid grid-cols-3 gap-4">
                          <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                            <div className="text-xs text-green-600 font-medium">Input Tokens</div>
                            <div className="text-lg text-green-900 font-bold">
                              {currentTrace.response.usage.prompt_tokens.toLocaleString()}
                            </div>
                          </div>
                          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                            <div className="text-xs text-blue-600 font-medium">Output Tokens</div>
                            <div className="text-lg text-blue-900 font-bold">
                              {currentTrace.response.usage.completion_tokens.toLocaleString()}
                            </div>
                          </div>
                          <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                            <div className="text-xs text-purple-600 font-medium">Total Tokens</div>
                            <div className="text-lg text-purple-900 font-bold">
                              {currentTrace.response.usage.total_tokens.toLocaleString()}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Additional Metadata */}
                    <div>
                      <div className="text-sm font-semibold text-gray-700 mb-2 flex items-center space-x-2">
                        <Cpu className="h-4 w-4" />
                        <span>Trace Metadata</span>
                      </div>
                      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                        <div className="grid grid-cols-2 gap-3 text-sm">
                          <div>
                            <div className="text-xs text-gray-500 font-medium">Provider</div>
                            <div className="text-gray-900 font-mono">{currentTrace.provider}</div>
                          </div>
                          <div>
                            <div className="text-xs text-gray-500 font-medium">Model</div>
                            <div className="text-gray-900 font-mono">{currentTrace.model}</div>
                          </div>
                          <div>
                            <div className="text-xs text-gray-500 font-medium">Step Type</div>
                            <div className="text-gray-900 font-mono">{currentTrace.metadata.step_type}</div>
                          </div>
                          <div>
                            <div className="text-xs text-gray-500 font-medium">Attempt Number</div>
                            <div className="text-gray-900 font-mono">{currentTrace.metadata.attempt_number}</div>
                          </div>
                          {currentTrace.response.finish_reason && (
                            <div>
                              <div className="text-xs text-gray-500 font-medium">Finish Reason</div>
                              <div className="text-gray-900 font-mono">{currentTrace.response.finish_reason}</div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          {/* Footer */}
          <div className="bg-gray-50 px-6 py-3 border-t border-gray-200">
            <button
              onClick={onClose}
              className="w-full sm:w-auto px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium text-sm"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default GenerationHistoryModal
