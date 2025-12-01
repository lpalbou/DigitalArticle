import React, { useState, useEffect, useCallback } from 'react'
import { 
  X, AlertCircle, CheckCircle, Loader, HelpCircle, Shuffle, 
  Download, Settings2, Beaker, ChevronDown, ChevronUp, Eye, EyeOff
} from 'lucide-react'
import axios from 'axios'
import { useToaster } from '../contexts/ToasterContext'
import { useModelDownload } from '../contexts/ModelDownloadContext'

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
  version: number
}

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
}

type TabId = 'provider' | 'reproducibility'

const DEFAULT_BASE_URLS: Record<string, string> = {
  ollama: 'http://localhost:11434',
  lmstudio: 'http://localhost:1234/v1',
  openai: '',
  anthropic: '',
}

const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const toaster = useToaster()
  const { downloadProgress, isDownloading, startDownload, cancelDownload } = useModelDownload()
  
  const [activeTab, setActiveTab] = useState<TabId>('provider')
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
  
  // Reproducibility
  const [useLlmSeed, setUseLlmSeed] = useState(true)
  const [llmSeed, setLlmSeed] = useState<string>('')
  const [useCodeSeed, setUseCodeSeed] = useState(true)
  const [codeSeed, setCodeSeed] = useState<string>('')

  // Load settings and providers on open
  useEffect(() => {
    if (isOpen) {
      loadData()
    }
  }, [isOpen])

  const loadData = async () => {
    setLoading(true)
    try {
      // Load providers and settings in parallel
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
      
    } catch (error) {
      console.error('Failed to load settings:', error)
      toaster.error('Failed to load settings')
    } finally {
      setLoading(false)
    }
  }

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
      // Save settings
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
      })

      // Trigger footer refresh
      window.dispatchEvent(new CustomEvent('llm-settings-updated'))

      toaster.success('Settings saved successfully')
      onClose()
      
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
      
    } catch (error: any) {
      toaster.error(error.response?.data?.detail || `Failed to save ${provider} API key`)
    }
  }

  const handleDeleteApiKey = async (provider: string) => {
    try {
      await axios.delete(`/api/settings/api-key/${provider}`)
      setApiKeySet(prev => ({ ...prev, [provider]: false }))
      toaster.info(`${provider} API key removed`)
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

  const currentProvider = providers.find(p => p.name === selectedProvider)
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
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-2xl sm:w-full">
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
            </nav>
          </div>

          {/* Content */}
          <div className="bg-white px-6 py-6 max-h-[60vh] overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader className="h-8 w-8 animate-spin text-blue-600" />
                <span className="ml-3 text-gray-600">Loading settings...</span>
              </div>
            ) : activeTab === 'provider' ? (
              /* Provider & Model Tab */
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
                    {selectedProvider && currentProvider && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Model
                        </label>
                        <select
                          value={selectedModel}
                          onChange={(e) => setSelectedModel(e.target.value)}
                          className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        >
                          <option value="">Select a model...</option>
                          {currentProvider.models.map((model) => (
                            <option key={model} value={model}>
                              {model}
                            </option>
                          ))}
                        </select>
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
                      {isDownloading ? (
                        <button
                          onClick={cancelDownload}
                          className="px-4 py-2 bg-red-600 text-white rounded-md text-sm hover:bg-red-700"
                        >
                          Cancel
                        </button>
                      ) : (
                        <button
                          onClick={handleStartDownload}
                          disabled={!modelToDownload}
                          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50"
                        >
                          Download
                        </button>
                      )}
                    </div>
                    
                    {/* Download Progress */}
                    {downloadProgress.status !== 'idle' && (
                      <div className="mt-3">
                        <div className="flex justify-between text-xs text-gray-600 mb-1">
                          <span>{downloadProgress.message || 'Downloading...'}</span>
                          {downloadProgress.progress > 0 && (
                            <span>{downloadProgress.progress}%</span>
                          )}
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full transition-all ${
                              downloadProgress.status === 'error' ? 'bg-red-600' :
                              downloadProgress.status === 'complete' ? 'bg-green-600' : 'bg-blue-600'
                            }`}
                            style={{ width: `${downloadProgress.progress}%` }}
                          />
                        </div>
                        {downloadProgress.currentSize && downloadProgress.totalSize && (
                          <div className="text-xs text-gray-500 mt-1">
                            {downloadProgress.currentSize} / {downloadProgress.totalSize}
                          </div>
                        )}
                      </div>
                    )}
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
                        {isDownloading ? (
                          <button
                            onClick={cancelDownload}
                            className="px-4 py-2 bg-red-600 text-white rounded-md text-sm hover:bg-red-700"
                          >
                            Cancel
                          </button>
                        ) : (
                          <button
                            onClick={handleStartHfDownload}
                            disabled={!hfModelToDownload}
                            className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50"
                          >
                            Download
                          </button>
                        )}
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
                    
                    {/* Download Progress */}
                    {downloadProgress.status !== 'idle' && (
                      <div className="mt-3">
                        <div className="flex justify-between text-xs text-gray-600 mb-1">
                          <span>{downloadProgress.message || 'Downloading...'}</span>
                          {downloadProgress.progress > 0 && (
                            <span>{downloadProgress.progress}%</span>
                          )}
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full transition-all ${
                              downloadProgress.status === 'error' ? 'bg-red-600' :
                              downloadProgress.status === 'complete' ? 'bg-green-600' : 'bg-blue-600'
                            }`}
                            style={{ width: `${downloadProgress.progress}%` }}
                          />
                        </div>
                      </div>
                    )}
                    
                    <p className="text-xs text-gray-500 mt-3">
                      Downloads are cached in the persistent volume and run in background.
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
                        {['ollama', 'lmstudio', 'openai', 'anthropic'].map((provider) => (
                          <div key={provider}>
                            <label className="block text-xs text-gray-500 mb-1 capitalize">
                              {provider} {provider === 'openai' || provider === 'anthropic' ? '(for Portkey/proxy)' : ''}
                            </label>
                            <input
                              type="text"
                              value={baseUrls[provider] || ''}
                              onChange={(e) => setBaseUrls(prev => ({ ...prev, [provider]: e.target.value }))}
                              placeholder={DEFAULT_BASE_URLS[provider] || 'Leave empty for default'}
                              className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
                            />
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
            ) : (
              /* Reproducibility Tab */
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
                      <HelpCircle className="h-4 w-4 text-gray-400" title="Controls randomness in AI-generated code" />
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
                      <HelpCircle className="h-4 w-4 text-gray-400" title="Controls randomness in executed Python code" />
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
              disabled={saving || (!selectedProvider && availableProviders.length > 0)}
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-2"
            >
              {saving && <Loader className="h-4 w-4 animate-spin" />}
              <span>{saving ? 'Saving...' : 'Save'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SettingsModal

