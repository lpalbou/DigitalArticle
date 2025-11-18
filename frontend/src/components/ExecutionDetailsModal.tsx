import React, { useState, useEffect } from 'react'
import { X, ChevronDown, ChevronRight, Activity, Download, Copy, Check, Terminal, AlertTriangle, Table as TableIcon, Zap, Database } from 'lucide-react'
import { LLMTrace, ExecutionResult, TableData } from '../types'

interface ExecutionDetailsModalProps {
  isVisible: boolean
  cellId: string
  notebookId: string
  traces: LLMTrace[]
  executionResult: ExecutionResult | null
  onClose: () => void
}

const ExecutionDetailsModal: React.FC<ExecutionDetailsModalProps> = ({
  isVisible,
  cellId,
  notebookId,
  traces,
  executionResult,
  onClose
}) => {
  const [expandedTraces, setExpandedTraces] = useState<Set<string>>(new Set())
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [activeMainTab, setActiveMainTab] = useState<'llm' | 'console' | 'warnings' | 'data' | 'variables'>('llm')
  const [activeTraceTab, setActiveTraceTab] = useState<Record<string, 'prompt' | 'system' | 'response' | 'parameters' | 'json'>>({})
  const [variables, setVariables] = useState<Record<string, string>>({})
  const [loadingVariables, setLoadingVariables] = useState(false)

  // Fetch variables when modal is opened
  useEffect(() => {
    if (isVisible && notebookId && cellId) {
      setLoadingVariables(true)
      fetch(`/api/cells/${notebookId}/${cellId}/variables`)
        .then(res => res.json())
        .then(data => {
          setVariables(data.variables || {})
          setLoadingVariables(false)
        })
        .catch(err => {
          console.error('Failed to fetch variables:', err)
          setLoadingVariables(false)
        })
    }
  }, [isVisible, notebookId, cellId])

  if (!isVisible) return null

  const toggleTrace = (traceId: string) => {
    const newExpanded = new Set(expandedTraces)
    if (newExpanded.has(traceId)) {
      newExpanded.delete(traceId)
    } else {
      newExpanded.add(traceId)
      if (!activeTraceTab[traceId]) {
        setActiveTraceTab({ ...activeTraceTab, [traceId]: 'prompt' })
      }
    }
    setExpandedTraces(newExpanded)
  }

  const setTraceTab = (traceId: string, tab: 'prompt' | 'system' | 'response' | 'parameters' | 'json') => {
    setActiveTraceTab({ ...activeTraceTab, [traceId]: tab })
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
    const content = trace.response?.content || ''
    const hasValidContent = content.trim().length > 10

    const isMethodology = trace.metadata?.step_type === 'methodology_generation'
    if (isMethodology && !hasValidContent) {
      return { color: 'text-red-600', label: '✗ Failed' }
    }

    if (finishReason === 'content_filter' || finishReason === 'error') {
      return { color: 'text-red-600', label: '✗ Failed' }
    }

    if (hasValidContent && (finishReason === 'stop' || finishReason === 'length' || finishReason === 'tool_calls')) {
      return { color: 'text-green-600', label: '✓ Success' }
    }

    if (!hasValidContent) {
      return { color: 'text-red-600', label: '✗ Failed' }
    }

    if (hasValidContent) {
      return { color: 'text-green-600', label: '✓ Success' }
    }

    return { color: 'text-gray-600', label: '○ Unknown' }
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
    const costPer1kTokens = 0.01
    const cost = (totalTokens / 1000) * costPer1kTokens
    return cost.toFixed(4)
  }

  const copyToClipboard = async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedId(id)
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
    a.download = `execution-traces-${cellId}.jsonl`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const totalTokens = calculateTotalTokens()
  const totalTime = calculateTotalTime()
  const estimatedCost = estimateCost(totalTokens)

  // Get intermediary data tables (source='variable')
  const intermediaryTables = executionResult?.tables.filter((t: any) => t.source === 'variable') || []

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={onClose}></div>

        {/* Modal panel */}
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-5xl sm:w-full">
          {/* Header */}
          <div className="bg-white px-6 pt-6 pb-4 border-b border-gray-200">
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-3">
                <Zap className="h-6 w-6 text-blue-600" />
                <div>
                  <h3 className="text-lg leading-6 font-medium text-gray-900">
                    Execution Details
                  </h3>
                  <p className="mt-1 text-sm text-gray-500">
                    Complete execution information for cell {cellId.slice(0, 8)}...
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

          {/* Main Tab Navigation */}
          <div className="bg-gray-50 border-b border-gray-200">
            <div className="flex">
              <button
                onClick={() => setActiveMainTab('llm')}
                className={`px-6 py-3 text-sm font-medium transition-colors flex items-center space-x-2 ${
                  activeMainTab === 'llm'
                    ? 'border-b-2 border-blue-500 text-blue-600 bg-white'
                    : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                }`}
              >
                <Activity className="h-4 w-4" />
                <span>LLM Traces</span>
                <span className="ml-1 px-2 py-0.5 text-xs bg-gray-100 rounded-full">{traces.length}</span>
              </button>
              <button
                onClick={() => setActiveMainTab('console')}
                className={`px-6 py-3 text-sm font-medium transition-colors flex items-center space-x-2 ${
                  activeMainTab === 'console'
                    ? 'border-b-2 border-blue-500 text-blue-600 bg-white'
                    : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                }`}
              >
                <Terminal className="h-4 w-4" />
                <span>Console Output</span>
              </button>
              {executionResult?.stderr && (
                <button
                  onClick={() => setActiveMainTab('warnings')}
                  className={`px-6 py-3 text-sm font-medium transition-colors flex items-center space-x-2 ${
                    activeMainTab === 'warnings'
                      ? 'border-b-2 border-yellow-500 text-yellow-600 bg-white'
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  <AlertTriangle className="h-4 w-4" />
                  <span>Warnings</span>
                </button>
              )}
              {intermediaryTables.length > 0 && (
                <button
                  onClick={() => setActiveMainTab('data')}
                  className={`px-6 py-3 text-sm font-medium transition-colors flex items-center space-x-2 ${
                    activeMainTab === 'data'
                      ? 'border-b-2 border-blue-500 text-blue-600 bg-white'
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  <TableIcon className="h-4 w-4" />
                  <span>Data Tables</span>
                  <span className="ml-1 px-2 py-0.5 text-xs bg-gray-100 rounded-full">{intermediaryTables.length}</span>
                </button>
              )}
              <button
                onClick={() => setActiveMainTab('variables')}
                className={`px-6 py-3 text-sm font-medium transition-colors flex items-center space-x-2 ${
                  activeMainTab === 'variables'
                    ? 'border-b-2 border-green-500 text-green-600 bg-white'
                    : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                }`}
              >
                <Database className="h-4 w-4" />
                <span>Variables</span>
                {Object.keys(variables).length > 0 && (
                  <span className="ml-1 px-2 py-0.5 text-xs bg-gray-100 rounded-full">{Object.keys(variables).length}</span>
                )}
              </button>
            </div>
          </div>

          {/* Tab Content */}
          <div className="bg-white px-6 py-4 max-h-[600px] overflow-y-auto">
            {/* LLM Traces Tab */}
            {activeMainTab === 'llm' && (
              <div>
                {/* Summary Section */}
                <div className="bg-gray-50 px-4 py-3 rounded-lg border border-gray-200 mb-4">
                  <div className="grid grid-cols-4 gap-4 text-center">
                    <div>
                      <p className="text-xs font-medium text-gray-500">Total Calls</p>
                      <p className="mt-1 text-xl font-semibold text-gray-900">{traces.length}</p>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-gray-500">Total Tokens</p>
                      <p className="mt-1 text-xl font-semibold text-gray-900">{totalTokens.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-gray-500">Total Time</p>
                      <p className="mt-1 text-xl font-semibold text-gray-900">{(totalTime / 1000).toFixed(1)}s</p>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-gray-500">Est. Cost</p>
                      <p className="mt-1 text-xl font-semibold text-gray-900">${estimatedCost}</p>
                    </div>
                  </div>
                </div>

                {/* Traces List */}
                {traces.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">
                    <Activity className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                    <p>No LLM traces available for this cell</p>
                  </div>
                ) : (
                  <div className="space-y-3">
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
                          {/* Trace Header */}
                          <div
                            className="p-3 bg-gray-50 cursor-pointer hover:bg-gray-100 transition-colors"
                            onClick={() => toggleTrace(trace.trace_id)}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center space-x-3">
                                {isExpanded ? (
                                  <ChevronDown className="h-4 w-4 text-gray-400" />
                                ) : (
                                  <ChevronRight className="h-4 w-4 text-gray-400" />
                                )}
                                <div>
                                  <div className="flex items-center space-x-2">
                                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${getStepTypeColor(stepType)}`}>
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

                          {/* Trace Details with Sub-tabs */}
                          {isExpanded && (
                            <div className="bg-white border-t border-gray-200">
                              {/* Sub-tab Header */}
                              <div className="flex border-b border-gray-200 bg-gray-50">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    setTraceTab(trace.trace_id, 'prompt')
                                  }}
                                  className={`px-3 py-2 text-xs font-medium transition-colors ${
                                    (activeTraceTab[trace.trace_id] || 'prompt') === 'prompt'
                                      ? 'border-b-2 border-blue-500 text-blue-600 bg-white'
                                      : 'text-gray-500 hover:text-gray-700'
                                  }`}
                                >
                                  Prompt
                                </button>
                                {trace.system_prompt && (
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      setTraceTab(trace.trace_id, 'system')
                                    }}
                                    className={`px-3 py-2 text-xs font-medium transition-colors ${
                                      activeTraceTab[trace.trace_id] === 'system'
                                        ? 'border-b-2 border-blue-500 text-blue-600 bg-white'
                                        : 'text-gray-500 hover:text-gray-700'
                                    }`}
                                  >
                                    System
                                  </button>
                                )}
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    setTraceTab(trace.trace_id, 'response')
                                  }}
                                  className={`px-3 py-2 text-xs font-medium transition-colors ${
                                    activeTraceTab[trace.trace_id] === 'response'
                                      ? 'border-b-2 border-blue-500 text-blue-600 bg-white'
                                      : 'text-gray-500 hover:text-gray-700'
                                  }`}
                                >
                                  Response
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    setTraceTab(trace.trace_id, 'parameters')
                                  }}
                                  className={`px-3 py-2 text-xs font-medium transition-colors ${
                                    activeTraceTab[trace.trace_id] === 'parameters'
                                      ? 'border-b-2 border-blue-500 text-blue-600 bg-white'
                                      : 'text-gray-500 hover:text-gray-700'
                                  }`}
                                >
                                  Parameters
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    setTraceTab(trace.trace_id, 'json')
                                  }}
                                  className={`px-3 py-2 text-xs font-medium transition-colors ${
                                    activeTraceTab[trace.trace_id] === 'json'
                                      ? 'border-b-2 border-blue-500 text-blue-600 bg-white'
                                      : 'text-gray-500 hover:text-gray-700'
                                  }`}
                                >
                                  JSON
                                </button>
                              </div>

                              {/* Sub-tab Content */}
                              <div className="p-3">
                                {/* Prompt Tab */}
                                {(activeTraceTab[trace.trace_id] || 'prompt') === 'prompt' && (
                                  <div>
                                    <div className="flex items-center justify-between mb-2">
                                      <h5 className="text-xs font-medium text-gray-700">User Prompt</h5>
                                      <button
                                        onClick={(e) => {
                                          e.stopPropagation()
                                          copyToClipboard(trace.prompt, `${trace.trace_id}-prompt`)
                                        }}
                                        className="text-gray-400 hover:text-gray-600 flex items-center space-x-1"
                                      >
                                        {copiedId === `${trace.trace_id}-prompt` ? (
                                          <>
                                            <Check className="h-3 w-3 text-green-500" />
                                            <span className="text-xs text-green-500">Copied!</span>
                                          </>
                                        ) : (
                                          <>
                                            <Copy className="h-3 w-3" />
                                            <span className="text-xs">Copy</span>
                                          </>
                                        )}
                                      </button>
                                    </div>
                                    <pre className="text-xs bg-gray-50 p-3 rounded border border-gray-200 overflow-x-auto max-h-64 whitespace-pre-wrap">
                                      {trace.prompt}
                                    </pre>
                                  </div>
                                )}

                                {/* System Tab */}
                                {activeTraceTab[trace.trace_id] === 'system' && trace.system_prompt && (
                                  <div>
                                    <div className="flex items-center justify-between mb-2">
                                      <h5 className="text-xs font-medium text-gray-700">System Prompt</h5>
                                      <button
                                        onClick={(e) => {
                                          e.stopPropagation()
                                          copyToClipboard(trace.system_prompt || '', `${trace.trace_id}-system`)
                                        }}
                                        className="text-gray-400 hover:text-gray-600 flex items-center space-x-1"
                                      >
                                        {copiedId === `${trace.trace_id}-system` ? (
                                          <>
                                            <Check className="h-3 w-3 text-green-500" />
                                            <span className="text-xs text-green-500">Copied!</span>
                                          </>
                                        ) : (
                                          <>
                                            <Copy className="h-3 w-3" />
                                            <span className="text-xs">Copy</span>
                                          </>
                                        )}
                                      </button>
                                    </div>
                                    <pre className="text-xs bg-gray-50 p-3 rounded border border-gray-200 overflow-x-auto max-h-64 whitespace-pre-wrap">
                                      {trace.system_prompt}
                                    </pre>
                                  </div>
                                )}

                                {/* Response Tab */}
                                {activeTraceTab[trace.trace_id] === 'response' && (
                                  <div>
                                    <div className="flex items-center justify-between mb-2">
                                      <h5 className="text-xs font-medium text-gray-700">Response</h5>
                                      <button
                                        onClick={(e) => {
                                          e.stopPropagation()
                                          copyToClipboard(trace.response?.content || '', `${trace.trace_id}-response`)
                                        }}
                                        className="text-gray-400 hover:text-gray-600 flex items-center space-x-1"
                                      >
                                        {copiedId === `${trace.trace_id}-response` ? (
                                          <>
                                            <Check className="h-3 w-3 text-green-500" />
                                            <span className="text-xs text-green-500">Copied!</span>
                                          </>
                                        ) : (
                                          <>
                                            <Copy className="h-3 w-3" />
                                            <span className="text-xs">Copy</span>
                                          </>
                                        )}
                                      </button>
                                    </div>
                                    <pre className="text-xs bg-gray-50 p-3 rounded border border-gray-200 overflow-x-auto max-h-64 whitespace-pre-wrap">
                                      {trace.response?.content}
                                    </pre>
                                  </div>
                                )}

                                {/* Parameters Tab */}
                                {activeTraceTab[trace.trace_id] === 'parameters' && (
                                  <div>
                                    <h5 className="text-xs font-medium text-gray-700 mb-2">LLM Parameters</h5>
                                    <div className="bg-gray-50 p-3 rounded border border-gray-200">
                                      <div className="text-xs text-gray-600 space-y-1">
                                        {Object.entries(trace.parameters || {}).map(([key, value]) => (
                                          <div key={key} className="flex items-start">
                                            <span className="font-mono text-gray-500 w-32 flex-shrink-0">{key}:</span>
                                            <span className="font-mono text-gray-900">{JSON.stringify(value)}</span>
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  </div>
                                )}

                                {/* JSON Tab */}
                                {activeTraceTab[trace.trace_id] === 'json' && (
                                  <div>
                                    <div className="flex items-center justify-between mb-2">
                                      <h5 className="text-xs font-medium text-gray-700">Complete Trace (JSON)</h5>
                                      <button
                                        onClick={(e) => {
                                          e.stopPropagation()
                                          copyToClipboard(JSON.stringify(trace, null, 2), `${trace.trace_id}-json`)
                                        }}
                                        className="text-gray-400 hover:text-gray-600 flex items-center space-x-1"
                                      >
                                        {copiedId === `${trace.trace_id}-json` ? (
                                          <>
                                            <Check className="h-3 w-3 text-green-500" />
                                            <span className="text-xs text-green-500">Copied!</span>
                                          </>
                                        ) : (
                                          <>
                                            <Copy className="h-3 w-3" />
                                            <span className="text-xs">Copy</span>
                                          </>
                                        )}
                                      </button>
                                    </div>
                                    <pre className="text-xs bg-gray-50 p-3 rounded border border-gray-200 overflow-x-auto max-h-64">
                                      {JSON.stringify(trace, null, 2)}
                                    </pre>
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )}

            {/* Console Output Tab */}
            {activeMainTab === 'console' && (
              <div>
                {executionResult?.stdout ? (
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-sm font-medium text-gray-700">Console Output (stdout)</h4>
                      <button
                        onClick={() => copyToClipboard(executionResult.stdout, 'console-output')}
                        className="text-gray-400 hover:text-gray-600 flex items-center space-x-1"
                      >
                        {copiedId === 'console-output' ? (
                          <>
                            <Check className="h-4 w-4 text-green-500" />
                            <span className="text-xs text-green-500">Copied!</span>
                          </>
                        ) : (
                          <>
                            <Copy className="h-4 w-4" />
                            <span className="text-xs">Copy</span>
                          </>
                        )}
                      </button>
                    </div>
                    <pre className="text-xs bg-gray-900 text-green-400 p-4 rounded border border-gray-700 overflow-x-auto max-h-96 whitespace-pre font-mono">
                      {executionResult.stdout}
                    </pre>
                  </div>
                ) : (
                  <div className="text-center py-12 text-gray-500">
                    <Terminal className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                    <p>No console output for this cell</p>
                  </div>
                )}
              </div>
            )}

            {/* Warnings Tab */}
            {activeMainTab === 'warnings' && (
              <div>
                {executionResult?.stderr ? (
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-sm font-medium text-gray-700">Warnings & Errors (stderr)</h4>
                      <button
                        onClick={() => copyToClipboard(executionResult.stderr, 'warnings')}
                        className="text-gray-400 hover:text-gray-600 flex items-center space-x-1"
                      >
                        {copiedId === 'warnings' ? (
                          <>
                            <Check className="h-4 w-4 text-green-500" />
                            <span className="text-xs text-green-500">Copied!</span>
                          </>
                        ) : (
                          <>
                            <Copy className="h-4 w-4" />
                            <span className="text-xs">Copy</span>
                          </>
                        )}
                      </button>
                    </div>
                    <pre className="text-xs bg-yellow-50 text-yellow-900 p-4 rounded border border-yellow-200 overflow-x-auto max-h-96 whitespace-pre-wrap font-mono">
                      {executionResult.stderr}
                    </pre>
                  </div>
                ) : (
                  <div className="text-center py-12 text-gray-500">
                    <AlertTriangle className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                    <p>No warnings or errors for this cell</p>
                  </div>
                )}
              </div>
            )}

            {/* Data Tables Tab */}
            {activeMainTab === 'data' && (
              <div>
                {intermediaryTables.length > 0 ? (
                  <div className="space-y-4">
                    <p className="text-xs text-gray-600 mb-3">
                      Intermediate DataFrames created during code execution
                    </p>
                    {intermediaryTables.map((table: any, index: number) => (
                      <div key={index} className="border border-gray-200 rounded-lg overflow-hidden">
                        <div className="bg-gray-50 px-3 py-2 border-b border-gray-200">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium text-gray-900">{table.name}</span>
                            <span className="text-xs text-gray-500">
                              {table.shape[0]} rows × {table.shape[1]} columns
                            </span>
                          </div>
                        </div>
                        <div className="overflow-x-auto max-h-64">
                          <table className="min-w-full text-xs">
                            <thead className="bg-gray-50 sticky top-0">
                              <tr>
                                {table.columns.map((col: string, colIndex: number) => (
                                  <th
                                    key={colIndex}
                                    className="px-3 py-2 text-left font-medium text-gray-700 border-r border-gray-200 last:border-r-0"
                                  >
                                    {col}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200">
                              {table.data.slice(0, 10).map((row: any, rowIndex: number) => (
                                <tr key={rowIndex} className="hover:bg-gray-50">
                                  {table.columns.map((col: string, colIndex: number) => (
                                    <td
                                      key={colIndex}
                                      className="px-3 py-2 text-gray-900 border-r border-gray-100 last:border-r-0 font-mono"
                                    >
                                      {row[col] !== null && row[col] !== undefined ? String(row[col]) : '-'}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                          {table.data.length > 10 && (
                            <div className="bg-gray-50 px-3 py-2 text-xs text-gray-500 text-center border-t">
                              Showing 10 of {table.data.length} rows
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12 text-gray-500">
                    <TableIcon className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                    <p>No intermediate data tables for this cell</p>
                  </div>
                )}
              </div>
            )}

            {/* Variables Tab */}
            {activeMainTab === 'variables' && (
              <div>
                {loadingVariables ? (
                  <div className="text-center py-12 text-gray-500">
                    <Database className="h-12 w-12 mx-auto mb-3 text-gray-300 animate-pulse" />
                    <p>Loading variables...</p>
                  </div>
                ) : Object.keys(variables).length > 0 ? (
                  <div className="space-y-6">
                    <p className="text-xs text-gray-600 mb-3">
                      All variables available at this cell execution. Click on a variable to see details.
                    </p>

                    {/* DataFrames Section */}
                    {Object.entries(variables).some(([_, info]) => info.includes('DataFrame')) && (
                      <div>
                        <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                          <TableIcon className="h-4 w-4 mr-2" />
                          DataFrames
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {Object.entries(variables)
                            .filter(([_, info]) => info.includes('DataFrame'))
                            .map(([name, info]) => (
                              <div
                                key={name}
                                className="inline-flex items-center px-3 py-2 rounded-lg bg-blue-50 border border-blue-200 hover:bg-blue-100 cursor-pointer transition-colors"
                                title={info}
                              >
                                <span className="font-mono text-sm font-medium text-blue-900">{name}</span>
                                <span className="ml-2 text-xs text-blue-600">
                                  {info.split(' ').slice(1).join(' ')}
                                </span>
                              </div>
                            ))}
                        </div>
                      </div>
                    )}

                    {/* Arrays Section */}
                    {Object.entries(variables).some(([_, info]) => info.includes('ndarray') || info.includes('Series')) && (
                      <div>
                        <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                          <Zap className="h-4 w-4 mr-2" />
                          Arrays & Series
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {Object.entries(variables)
                            .filter(([_, info]) => info.includes('ndarray') || info.includes('Series'))
                            .map(([name, info]) => (
                              <div
                                key={name}
                                className="inline-flex items-center px-3 py-2 rounded-lg bg-purple-50 border border-purple-200 hover:bg-purple-100 cursor-pointer transition-colors"
                                title={info}
                              >
                                <span className="font-mono text-sm font-medium text-purple-900">{name}</span>
                                <span className="ml-2 text-xs text-purple-600">{info.split(' ').slice(1).join(' ')}</span>
                              </div>
                            ))}
                        </div>
                      </div>
                    )}

                    {/* Other Variables Section */}
                    {Object.entries(variables).some(([_, info]) => !info.includes('DataFrame') && !info.includes('ndarray') && !info.includes('Series')) && (
                      <div>
                        <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                          <Database className="h-4 w-4 mr-2" />
                          Other Variables
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {Object.entries(variables)
                            .filter(([_, info]) => !info.includes('DataFrame') && !info.includes('ndarray') && !info.includes('Series'))
                            .map(([name, info]) => (
                              <div
                                key={name}
                                className="inline-flex items-center px-3 py-2 rounded-lg bg-gray-50 border border-gray-200 hover:bg-gray-100 cursor-pointer transition-colors"
                                title={info}
                              >
                                <span className="font-mono text-sm font-medium text-gray-900">{name}</span>
                                <span className="ml-2 text-xs text-gray-600">{info}</span>
                              </div>
                            ))}
                        </div>
                      </div>
                    )}

                    <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                      <p className="text-xs text-yellow-800">
                        <strong>💡 Tip:</strong> DataFrame info shows column names. Use the exact column names shown when accessing DataFrame columns in your code.
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-12 text-gray-500">
                    <Database className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                    <p>No variables available at this cell</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex justify-between items-center">
            <p className="text-xs text-gray-500">
              Technical details for transparency - main results shown in article view
            </p>
            {traces.length > 0 && (
              <button
                onClick={exportTraces}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                <Download className="h-4 w-4 mr-2" />
                Export Traces
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default ExecutionDetailsModal
