import React, { useState } from 'react'
import { X, ChevronDown, ChevronRight, Activity, Download, Copy, Check } from 'lucide-react'
import { LLMTrace } from '../types'

interface LLMTraceModalProps {
  isVisible: boolean
  cellId: string
  traces: LLMTrace[]
  onClose: () => void
}

const LLMTraceModal: React.FC<LLMTraceModalProps> = ({
  isVisible,
  cellId,
  traces,
  onClose
}) => {
  const [expandedTraces, setExpandedTraces] = useState<Set<string>>(new Set())
  const [copiedId, setCopiedId] = useState<string | null>(null)

  if (!isVisible) return null

  const toggleTrace = (traceId: string) => {
    const newExpanded = new Set(expandedTraces)
    if (newExpanded.has(traceId)) {
      newExpanded.delete(traceId)
    } else {
      newExpanded.add(traceId)
    }
    setExpandedTraces(newExpanded)
  }

  const getStepTypeLabel = (stepType: string): string => {
    switch (stepType) {
      case 'code_generation':
        return 'Code Generation'
      case 'code_fix':
        return 'Code Fix / Retry'
      case 'methodology_generation':
        return 'Methodology Generation'
      default:
        return stepType
    }
  }

  const getStepTypeColor = (stepType: string): string => {
    switch (stepType) {
      case 'code_generation':
        return 'text-blue-600 bg-blue-50'
      case 'code_fix':
        return 'text-yellow-600 bg-yellow-50'
      case 'methodology_generation':
        return 'text-purple-600 bg-purple-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  const getSuccessIndicator = (trace: LLMTrace): { color: string, label: string } => {
    const finishReason = trace.response?.finish_reason
    if (finishReason === 'stop') {
      return { color: 'text-green-600', label: '✓ Success' }
    } else if (trace.metadata?.step_type === 'code_fix') {
      return { color: 'text-yellow-600', label: '⚠ Retry' }
    } else {
      return { color: 'text-gray-600', label: '○ Complete' }
    }
  }

  const formatTimestamp = (timestamp: string): string => {
    try {
      const date = new Date(timestamp)
      return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    } catch {
      return timestamp
    }
  }

  const calculateTotalTokens = (): number => {
    return traces.reduce((sum, trace) => {
      const usage = trace.response?.usage
      return sum + (usage?.total_tokens || 0)
    }, 0)
  }

  const calculateTotalTime = (): number => {
    return traces.reduce((sum, trace) => {
      return sum + (trace.response?.generation_time_ms || 0)
    }, 0)
  }

  const estimateCost = (totalTokens: number): string => {
    // Rough estimate: $0.01 per 1000 tokens (adjust based on actual model pricing)
    const costPer1kTokens = 0.01
    const cost = (totalTokens / 1000) * costPer1kTokens
    return cost.toFixed(4)
  }

  const copyToClipboard = async (text: string, traceId: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedId(traceId)
      setTimeout(() => setCopiedId(null), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const exportTraces = () => {
    const jsonl = traces.map(trace => JSON.stringify(trace)).join('\n')
    const blob = new Blob([jsonl], { type: 'application/jsonl' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `llm-traces-${cellId}.jsonl`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const totalTokens = calculateTotalTokens()
  const totalTime = calculateTotalTime()
  const estimatedCost = estimateCost(totalTokens)

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={onClose}></div>

        {/* Modal panel */}
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
          {/* Header */}
          <div className="bg-white px-6 pt-6 pb-4 border-b border-gray-200">
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-3">
                <Activity className="h-6 w-6 text-blue-600" />
                <div>
                  <h3 className="text-lg leading-6 font-medium text-gray-900">
                    LLM Execution Traces
                  </h3>
                  <p className="mt-1 text-sm text-gray-500">
                    Complete trace history for cell {cellId.slice(0, 8)}...
                  </p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="ml-4 text-gray-400 hover:text-gray-500"
              >
                <X className="h-6 w-6" />
              </button>
            </div>
          </div>

          {/* Summary Section */}
          <div className="bg-gray-50 px-6 py-4 border-b border-gray-200">
            <div className="grid grid-cols-4 gap-4 text-center">
              <div>
                <p className="text-sm font-medium text-gray-500">Total Attempts</p>
                <p className="mt-1 text-2xl font-semibold text-gray-900">{traces.length}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Total Tokens</p>
                <p className="mt-1 text-2xl font-semibold text-gray-900">{totalTokens.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Total Time</p>
                <p className="mt-1 text-2xl font-semibold text-gray-900">{(totalTime / 1000).toFixed(1)}s</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Est. Cost</p>
                <p className="mt-1 text-2xl font-semibold text-gray-900">${estimatedCost}</p>
              </div>
            </div>
          </div>

          {/* Traces Timeline */}
          <div className="bg-white px-6 py-4 max-h-96 overflow-y-auto">
            {traces.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <Activity className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                <p>No traces available for this cell</p>
              </div>
            ) : (
              <div className="space-y-4">
                {traces.map((trace, index) => {
                  const isExpanded = expandedTraces.has(trace.trace_id)
                  const successInfo = getSuccessIndicator(trace)
                  const stepType = trace.metadata?.step_type || 'unknown'
                  const attemptNumber = trace.metadata?.attempt_number || index + 1
                  const inputTokens = trace.response?.usage?.input_tokens || trace.response?.usage?.prompt_tokens || 0
                  const outputTokens = trace.response?.usage?.output_tokens || trace.response?.usage?.completion_tokens || 0
                  const totalTraceTokens = trace.response?.usage?.total_tokens || 0
                  const genTime = trace.response?.generation_time_ms || 0

                  return (
                    <div key={trace.trace_id} className="border border-gray-200 rounded-lg overflow-hidden">
                      {/* Trace Header - Clickable */}
                      <div
                        className="p-4 bg-gray-50 cursor-pointer hover:bg-gray-100 transition-colors"
                        onClick={() => toggleTrace(trace.trace_id)}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-3">
                            {isExpanded ? (
                              <ChevronDown className="h-5 w-5 text-gray-400" />
                            ) : (
                              <ChevronRight className="h-5 w-5 text-gray-400" />
                            )}
                            <div>
                              <div className="flex items-center space-x-2">
                                <span className={`px-2 py-1 rounded text-xs font-medium ${getStepTypeColor(stepType)}`}>
                                  {getStepTypeLabel(stepType)}
                                </span>
                                <span className="text-xs text-gray-500">
                                  Attempt #{attemptNumber}
                                </span>
                                <span className={`text-sm font-medium ${successInfo.color}`}>
                                  {successInfo.label}
                                </span>
                              </div>
                              <div className="mt-1 text-xs text-gray-500">
                                {formatTimestamp(trace.timestamp)} • {genTime}ms • {totalTraceTokens} tokens ({inputTokens}→{outputTokens})
                              </div>
                            </div>
                          </div>
                          <div className="text-xs text-gray-400">
                            {trace.provider} / {trace.model}
                          </div>
                        </div>
                      </div>

                      {/* Trace Details - Expandable */}
                      {isExpanded && (
                        <div className="p-4 space-y-4 bg-white border-t border-gray-200">
                          {/* System Prompt */}
                          {trace.system_prompt && (
                            <div>
                              <div className="flex items-center justify-between mb-2">
                                <h4 className="text-sm font-medium text-gray-700">System Prompt</h4>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    copyToClipboard(trace.system_prompt || '', `${trace.trace_id}-system`)
                                  }}
                                  className="text-gray-400 hover:text-gray-600"
                                >
                                  {copiedId === `${trace.trace_id}-system` ? (
                                    <Check className="h-4 w-4 text-green-500" />
                                  ) : (
                                    <Copy className="h-4 w-4" />
                                  )}
                                </button>
                              </div>
                              <pre className="text-xs bg-gray-50 p-3 rounded border border-gray-200 overflow-x-auto max-h-32">
                                {trace.system_prompt}
                              </pre>
                            </div>
                          )}

                          {/* User Prompt */}
                          <div>
                            <div className="flex items-center justify-between mb-2">
                              <h4 className="text-sm font-medium text-gray-700">User Prompt</h4>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  copyToClipboard(trace.prompt, `${trace.trace_id}-prompt`)
                                }}
                                className="text-gray-400 hover:text-gray-600"
                              >
                                {copiedId === `${trace.trace_id}-prompt` ? (
                                  <Check className="h-4 w-4 text-green-500" />
                                ) : (
                                  <Copy className="h-4 w-4" />
                                )}
                              </button>
                            </div>
                            <pre className="text-xs bg-gray-50 p-3 rounded border border-gray-200 overflow-x-auto max-h-32">
                              {trace.prompt}
                            </pre>
                          </div>

                          {/* Response */}
                          <div>
                            <div className="flex items-center justify-between mb-2">
                              <h4 className="text-sm font-medium text-gray-700">Response</h4>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  copyToClipboard(trace.response?.content || '', `${trace.trace_id}-response`)
                                }}
                                className="text-gray-400 hover:text-gray-600"
                              >
                                {copiedId === `${trace.trace_id}-response` ? (
                                  <Check className="h-4 w-4 text-green-500" />
                                ) : (
                                  <Copy className="h-4 w-4" />
                                )}
                              </button>
                            </div>
                            <pre className="text-xs bg-gray-50 p-3 rounded border border-gray-200 overflow-x-auto max-h-32">
                              {trace.response?.content}
                            </pre>
                          </div>

                          {/* Parameters */}
                          <div>
                            <h4 className="text-sm font-medium text-gray-700 mb-2">Parameters</h4>
                            <div className="text-xs text-gray-600 space-y-1">
                              {Object.entries(trace.parameters || {}).map(([key, value]) => (
                                <div key={key} className="flex">
                                  <span className="font-mono text-gray-500 w-32">{key}:</span>
                                  <span className="font-mono">{JSON.stringify(value)}</span>
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Raw JSON */}
                          <div>
                            <div className="flex items-center justify-between mb-2">
                              <h4 className="text-sm font-medium text-gray-700">Raw JSON</h4>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  copyToClipboard(JSON.stringify(trace, null, 2), `${trace.trace_id}-json`)
                                }}
                                className="text-gray-400 hover:text-gray-600"
                              >
                                {copiedId === `${trace.trace_id}-json` ? (
                                  <Check className="h-4 w-4 text-green-500" />
                                ) : (
                                  <Copy className="h-4 w-4" />
                                )}
                              </button>
                            </div>
                            <pre className="text-xs bg-gray-50 p-3 rounded border border-gray-200 overflow-x-auto max-h-32">
                              {JSON.stringify(trace, null, 2)}
                            </pre>
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Footer with Export */}
          <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex justify-between items-center">
            <p className="text-xs text-gray-500">
              Traces are persisted with the notebook and survive server restarts
            </p>
            <button
              onClick={exportTraces}
              disabled={traces.length === 0}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              <Download className="h-4 w-4 mr-2" />
              Export JSONL
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default LLMTraceModal
