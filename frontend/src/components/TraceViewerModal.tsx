import React, { useState, useEffect } from 'react'
import {
  X,
  Activity,
  ChevronDown,
  ChevronRight,
  Clock,
  Cpu,
  AlertCircle,
  CheckCircle,
  Play,
  RefreshCw,
  Trash2
} from 'lucide-react'
import { traceAPI } from '../services/api'
import { FlowSummary, TraceEvent, TraceStatus } from '../types'

interface TraceViewerModalProps {
  isOpen: boolean
  onClose: () => void
  notebookId?: string
}

const TraceViewerModal: React.FC<TraceViewerModalProps> = ({
  isOpen,
  onClose,
  notebookId
}) => {
  const [flows, setFlows] = useState<FlowSummary[]>([])
  const [selectedFlow, setSelectedFlow] = useState<string | null>(null)
  const [flowEvents, setFlowEvents] = useState<TraceEvent[]>([])
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(false)
  const [loadingFlow, setLoadingFlow] = useState(false)
  const [sinceHours, setSinceHours] = useState(24)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'prompt' | 'system' | 'response' | 'execution'>('prompt')

  // Fetch flows on mount and when filters change
  useEffect(() => {
    if (isOpen) {
      fetchFlows()
    }
  }, [isOpen, notebookId, sinceHours])

  // Fetch flow details when a flow is selected
  useEffect(() => {
    if (selectedFlow) {
      fetchFlowDetails(selectedFlow)
    }
  }, [selectedFlow])

  const fetchFlows = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await traceAPI.listFlows({
        notebook_id: notebookId,
        since_hours: sinceHours,
        limit: 50
      })
      setFlows(data)
    } catch (err) {
      setError('Failed to load traces')
      console.error('Error fetching flows:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchFlowDetails = async (flowId: string) => {
    setLoadingFlow(true)
    try {
      const data = await traceAPI.getFlow(flowId)
      setFlowEvents(data.traces)
    } catch (err) {
      console.error('Error fetching flow details:', err)
    } finally {
      setLoadingFlow(false)
    }
  }

  const handleCleanup = async () => {
    if (!confirm('Remove trace files older than 30 days?')) return
    try {
      const result = await traceAPI.cleanup(30)
      alert(`Removed ${result.files_removed} old trace files`)
      fetchFlows()
    } catch (err) {
      console.error('Error cleaning up traces:', err)
    }
  }

  const toggleStep = (stepId: string) => {
    const newExpanded = new Set(expandedSteps)
    if (newExpanded.has(stepId)) {
      newExpanded.delete(stepId)
    } else {
      newExpanded.add(stepId)
    }
    setExpandedSteps(newExpanded)
  }

  const formatDuration = (ms?: number) => {
    if (!ms) return '-'
    if (ms < 1000) return `${Math.round(ms)}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${Math.round(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`
  }

  const formatTime = (isoString: string) => {
    const date = new Date(isoString)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

  const formatDate = (isoString: string) => {
    const date = new Date(isoString)
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
  }

  const getStatusIcon = (status: TraceStatus) => {
    switch (status) {
      case TraceStatus.SUCCESS:
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case TraceStatus.ERROR:
        return <AlertCircle className="h-4 w-4 text-red-500" />
      case TraceStatus.STARTED:
        return <Play className="h-4 w-4 text-blue-500" />
      default:
        return <Activity className="h-4 w-4 text-gray-400" />
    }
  }

  const getStepTypeLabel = (stepType: string) => {
    const labels: Record<string, string> = {
      llm_code_generation: 'Code Generation',
      llm_code_fix: 'Code Fix',
      llm_methodology: 'Methodology',
      llm_review: 'Review',
      llm_chat: 'Chat',
      llm_semantic_extraction: 'Semantic Extraction',
      llm_error_analysis: 'Error Analysis',
      code_execution: 'Execution',
      code_lint: 'Lint',
      code_autofix: 'Autofix',
      retry: 'Retry',
      logic_correction: 'Logic Correction'
    }
    return labels[stepType] || stepType
  }

  const getStepTypeColor = (stepType: string) => {
    if (stepType.startsWith('llm_')) return 'bg-purple-100 text-purple-700'
    if (stepType.startsWith('code_')) return 'bg-blue-100 text-blue-700'
    if (stepType === 'retry') return 'bg-amber-100 text-amber-700'
    return 'bg-gray-100 text-gray-700'
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      {/* Modal */}
      <div className="absolute inset-4 md:inset-8 lg:inset-12 bg-white rounded-xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-indigo-50 to-purple-50">
          <div className="flex items-center gap-3">
            <Activity className="h-6 w-6 text-indigo-600" />
            <h2 className="text-xl font-semibold text-gray-900">Trace Viewer</h2>
            <span className="text-sm text-gray-500">
              LLM & Execution Observability
            </span>
          </div>
          <div className="flex items-center gap-2">
            {/* Time filter */}
            <select
              value={sinceHours}
              onChange={(e) => setSinceHours(Number(e.target.value))}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            >
              <option value={1}>Last hour</option>
              <option value={6}>Last 6 hours</option>
              <option value={24}>Last 24 hours</option>
              <option value={168}>Last week</option>
            </select>

            <button
              onClick={fetchFlows}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
              title="Refresh"
            >
              <RefreshCw className="h-5 w-5" />
            </button>

            <button
              onClick={handleCleanup}
              className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg"
              title="Cleanup old traces"
            >
              <Trash2 className="h-5 w-5" />
            </button>

            <button
              onClick={onClose}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Flow list (left panel) */}
          <div className="w-80 border-r border-gray-200 overflow-y-auto bg-gray-50">
            <div className="p-3 border-b border-gray-200 bg-white sticky top-0">
              <h3 className="text-sm font-medium text-gray-700">
                Recent Operations ({flows.length})
              </h3>
            </div>

            {loading ? (
              <div className="p-8 text-center text-gray-500">
                <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2" />
                Loading traces...
              </div>
            ) : error ? (
              <div className="p-8 text-center text-red-500">
                <AlertCircle className="h-6 w-6 mx-auto mb-2" />
                {error}
              </div>
            ) : flows.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <Activity className="h-8 w-8 mx-auto mb-2 text-gray-300" />
                No traces found
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {flows.map((flow) => (
                  <button
                    key={flow.flow_id}
                    onClick={() => setSelectedFlow(flow.flow_id)}
                    className={`w-full text-left p-3 hover:bg-white transition-colors ${
                      selectedFlow === flow.flow_id ? 'bg-white border-l-4 border-indigo-500' : ''
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      {getStatusIcon(flow.status)}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-gray-900 truncate">
                            {flow.step_types.map(getStepTypeLabel).join(' → ')}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                          <span>{formatDate(flow.started_at)} {formatTime(flow.started_at)}</span>
                          {flow.total_duration_ms && (
                            <>
                              <span>•</span>
                              <span className="flex items-center gap-1">
                                <Clock className="h-3 w-3" />
                                {formatDuration(flow.total_duration_ms)}
                              </span>
                            </>
                          )}
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs text-gray-400">
                            {flow.step_count} step{flow.step_count !== 1 ? 's' : ''}
                          </span>
                          {flow.total_tokens && (
                            <>
                              <span className="text-xs text-gray-300">•</span>
                              <span className="text-xs text-gray-400 flex items-center gap-1">
                                <Cpu className="h-3 w-3" />
                                {flow.total_tokens.toLocaleString()} tokens
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Flow details (right panel) */}
          <div className="flex-1 overflow-y-auto">
            {!selectedFlow ? (
              <div className="h-full flex items-center justify-center text-gray-400">
                <div className="text-center">
                  <Activity className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                  <p>Select a trace to view details</p>
                </div>
              </div>
            ) : loadingFlow ? (
              <div className="h-full flex items-center justify-center text-gray-500">
                <RefreshCw className="h-6 w-6 animate-spin" />
              </div>
            ) : (
              <div className="p-4 space-y-3">
                {flowEvents.map((event, index) => (
                  <div
                    key={event.step_id}
                    className="bg-white border border-gray-200 rounded-lg overflow-hidden"
                  >
                    {/* Step header */}
                    <button
                      onClick={() => toggleStep(event.step_id)}
                      className="w-full flex items-center gap-3 p-3 hover:bg-gray-50 transition-colors"
                    >
                      {expandedSteps.has(event.step_id) ? (
                        <ChevronDown className="h-4 w-4 text-gray-400 flex-shrink-0" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-gray-400 flex-shrink-0" />
                      )}

                      <span className="text-sm text-gray-400 w-6">{index + 1}</span>

                      {getStatusIcon(event.status)}

                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${getStepTypeColor(event.step_type)}`}>
                        {getStepTypeLabel(event.step_type)}
                      </span>

                      <span className="flex-1 text-left text-sm text-gray-600 truncate">
                        {event.llm_model || event.exec_error_type || ''}
                      </span>

                      <div className="flex items-center gap-3 text-xs text-gray-400">
                        {event.llm_total_tokens && (
                          <span className="flex items-center gap-1">
                            <Cpu className="h-3 w-3" />
                            {event.llm_total_tokens.toLocaleString()}
                          </span>
                        )}
                        {event.duration_ms && (
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {formatDuration(event.duration_ms)}
                          </span>
                        )}
                        <span>{formatTime(event.started_at)}</span>
                      </div>
                    </button>

                    {/* Step details */}
                    {expandedSteps.has(event.step_id) && (
                      <div className="border-t border-gray-200">
                        {/* Tabs for LLM events */}
                        {event.step_type.startsWith('llm_') && (
                          <>
                            <div className="flex border-b border-gray-200 bg-gray-50">
                              {['prompt', 'system', 'response'].map((tab) => (
                                <button
                                  key={tab}
                                  onClick={() => setActiveTab(tab as typeof activeTab)}
                                  className={`px-4 py-2 text-sm font-medium ${
                                    activeTab === tab
                                      ? 'text-indigo-600 border-b-2 border-indigo-600 bg-white'
                                      : 'text-gray-500 hover:text-gray-700'
                                  }`}
                                >
                                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                                </button>
                              ))}
                            </div>

                            <div className="p-4 max-h-96 overflow-y-auto">
                              {activeTab === 'prompt' && (
                                <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono bg-gray-50 p-3 rounded">
                                  {event.llm_prompt || 'No prompt recorded'}
                                </pre>
                              )}
                              {activeTab === 'system' && (
                                <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono bg-gray-50 p-3 rounded">
                                  {event.llm_system_prompt || 'No system prompt recorded'}
                                </pre>
                              )}
                              {activeTab === 'response' && (
                                <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono bg-gray-50 p-3 rounded">
                                  {event.llm_response || 'No response recorded'}
                                </pre>
                              )}
                            </div>

                            {/* Token stats */}
                            <div className="px-4 py-2 bg-gray-50 border-t border-gray-100 flex items-center gap-4 text-xs text-gray-500">
                              {event.llm_provider && (
                                <span>Provider: <strong>{event.llm_provider}</strong></span>
                              )}
                              {event.llm_model && (
                                <span>Model: <strong>{event.llm_model}</strong></span>
                              )}
                              {event.llm_input_tokens && (
                                <span>Input: <strong>{event.llm_input_tokens.toLocaleString()}</strong></span>
                              )}
                              {event.llm_output_tokens && (
                                <span>Output: <strong>{event.llm_output_tokens.toLocaleString()}</strong></span>
                              )}
                              {event.llm_temperature !== undefined && (
                                <span>Temp: <strong>{event.llm_temperature}</strong></span>
                              )}
                            </div>
                          </>
                        )}

                        {/* Execution details */}
                        {event.step_type === 'code_execution' && (
                          <div className="p-4 space-y-3">
                            {event.exec_code && (
                              <div>
                                <h4 className="text-xs font-medium text-gray-500 mb-1">Code</h4>
                                <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono bg-gray-50 p-3 rounded max-h-48 overflow-y-auto">
                                  {event.exec_code}
                                </pre>
                              </div>
                            )}
                            {event.exec_stdout && (
                              <div>
                                <h4 className="text-xs font-medium text-gray-500 mb-1">Output</h4>
                                <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono bg-green-50 p-3 rounded max-h-32 overflow-y-auto">
                                  {event.exec_stdout}
                                </pre>
                              </div>
                            )}
                            {event.exec_error && (
                              <div>
                                <h4 className="text-xs font-medium text-red-500 mb-1">
                                  Error: {event.exec_error_type}
                                </h4>
                                <pre className="text-sm text-red-700 whitespace-pre-wrap font-mono bg-red-50 p-3 rounded">
                                  {event.exec_error}
                                </pre>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Error details for any step */}
                        {event.status === TraceStatus.ERROR && event.error_message && !event.exec_error && (
                          <div className="p-4">
                            <h4 className="text-xs font-medium text-red-500 mb-1">
                              Error: {event.error_type}
                            </h4>
                            <pre className="text-sm text-red-700 whitespace-pre-wrap font-mono bg-red-50 p-3 rounded">
                              {event.error_message}
                            </pre>
                          </div>
                        )}

                        {/* Metadata */}
                        {event.metadata && Object.keys(event.metadata).length > 0 && (
                          <div className="px-4 py-2 bg-gray-50 border-t border-gray-100">
                            <h4 className="text-xs font-medium text-gray-500 mb-1">Metadata</h4>
                            <pre className="text-xs text-gray-600 font-mono">
                              {JSON.stringify(event.metadata, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default TraceViewerModal
