import React, { useState, useEffect } from 'react'
import { Settings, Activity, AlertCircle } from 'lucide-react'
import { llmAPI } from '../services/api'

interface LLMStatusFooterProps {
  onSettingsClick?: () => void
  notebookId?: string  // Add notebook ID prop for context tracking
}

const LLMStatusFooter: React.FC<LLMStatusFooterProps> = ({ onSettingsClick, notebookId }) => {
  const [status, setStatus] = useState<{
    provider: string
    model: string
    status: string
    max_tokens: number | null
    max_input_tokens: number | null
    max_output_tokens: number | null
    error_message?: string
    active_context_tokens?: number | null
  } | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchStatus = async () => {
    try:
      const statusData = await llmAPI.getStatus(notebookId)
      setStatus(statusData)
      setLoading(false)
    } catch (error) {
      console.error('Failed to fetch LLM status:', error)
      setStatus({
        provider: 'unknown',
        model: 'unknown',
        status: 'error',
        max_tokens: null,
        max_input_tokens: null,
        max_output_tokens: null,
        error_message: 'Failed to connect',
        active_context_tokens: null
      })
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
    // Refresh status every 10 seconds (faster for context updates)
    const interval = setInterval(fetchStatus, 10000)
    return () => clearInterval(interval)
  }, [notebookId])  // Re-fetch when notebook changes

  const formatTokens = (tokens: number | null): string => {
    if (tokens === null) return '?'
    if (tokens >= 1000000) return `${(tokens / 1000000).toFixed(1)}M`
    if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}k`
    return tokens.toString()
  }

  const getProviderDisplayName = (provider: string): string => {
    const displayNames: Record<string, string> = {
      'lmstudio': 'LM Studio',
      'ollama': 'Ollama',
      'openai': 'OpenAI',
      'anthropic': 'Anthropic',
      'mlx': 'MLX',
      'huggingface': 'HuggingFace'
    }
    return displayNames[provider] || provider
  }

  const getStatusColor = (statusType: string): string => {
    switch (statusType) {
      case 'connected':
        return 'text-green-600'
      case 'error':
        return 'text-red-600'
      default:
        return 'text-gray-600'
    }
  }

  const getStatusIcon = () => {
    if (loading) return <Activity className="h-3.5 w-3.5 animate-spin" />
    if (status?.status === 'error') return <AlertCircle className="h-3.5 w-3.5" />
    return <Activity className="h-3.5 w-3.5" />
  }

  const getContextUsageColor = (): string => {
    if (!status?.active_context_tokens || !status?.max_tokens) return 'text-blue-600'
    const percentage = (status.active_context_tokens / status.max_tokens) * 100
    if (percentage > 80) return 'text-red-600'
    if (percentage > 60) return 'text-orange-600'
    return 'text-green-600'
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-gray-50 border-t border-gray-200 shadow-lg z-40">
      <div className="container mx-auto px-4 py-2">
        <div className="flex items-center justify-between">
          {/* Left: Status Info */}
          <div className="flex items-center space-x-4 text-xs">
            <div className={`flex items-center space-x-1.5 ${getStatusColor(status?.status || 'unknown')}`}>
              {getStatusIcon()}
              <span className="font-medium">
                {loading ? 'Loading...' : status?.status === 'connected' ? 'Connected' : 'Error'}
              </span>
            </div>

            {!loading && status && (
              <>
                <div className="text-gray-400">|</div>
                <div className="flex items-center space-x-1.5">
                  <span className="text-gray-500">Provider:</span>
                  <span className="font-semibold text-gray-700">
                    {getProviderDisplayName(status.provider)}
                  </span>
                </div>

                <div className="text-gray-400">|</div>
                <div className="flex items-center space-x-1.5">
                  <span className="text-gray-500">Model:</span>
                  <span className="font-semibold text-gray-700">
                    {status.model}
                  </span>
                </div>

                {status.max_tokens && (
                  <>
                    <div className="text-gray-400">|</div>
                    <div className="flex items-center space-x-1.5">
                      <span className="text-gray-500">Context:</span>
                      {status.active_context_tokens !== null && status.active_context_tokens !== undefined ? (
                        <span className={`font-semibold ${getContextUsageColor()}`}>
                          {formatTokens(status.active_context_tokens)} / {formatTokens(status.max_tokens)}
                        </span>
                      ) : (
                        <span className="font-semibold text-blue-600">
                          {formatTokens(status.max_tokens)}
                        </span>
                      )}
                      {status.max_output_tokens && (
                        <span className="text-gray-500 text-xs">
                          (out: {formatTokens(status.max_output_tokens)})
                        </span>
                      )}
                    </div>
                  </>
                )}

                {status.error_message && (
                  <>
                    <div className="text-gray-400">|</div>
                    <div className="text-red-600 text-xs">
                      {status.error_message}
                    </div>
                  </>
                )}
              </>
            )}
          </div>

          {/* Right: Settings Button */}
          <button
            onClick={onSettingsClick}
            className="flex items-center space-x-1.5 px-3 py-1 text-xs text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
            title="LLM Settings"
          >
            <Settings className="h-3.5 w-3.5" />
            <span>Settings</span>
          </button>
        </div>
      </div>
    </div>
  )
}

export default LLMStatusFooter
