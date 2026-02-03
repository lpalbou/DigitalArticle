import React, { useState, useEffect, useCallback, useRef } from 'react'
import {
  X, AlertCircle, CheckCircle, Loader, HelpCircle, Shuffle,
  Download, Settings2, Beaker, ChevronDown, ChevronUp, Eye, EyeOff,
  Users, ClipboardCheck, Trash2, Zap
} from 'lucide-react'
import axios from 'axios'
import { useToaster } from '../contexts/ToasterContext'
import { useModelDownload } from '../contexts/ModelDownloadContext'
import PersonaTab, { PersonaTabRef } from './PersonaTab'
import ReviewSettingsTab, { ReviewSettingsTabRef } from './ReviewSettingsTab'

interface Provider {
  name: string
  display_name: string
  available: boolean
  error?: string
  default_model?: string
  models: string[]
}

interface UserSettings {
  llm: {
    provider: string
    model: string
    temperature: number
    base_urls: Record<string, string>
    api_keys: Record<string, string>
  }
  reproducibility: {
    use_llm_seed: boolean
    llm_seed: number | null
    use_code_seed: boolean
    code_seed: number | null
  }
  execution: {
    logic_validation_enabled: boolean
    max_logic_corrections: number
    medium_retry_max_corrections: number
    low_retry_max_corrections: number
  }
  version: number
}

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
  notebookId?: string  // Current notebook ID, if any
}

type TabId = 'personas' | 'provider' | 'reproducibility' | 'execution' | 'review'

const DEFAULT_BASE_URLS: Record<string, string> = {
  ollama: 'http://localhost:11434',
  lmstudio: 'http://localhost:1234/v1',
  vllm: 'http://localhost:8000/v1',
  'openai-compatible': 'http://localhost:8080/v1',
  openai: '',
  anthropic: '',
}

