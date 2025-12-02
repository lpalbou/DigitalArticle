import React, { useState, useEffect } from 'react'
import { Activity, AlertCircle } from 'lucide-react'
import { llmAPI, systemAPI } from '../services/api'

interface LLMStatusFooterProps {
  notebookId?: string  // Add notebook ID prop for context tracking
}

const LLMStatusFooter: React.FC<LLMStatusFooterProps> = ({ notebookId }) => {
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
  const [version, setVersion] = useState<string>('...')

  const fetchStatus = async () => {
    try {
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

  const fetchVersion = async () => {
    try {
      const data = await systemAPI.getVersion()
      setVersion(data.version)
    } catch (error) {
      console.error('Failed to fetch version:', error)
      setVersion('?')
    }
  }

  useEffect(() => {
    fetchStatus()
    fetchVersion()  // Fetch version once on mount

    // Refresh status every 60 seconds (reasonable for health checks)
    const interval = setInterval(fetchStatus, 60000)

    // Listen for settings updates and refresh immediately
    const handleSettingsUpdate = () => {
      fetchStatus()
    }
    window.addEventListener('llm-settings-updated', handleSettingsUpdate)

    return () => {
      clearInterval(interval)
      window.removeEventListener('llm-settings-updated', handleSettingsUpdate)
    }
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

  const getStatusDot = () => {
    if (loading) {
      return <div className="h-2.5 w-2.5 rounded-full bg-yellow-500 animate-pulse" />
    }
    if (status?.status === 'connected') {
      return <div className="h-2.5 w-2.5 rounded-full bg-green-500" />
    }
    return <div className="h-2.5 w-2.5 rounded-full bg-red-500" />
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
          <div className="flex items-center space-x-3 text-xs">
            {/* Connection status dot */}
            {getStatusDot()}

            {!loading && status && (
              <>
                <div className="flex items-center space-x-1.5">
                  <span className="text-gray-500">Provider:</span>
                  <span className="font-semibold text-gray-700">
                    {getProviderDisplayName(status.provider)}
                  </span>
                </div>

                <div className="text-gray-400">|</div>
                <div className="flex items-center space-x-1.5">
                  <span className="font-semibold text-gray-700">
                    {status.model}
                  </span>
                  <span className="text-gray-400">|</span>
                  {status.active_context_tokens !== null && status.active_context_tokens !== undefined && status.active_context_tokens > 0 ? (
                    <span className={`font-medium ${getContextUsageColor()}`}>
                      {formatTokens(status.active_context_tokens)}{status.max_tokens ? ` / ${formatTokens(status.max_tokens)}` : ''}
                    </span>
                  ) : status.max_tokens ? (
                    <span className="font-medium text-blue-600">
                      0 / {formatTokens(status.max_tokens)}
                    </span>
                  ) : (
                    <span className="font-medium text-gray-500">
                      No tokens yet
                    </span>
                  )}
                </div>

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

          {/* Right: Version & Update Info */}
          <div className="flex items-center space-x-3 text-xs text-gray-500">
            <span>v{version}</span>
            <div className="text-gray-400">|</div>
            <span>Updated Dec 2025</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default LLMStatusFooter