const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose, notebookId }) => {
  const toaster = useToaster()
  const { downloadProgress, isDownloading, startDownload, cancelDownload } = useModelDownload()

  // Refs for tab save functions
  const personaTabRef = useRef<PersonaTabRef>(null)
  const reviewTabRef = useRef<ReviewSettingsTabRef>(null)

  const [activeTab, setActiveTab] = useState<TabId>('personas')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  
  // Provider data
  const [providers, setProviders] = useState<Provider[]>([])
  const [selectedProvider, setSelectedProvider] = useState<string>('')
  const [selectedModel, setSelectedModel] = useState<string>('')
  
  // Settings state
  const [temperature, setTemperature] = useState(0.7)
  const [baseUrls, setBaseUrls] = useState<Record<string, string>>(DEFAULT_BASE_URLS)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const baseUrlsRef = useRef<Record<string, string>>(baseUrls)

  useEffect(() => {
    baseUrlsRef.current = baseUrls
  }, [baseUrls])
  
  // API Keys (only for display, actual values are masked)
  const [apiKeySet, setApiKeySet] = useState<Record<string, boolean>>({
    openai: false,
    anthropic: false,
    huggingface: false,
  })
  const [newApiKey, setNewApiKey] = useState<Record<string, string>>({
    openai: '',
    anthropic: '',
    huggingface: '',
  })
  const [showApiKey, setShowApiKey] = useState<Record<string, boolean>>({
    openai: false,
    anthropic: false,
    huggingface: false,
  })
  
  // Model download
  const [modelToDownload, setModelToDownload] = useState('')
  const [hfModelToDownload, setHfModelToDownload] = useState('')
  const [hfAuthToken, setHfAuthToken] = useState('')
  const [mlxModelToDownload, setMlxModelToDownload] = useState('')

  // Model list loading
  const [loadingModels, setLoadingModels] = useState(false)
  const [currentProviderModels, setCurrentProviderModels] = useState<string[]>([])
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false)

  // Reproducibility
  const [useLlmSeed, setUseLlmSeed] = useState(true)
  const [llmSeed, setLlmSeed] = useState<string>('')
  const [useCodeSeed, setUseCodeSeed] = useState(true)
  const [codeSeed, setCodeSeed] = useState<string>('')

  // Execution / Quality
  const [logicValidationEnabled, setLogicValidationEnabled] = useState(true)
  const [maxLogicCorrections, setMaxLogicCorrections] = useState(2)
  const [mediumRetryMaxCorrections, setMediumRetryMaxCorrections] = useState(0)
  const [lowRetryMaxCorrections, setLowRetryMaxCorrections] = useState(0)

  const refreshProviders = async () => {
    try {
      // Re-fetch provider list (no cache - AbstractCore queries fresh)
      const providersRes = await axios.get<Provider[]>('/api/llm/providers')
      setProviders(providersRes.data)

      // If selected provider is no longer available, clear selection
      if (selectedProvider && !providersRes.data.find(p => p.name === selectedProvider)) {
        setSelectedProvider('')
        setSelectedModel('')
        setCurrentProviderModels([])
      }
    } catch (error) {
      console.error('Failed to refresh providers:', error)
    }
  }

  const fetchModelsForProvider = useCallback(async (provider: string, baseUrl?: string) => {
    setLoadingModels(true)
    try {
      // ============ DEBUG START - REMOVE AFTER TESTING ============
      console.log('🔍 [DEBUG] fetchModelsForProvider called:', {
        provider,
        baseUrl,
        baseUrlType: typeof baseUrl,
        baseUrlLength: baseUrl?.length,
        baseUrlTrimmed: baseUrl?.trim(),
        timestamp: new Date().toISOString()
      })
      // ============ DEBUG END ============

      const params = new URLSearchParams()
      if (baseUrl) {
        params.append('base_url', baseUrl)
      }

      const url = `/api/llm/providers/${provider}/models${params.toString() ? '?' + params.toString() : ''}`

      // ============ DEBUG START - REMOVE AFTER TESTING ============
      console.log('🌐 [DEBUG] API request:', {
        fullUrl: url,
        paramsString: params.toString(),
        decodedParams: decodeURIComponent(params.toString()),
        timestamp: new Date().toISOString()
      })
      // ============ DEBUG END ============

      const response = await axios.get(url)

      // ============ DEBUG START - REMOVE AFTER TESTING ============
      console.log('✅ [DEBUG] API response:', {
        provider,
        available: response.data.available,
        count: response.data.count,
        modelsLength: response.data.models?.length || 0,
        firstFiveModels: response.data.models?.slice(0, 5),
        rawResponse: response.data,
        timestamp: new Date().toISOString()
      })

      // CRITICAL CHECK: If available=true but 0 models, something is wrong!
      if (response.data.available === true && response.data.count === 0) {
        console.error('🚨 [DEBUG] CRITICAL: available=true but 0 models returned!', {
          provider,
          baseUrl,
          response: response.data
        })
      }
      // ============ DEBUG END ============

      console.log(`[fetchModels] ${provider}:`, {
        available: response.data.available,
        count: response.data.count,
        models: response.data.models?.length || 0,
        firstModel: response.data.models?.[0]
      })

      setCurrentProviderModels(response.data.models || [])
      console.log('[fetchModels] State updated, currentProviderModels length:', response.data.models?.length || 0)

      // If connection failed (custom base URL), update provider availability
      if (response.data.available === false) {
        // Remove provider from list if connection failed with custom URL
        if (baseUrl) {
          setProviders(prev => prev.filter(p => p.name !== provider))
          toaster.error(`Cannot connect to ${provider} at ${baseUrl}`)
        }
      } else if (response.data.available === true && baseUrl) {
        // Connection succeeded with custom URL - ensure provider is in list
        const providerExists = providers.find(p => p.name === provider)
        if (!providerExists) {
          // Add provider to list (connection now works)
          const newProvider = {
            name: provider,
            display_name: provider.charAt(0).toUpperCase() + provider.slice(1),
            available: true,
            default_model: response.data.models[0] || '',
            models: []
          }
          setProviders(prev => [...prev, newProvider])
          toaster.success(`Connected to ${provider} at ${baseUrl}`)
        }
      }

      // Auto-select first model if none selected
      if (response.data.models && response.data.models.length > 0 && !selectedModel) {
        setSelectedModel(response.data.models[0])
      }
    } catch (error) {
      console.error(`Failed to fetch models for ${provider}:`, error)
      setCurrentProviderModels([])
      toaster.error(`Connection failed: ${error}`)
    } finally {
      setLoadingModels(false)
    }
  }, [providers, selectedModel, toaster])

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      // Load providers and settings in parallel (providers without models - fast)
      const [providersRes, settingsRes] = await Promise.all([
        axios.get<Provider[]>('/api/llm/providers'),
        axios.get<UserSettings>('/api/settings'),
      ])

      setProviders(providersRes.data)

      const settings = settingsRes.data
      setSelectedProvider(settings.llm.provider)
      setSelectedModel(settings.llm.model)
      setTemperature(settings.llm.temperature)
      setBaseUrls({ ...DEFAULT_BASE_URLS, ...settings.llm.base_urls })

      // Check which API keys are set
      setApiKeySet({
        openai: settings.llm.api_keys.openai === '***SET***',
        anthropic: settings.llm.api_keys.anthropic === '***SET***',
        huggingface: settings.llm.api_keys.huggingface === '***SET***',
      })

      // Reproducibility
      setUseLlmSeed(settings.reproducibility.use_llm_seed)
      setLlmSeed(settings.reproducibility.llm_seed?.toString() || '')
      setUseCodeSeed(settings.reproducibility.use_code_seed)
      setCodeSeed(settings.reproducibility.code_seed?.toString() || '')

      // Execution / Quality
      setLogicValidationEnabled(settings.execution?.logic_validation_enabled ?? true)
      setMaxLogicCorrections(settings.execution?.max_logic_corrections ?? 2)
      setMediumRetryMaxCorrections(settings.execution?.medium_retry_max_corrections ?? 0)
      setLowRetryMaxCorrections(settings.execution?.low_retry_max_corrections ?? 0)

      // Models will be fetched by useEffect when provider is set

    } catch (error) {
      console.error('Failed to load settings:', error)
      toaster.error('Failed to load settings')
    } finally {
      setLoading(false)
    }
  }, [toaster])

  // Load settings and providers on open
  useEffect(() => {
    if (isOpen) {
      loadData()
    }
  }, [isOpen, loadData])

  // Fetch models when provider changes
  useEffect(() => {
    if (selectedProvider && isOpen) {
      fetchModelsForProvider(selectedProvider, baseUrlsRef.current[selectedProvider])
    }
  }, [selectedProvider, isOpen, fetchModelsForProvider])
  // Note: baseUrls changes do not auto-trigger model refresh; use Update button.

  // Listen for model download completion to refresh model list
  useEffect(() => {
    const handleModelDownloadComplete = (e: any) => {
      const { provider } = e.detail
      // Refresh only if it's for the currently selected provider
      if (provider === selectedProvider) {
        fetchModelsForProvider(provider, baseUrlsRef.current[provider])
      }
    }

    window.addEventListener('model-download-complete', handleModelDownloadComplete)
    return () => {
      window.removeEventListener('model-download-complete', handleModelDownloadComplete)
    }
  }, [selectedProvider, fetchModelsForProvider])

  const handleProviderChange = (providerName: string) => {
    setSelectedProvider(providerName)
    const provider = providers.find(p => p.name === providerName)
    if (provider && provider.models.length > 0) {
      setSelectedModel(provider.default_model || provider.models[0])
    }
  }

  const generateRandomSeed = (setter: React.Dispatch<React.SetStateAction<string>>) => {
    const seed = Math.floor(Math.random() * 2147483647)
    setter(seed.toString())
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      // Call the appropriate tab's save function based on active tab
      if (activeTab === 'personas' && personaTabRef.current) {
        await personaTabRef.current.save()
        // Fire custom event to notify badge to refresh
        window.dispatchEvent(new CustomEvent('persona-updated'))
        onClose()
      } else if (activeTab === 'review' && reviewTabRef.current) {
        await reviewTabRef.current.save()
        toaster.success('Review settings saved successfully')
        onClose()
      } else if (activeTab === 'execution') {
        // Save execution / quality settings
        await axios.put('/api/settings', {
          execution: {
            logic_validation_enabled: logicValidationEnabled,
            max_logic_corrections: maxLogicCorrections,
            medium_retry_max_corrections: mediumRetryMaxCorrections,
            low_retry_max_corrections: lowRetryMaxCorrections,
          },
        })

        toaster.success('Execution settings saved successfully')
        onClose()
      } else if (activeTab === 'provider' || activeTab === 'reproducibility') {
        // Save provider and reproducibility settings
        await axios.put('/api/settings', {
          llm: {
            provider: selectedProvider,
            model: selectedModel,
            temperature,
            base_urls: baseUrls,
          },
          reproducibility: {
            use_llm_seed: useLlmSeed,
            llm_seed: useLlmSeed && llmSeed ? parseInt(llmSeed) : null,
            use_code_seed: useCodeSeed,
            code_seed: useCodeSeed && codeSeed ? parseInt(codeSeed) : null,
          },
        })

        // Also update the global LLM provider selection
        await axios.post('/api/llm/providers/select', {
          provider: selectedProvider,
          model: selectedModel,
          notebook_id: notebookId,
        })

        // Trigger footer refresh
        window.dispatchEvent(new CustomEvent('llm-settings-updated'))

        toaster.success('Settings saved successfully')
        onClose()
      }
    } catch (error: any) {
      toaster.error(error.response?.data?.detail || 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveApiKey = async (provider: string) => {
    const key = newApiKey[provider]
    if (!key) return

    try {
      await axios.put('/api/settings/api-key', {
        provider,
        api_key: key,
      })

      setApiKeySet(prev => ({ ...prev, [provider]: true }))
      setNewApiKey(prev => ({ ...prev, [provider]: '' }))
      toaster.success(`${provider} API key saved`)

      // Refresh provider list - the provider might now be available
      await refreshProviders()

      // If this is the selected provider, fetch its models
      if (provider === selectedProvider) {
        await fetchModelsForProvider(provider, baseUrls[provider])
      }

    } catch (error: any) {
      toaster.error(error.response?.data?.detail || `Failed to save ${provider} API key`)
    }
  }

  const handleDeleteApiKey = async (provider: string) => {
    try {
      await axios.delete(`/api/settings/api-key/${provider}`)
      setApiKeySet(prev => ({ ...prev, [provider]: false }))
      toaster.info(`${provider} API key removed`)

      // Refresh provider list - the provider might disappear
      await refreshProviders()

      // If this was the selected provider, clear selection
      if (provider === selectedProvider) {
        setSelectedProvider('')
        setSelectedModel('')
        setCurrentProviderModels([])
      }
    } catch (error: any) {
      toaster.error(`Failed to remove ${provider} API key`)
    }
  }

  const handleStartDownload = () => {
    if (!modelToDownload) return
    startDownload('ollama', modelToDownload)
  }

  const handleStartHfDownload = () => {
    if (!hfModelToDownload) return
    // Use auth token if provided, otherwise will fall back to env var on backend
    startDownload('huggingface', hfModelToDownload, hfAuthToken || undefined)
  }

  const handleStartMlxDownload = () => {
    if (!mlxModelToDownload) return
    startDownload('mlx', mlxModelToDownload)
  }

  const handleDeleteModel = async (modelName: string) => {
    if (!confirm(`Delete model "${modelName}"? This will free disk space.`)) return

    try {
      await axios.delete(`/api/models/ollama/${encodeURIComponent(modelName)}`)
      // Refresh model list
      await fetchModelsForProvider('ollama', baseUrls['ollama'])
      toaster.success(`Model ${modelName} deleted`)
    } catch (error: any) {
      toaster.error(`Failed to delete: ${error.response?.data?.detail || error.message}`)
    }
  }

  const availableProviders = providers.filter(p => p.available)
  const hasNoAvailableProviders = !loading && availableProviders.length === 0

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
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-[840px] sm:w-full">
          {/* Header */}
          <div className="bg-gray-50 px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">Settings</h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-500 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Tabs */}
          <div className="border-b border-gray-200">
            <nav className="flex -mb-px">
              <button
                onClick={() => setActiveTab('personas')}
                className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors flex items-center space-x-2 ${
                  activeTab === 'personas'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Users className="h-4 w-4" />
                <span>Persona</span>
              </button>
              <button
                onClick={() => setActiveTab('provider')}
                className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors flex items-center space-x-2 ${
                  activeTab === 'provider'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Settings2 className="h-4 w-4" />
                <span>Provider & Model</span>
              </button>
              <button
                onClick={() => setActiveTab('reproducibility')}
                className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors flex items-center space-x-2 ${
                  activeTab === 'reproducibility'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Beaker className="h-4 w-4" />
                <span>Reproducibility</span>
              </button>
              <button
                onClick={() => setActiveTab('execution')}
                className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors flex items-center space-x-2 ${
                  activeTab === 'execution'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Zap className="h-4 w-4" />
                <span>Execution</span>
              </button>
              <button
                onClick={() => setActiveTab('review')}
                className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors flex items-center space-x-2 ${
                  activeTab === 'review'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <ClipboardCheck className="h-4 w-4" />
                <span>Review</span>
              </button>
            </nav>
          </div>

          {/* Content */}
          <div className="bg-white px-6 py-6 max-h-[69vh] overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader className="h-8 w-8 animate-spin text-blue-600" />
                <span className="ml-3 text-gray-600">Loading settings...</span>
              </div>
            ) : (
              <>
                {/* Active Download Section - Shown regardless of selected tab/provider */}
                {downloadProgress.status !== 'idle' && downloadProgress.model && (
                  <div className="mb-6 bg-blue-50 border-2 border-blue-200 rounded-lg p-4">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        <Download className="h-5 w-5 text-blue-600" />
                        <div>
                          <h4 className="text-sm font-semibold text-blue-900">
                            Active Download
                          </h4>
                          <p className="text-xs text-blue-700 mt-0.5">
                            {downloadProgress.provider}: {downloadProgress.model}
                          </p>
                        </div>
                      </div>
                      {isDownloading && (
                        <button
                          onClick={cancelDownload}
                          className="px-3 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700"
                        >
                          Cancel
                        </button>
                      )}
                    </div>

                    <div className="mt-3">
                      <div className="flex justify-between text-xs text-blue-700 mb-1">
                        <span>{downloadProgress.message || 'Downloading...'}</span>
                        {downloadProgress.progress > 0 && (
                          <span>{downloadProgress.progress}%</span>
                        )}
                      </div>
                      <div className="w-full bg-blue-100 rounded-full h-2.5">
                        <div
                          className={`h-2.5 rounded-full transition-all ${
                            downloadProgress.status === 'error' ? 'bg-red-600' :
                            downloadProgress.status === 'complete' ? 'bg-green-600' : 'bg-blue-600'
                          }`}
                          style={{ width: `${downloadProgress.progress}%` }}
                        />
                      </div>
                      {downloadProgress.currentSize && downloadProgress.totalSize && (
                        <div className="text-xs text-blue-600 mt-1">
                          {downloadProgress.currentSize} / {downloadProgress.totalSize}
                        </div>
                      )}
                    </div>

                    <p className="text-xs text-blue-600 mt-3">
                      💡 You can close this window - download continues in background
                    </p>
                  </div>
                )}

                {/* Persona Tab */}
                {activeTab === 'personas' && (
                  <PersonaTab ref={personaTabRef} notebookId={notebookId} />
                )}

                {/* Provider & Model Tab */}
                {activeTab === 'provider' && (
                  <div className="space-y-6">
                {hasNoAvailableProviders ? (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                    <div className="flex items-start">
                      <AlertCircle className="h-6 w-6 text-red-600 flex-shrink-0 mt-0.5" />
                      <div className="ml-4">
                        <h4 className="text-base font-semibold text-red-900 mb-2">
                          No LLM Providers Available
                        </h4>
                        <p className="text-sm text-red-800">
                          Install Ollama or LM Studio locally, or configure an API key below.
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <>
                    {/* Provider Selection */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Provider
                      </label>
                      <select
                        value={selectedProvider}
                        onChange={(e) => handleProviderChange(e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      >
                        <option value="">Select a provider...</option>
                        {availableProviders.map((provider) => (
                          <option key={provider.name} value={provider.name}>
                            {provider.display_name}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Model Selection */}
                    {selectedProvider && (
                      <div className="relative">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Model {loadingModels && <span className="text-gray-500 text-xs ml-2">(loading...)</span>}
                        </label>

                        {/* Custom dropdown button */}
                        <button
                          type="button"
                          onClick={() => !loadingModels && setModelDropdownOpen(!modelDropdownOpen)}
                          disabled={loadingModels}
                          className="w-full px-4 py-2 border border-gray-300 rounded-md bg-white text-left flex items-center justify-between focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <span className="truncate">{selectedModel || (loadingModels ? 'Loading models...' : `Select a model... (${currentProviderModels.length} available)`)}</span>
                          <ChevronDown className={`h-4 w-4 transition-transform ${modelDropdownOpen ? 'rotate-180' : ''}`} />
                        </button>

                        {/* Dropdown menu */}
                        {modelDropdownOpen && !loadingModels && (
                          <div className="absolute z-10 mt-1 w-full bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto">
                            {currentProviderModels.length === 0 ? (
                              <div className="px-3 py-2 text-gray-500 text-sm">No models available</div>
                            ) : (
                              currentProviderModels.map((model) => (
                                <div
                                  key={model}
                                  className="flex items-center justify-between px-3 py-2 hover:bg-gray-100 cursor-pointer"
                                  onClick={() => {
                                    setSelectedModel(model)
                                    setModelDropdownOpen(false)
                                  }}
                                >
                                  <span className="flex-1 truncate">{model}</span>
                                  {selectedProvider === 'ollama' && (
                                    <Trash2
                                      className="h-4 w-4 text-red-400 hover:text-red-600 ml-2 flex-shrink-0"
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        handleDeleteModel(model)
                                        setModelDropdownOpen(false)
                                      }}
                                    />
                                  )}
                                </div>
                              ))
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Temperature */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Temperature: {temperature.toFixed(1)}
                      </label>
                      <input
                        type="range"
                        min="0"
                        max="2"
                        step="0.1"
                        value={temperature}
                        onChange={(e) => setTemperature(parseFloat(e.target.value))}
                        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                      />
                      <div className="flex justify-between text-xs text-gray-500 mt-1">
                        <span>Precise (0)</span>
                        <span>Creative (2)</span>
                      </div>
                    </div>
                  </>
                )}

                {/* Model Download (Ollama) */}
                {selectedProvider === 'ollama' && (
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                    <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                      <Download className="h-4 w-4 mr-2" />
                      Download Ollama Model
                    </h4>
                    <div className="flex space-x-2">
                      <input
                        type="text"
                        value={modelToDownload}
                        onChange={(e) => setModelToDownload(e.target.value)}
                        placeholder="e.g., llama3.2, qwen3:4b"
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm"
                        disabled={isDownloading}
                      />
                      <button
                        onClick={handleStartDownload}
                        disabled={!modelToDownload || isDownloading}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {isDownloading ? 'Downloading...' : 'Download'}
                      </button>
                    </div>
                    <p className="text-xs text-gray-500 mt-2">
                      Examples: llama3.2, qwen3:4b, gemma3:1b
                    </p>
                  </div>
                )}

                {/* Model Download (HuggingFace) */}
                {selectedProvider === 'huggingface' && (
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                    <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                      <Download className="h-4 w-4 mr-2" />
                      Download HuggingFace Model
                    </h4>
                    <div className="space-y-3">
                      <div className="flex space-x-2">
                        <input
                          type="text"
                          value={hfModelToDownload}
                          onChange={(e) => setHfModelToDownload(e.target.value)}
                          placeholder="e.g., meta-llama/Llama-2-7b-hf"
                          className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm"
                          disabled={isDownloading}
                        />
                        <button
                          onClick={handleStartHfDownload}
                          disabled={!hfModelToDownload || isDownloading}
                          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {isDownloading ? 'Downloading...' : 'Download'}
                        </button>
                      </div>

                      {/* Optional auth token for gated models */}
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">
                          Auth Token (optional, for gated models)
                        </label>
                        <input
                          type="password"
                          value={hfAuthToken}
                          onChange={(e) => setHfAuthToken(e.target.value)}
                          placeholder="hf_..."
                          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                          disabled={isDownloading}
                        />
                      </div>
                    </div>

                    <p className="text-xs text-gray-500 mt-3">
                      Downloads are cached in persistent volume. Progress shown above.
                    </p>
                  </div>
                )}

                {/* Model Download (MLX - Apple Silicon only) */}
                {selectedProvider === 'mlx' && (
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                    <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                      <Download className="h-4 w-4 mr-2" />
                      Download MLX Model
                    </h4>
                    <div className="flex space-x-2">
                      <input
                        type="text"
                        value={mlxModelToDownload}
                        onChange={(e) => setMlxModelToDownload(e.target.value)}
                        placeholder="e.g., mlx-community/Qwen3-4B-4bit"
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm"
                        disabled={isDownloading}
                      />
                      <button
                        onClick={handleStartMlxDownload}
                        disabled={!mlxModelToDownload || isDownloading}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {isDownloading ? 'Downloading...' : 'Download'}
                      </button>
                    </div>

                    <p className="text-xs text-gray-500 mt-3">
                      MLX models optimized for Apple Silicon. Not available in Docker. Progress shown above.
                    </p>
                  </div>
                )}

                {/* LMStudio Note */}
                {selectedProvider === 'lmstudio' && (
                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                    <h4 className="text-sm font-semibold text-amber-800 mb-2 flex items-center">
                      <HelpCircle className="h-4 w-4 mr-2" />
                      LMStudio Model Downloads
                    </h4>
                    <p className="text-xs text-amber-700">
                      LMStudio models must be downloaded using the LMStudio GUI or <code className="bg-amber-100 px-1 rounded">lms get</code> CLI 
                      on your host machine. Digital Article connects to LMStudio as an external server.
                    </p>
                  </div>
                )}

                {/* Advanced Settings (Base URLs) */}
                <div className="border border-gray-200 rounded-lg">
                  <button
                    onClick={() => setShowAdvanced(!showAdvanced)}
                    className="w-full px-4 py-3 flex items-center justify-between text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    <span>Advanced Settings</span>
                    {showAdvanced ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </button>
                  
                  {showAdvanced && (
                    <div className="px-4 pb-4 space-y-4 border-t border-gray-200 pt-4">
                      {/* Base URLs */}
                      <div className="space-y-3">
                        <h5 className="text-sm font-medium text-gray-700">Base URLs</h5>
                        {['ollama', 'lmstudio', 'vllm', 'openai-compatible', 'openai', 'anthropic'].map((provider) => (
                          <div key={provider}>
                            <label className="block text-xs text-gray-500 mb-1 capitalize">
                              {provider === 'openai-compatible' ? 'OpenAI-Compatible' : provider} {
                                provider === 'openai' || provider === 'anthropic' ? '(for Portkey/proxy)' : 
                                provider === 'lmstudio' ? '(e.g., http://localhost:1234/v1)' :
                                provider === 'vllm' ? '(GPU inference server)' :
                                provider === 'openai-compatible' ? '(any OpenAI-compatible API)' : ''
                              }
                            </label>
                            <div className="flex space-x-2">
                              <input
                                type="text"
                                value={baseUrls[provider] || ''}
                                onChange={(e) => setBaseUrls(prev => ({ ...prev, [provider]: e.target.value }))}
                                placeholder={
                                  provider === 'lmstudio' ? 'http://localhost:1234/v1' : 
                                  provider === 'vllm' ? 'http://localhost:8000/v1' :
                                  provider === 'openai-compatible' ? 'http://localhost:8080/v1' :
                                  DEFAULT_BASE_URLS[provider] || 'Leave empty for default'
                                }
                                className="flex-1 px-3 py-1.5 border border-gray-300 rounded text-sm"
                              />
                              {(provider === 'ollama' || provider === 'lmstudio' || provider === 'vllm' || provider === 'openai-compatible') && (
                                <button
                                  onClick={async () => {
                                    console.log('🔵 [DEBUG] Update button clicked:', {
                                      provider,
                                      baseUrl: baseUrls[provider],
                                      selectedProvider,
                                      willFetchModels: provider === selectedProvider,
                                      timestamp: new Date().toISOString()
                                    })

                                    // Refresh providers first (in case URL now connects)
                                    await refreshProviders()
                                    // Then fetch models with new URL (only if this is the selected provider)
                                    if (provider === selectedProvider) {
                                      await fetchModelsForProvider(provider, baseUrls[provider])
                                    }
                                  }}
                                  disabled={loadingModels}
                                  className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-1"
                                  title="Test connection and refresh provider list"
                                >
                                  {loadingModels ? (
                                    <Loader className="h-3 w-3 animate-spin" />
                                  ) : (
                                    <CheckCircle className="h-3 w-3" />
                                  )}
                                  <span>Update</span>
                                </button>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* API Keys */}
                      <div className="space-y-3 pt-4 border-t border-gray-100">
                        <h5 className="text-sm font-medium text-gray-700">API Keys</h5>
                        {['openai', 'anthropic', 'huggingface'].map((provider) => (
                          <div key={provider}>
                            <label className="block text-xs text-gray-500 mb-1 capitalize flex items-center justify-between">
                              <span>{provider}</span>
                              {apiKeySet[provider] && (
                                <span className="text-green-600 flex items-center">
                                  <CheckCircle className="h-3 w-3 mr-1" />
                                  Set
                                </span>
                              )}
                            </label>
                            <div className="flex space-x-2">
                              <div className="relative flex-1">
                                <input
                                  type={showApiKey[provider] ? 'text' : 'password'}
                                  value={newApiKey[provider]}
                                  onChange={(e) => setNewApiKey(prev => ({ ...prev, [provider]: e.target.value }))}
                                  placeholder={apiKeySet[provider] ? '••••••••' : 'Enter API key'}
                                  className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm pr-10"
                                />
                                <button
                                  type="button"
                                  onClick={() => setShowApiKey(prev => ({ ...prev, [provider]: !prev[provider] }))}
                                  className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                                >
                                  {showApiKey[provider] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                </button>
                              </div>
                              {newApiKey[provider] ? (
                                <button
                                  onClick={() => handleSaveApiKey(provider)}
                                  className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
                                >
                                  Save
                                </button>
                              ) : apiKeySet[provider] ? (
                                <button
                                  onClick={() => handleDeleteApiKey(provider)}
                                  className="px-3 py-1.5 bg-red-100 text-red-700 rounded text-sm hover:bg-red-200"
                                >
                                  Clear
                                </button>
                              ) : null}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

                {/* Reproducibility Tab */}
                {activeTab === 'reproducibility' && (
              <div className="space-y-6">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <p className="text-sm text-blue-800">
                    <strong>Reproducibility settings</strong> ensure your analyses produce consistent results. 
                    Seeds control random number generation for both LLM responses and code execution.
                  </p>
                </div>

                {/* LLM Seed */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <h4 className="text-sm font-medium text-gray-700">LLM Seed</h4>
                      <span title="Controls randomness in AI-generated code">
                        <HelpCircle className="h-4 w-4 text-gray-400" />
                      </span>
                    </div>
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={useLlmSeed}
                        onChange={(e) => setUseLlmSeed(e.target.checked)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="ml-2 text-sm text-gray-600">Enable</span>
                    </label>
                  </div>
                  
                  {useLlmSeed && (
                    <div className="flex space-x-2">
                      <input
                        type="number"
                        value={llmSeed}
                        onChange={(e) => setLlmSeed(e.target.value)}
                        placeholder="Enter seed (0-2147483647)"
                        min="0"
                        max="2147483647"
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm"
                      />
                      <button
                        onClick={() => generateRandomSeed(setLlmSeed)}
                        className="px-3 py-2 bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded-md flex items-center space-x-1"
                      >
                        <Shuffle className="h-4 w-4" />
                        <span className="text-sm">Random</span>
                      </button>
                    </div>
                  )}
                </div>

                {/* Code Execution Seed */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <h4 className="text-sm font-medium text-gray-700">Code Execution Seed</h4>
                      <span title="Controls randomness in executed Python code">
                        <HelpCircle className="h-4 w-4 text-gray-400" />
                      </span>
                    </div>
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={useCodeSeed}
                        onChange={(e) => setUseCodeSeed(e.target.checked)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="ml-2 text-sm text-gray-600">Enable</span>
                    </label>
                  </div>
                  
                  {useCodeSeed && (
                    <div className="flex space-x-2">
                      <input
                        type="number"
                        value={codeSeed}
                        onChange={(e) => setCodeSeed(e.target.value)}
                        placeholder="Enter seed (0-2147483647)"
                        min="0"
                        max="2147483647"
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm"
                      />
                      <button
                        onClick={() => generateRandomSeed(setCodeSeed)}
                        className="px-3 py-2 bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded-md flex items-center space-x-1"
                      >
                        <Shuffle className="h-4 w-4" />
                        <span className="text-sm">Random</span>
                      </button>
                    </div>
                  )}
                </div>

                {/* Info about seeds */}
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 space-y-2">
                  <h5 className="text-sm font-medium text-gray-700">How seeds work</h5>
                  <ul className="text-xs text-gray-600 space-y-1 list-disc list-inside">
                    <li><strong>Same seed</strong> = Same random numbers, reproducible results</li>
                    <li><strong>Different seed</strong> = Different random variations</li>
                    <li><strong>Disabled</strong> = Random seed each time (non-reproducible)</li>
                  </ul>
                </div>
              </div>
                )}

                {/* Execution / Quality Tab */}
                {activeTab === 'execution' && (
                  <div className="space-y-6">
                    <div className="bg-cyan-50 border border-cyan-200 rounded-lg p-4">
                      <p className="text-sm text-cyan-900">
                        <strong>Logic/Semantic validation</strong> runs after successful execution to catch
                        “code runs but the answer is wrong” (domain/statistical/methodology issues).
                        You can control which severities trigger automatic correction.
                      </p>
                      <p className="text-xs text-cyan-800 mt-2">
                        Default behavior: HIGH retries (bounded), MEDIUM/LOW are logged only (no auto-correction).
                      </p>
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <h4 className="text-sm font-medium text-gray-700">Enable Logic Validation</h4>
                        <span title="Runs a post-success semantic check and (optionally) corrects issues">
                          <HelpCircle className="h-4 w-4 text-gray-400" />
                        </span>
                      </div>
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={logicValidationEnabled}
                          onChange={(e) => setLogicValidationEnabled(e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        <span className="ml-2 text-sm text-gray-600">Enable</span>
                      </label>
                    </div>

                    {logicValidationEnabled && (
                      <div className="space-y-4">
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                            <div className="text-xs font-semibold text-gray-700 mb-1">HIGH</div>
                            <div className="text-xs text-gray-600">
                              Must retry (bounded by max corrections).
                            </div>
                          </div>
                          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                            <div className="text-xs font-semibold text-gray-700 mb-1">MEDIUM</div>
                            <div className="text-xs text-gray-600">
                              Retry only while corrections_done &lt; threshold.
                            </div>
                          </div>
                          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                            <div className="text-xs font-semibold text-gray-700 mb-1">LOW</div>
                            <div className="text-xs text-gray-600">
                              Usually ignored unless you explicitly enable retries.
                            </div>
                          </div>
                        </div>

                        <div className="space-y-2">
                          <label className="block text-sm font-medium text-gray-700">
                            Max logic corrections (HIGH severity budget): {maxLogicCorrections}
                          </label>
                          <input
                            type="range"
                            min="0"
                            max="5"
                            step="1"
                            value={maxLogicCorrections}
                            onChange={(e) => setMaxLogicCorrections(parseInt(e.target.value))}
                            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                          />
                          <div className="text-xs text-gray-500">
                            Note: Validation always runs once; this controls how many correction attempts are allowed.
                          </div>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              MEDIUM: retry while corrections_done &lt;
                            </label>
                            <input
                              type="number"
                              min="0"
                              max="5"
                              value={mediumRetryMaxCorrections}
                              onChange={(e) => setMediumRetryMaxCorrections(parseInt(e.target.value || '0'))}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                            />
                            <div className="text-xs text-gray-500 mt-1">
                              Set to 0 to never auto-correct MEDIUM issues.
                            </div>
                          </div>

                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              LOW: retry while corrections_done &lt;
                            </label>
                            <input
                              type="number"
                              min="0"
                              max="5"
                              value={lowRetryMaxCorrections}
                              onChange={(e) => setLowRetryMaxCorrections(parseInt(e.target.value || '0'))}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                            />
                            <div className="text-xs text-gray-500 mt-1">
                              Set to 0 to never auto-correct LOW issues.
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Review Tab */}
                {activeTab === 'review' && (
                  <ReviewSettingsTab ref={reviewTabRef} notebookId={notebookId} />
                )}
              </>
            )}
          </div>

          {/* Footer */}
          <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving || (activeTab === 'provider' && !selectedProvider && availableProviders.length > 0) || (activeTab === 'personas' && !notebookId) || (activeTab === 'review' && !notebookId)}
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-2"
            >
              {saving && <Loader className="h-4 w-4 animate-spin" />}
              <span>
                {saving ? 'Saving...' :
                  activeTab === 'personas' ? 'Save Persona Settings' :
                  activeTab === 'review' ? 'Save Review Settings' :
                  'Save Settings'}
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SettingsModal

