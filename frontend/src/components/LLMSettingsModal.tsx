import React, { useState, useEffect } from 'react'
import { X, AlertCircle, CheckCircle, Loader, ExternalLink, HelpCircle, Shuffle } from 'lucide-react'
import axios from 'axios'

interface Provider {
  name: string
  display_name: string
  available: boolean
  error?: string
  default_model?: string
  models: string[]
}

interface LLMSettingsModalProps {
  isOpen: boolean
  onClose: () => void
  currentNotebookId?: string
}

const LLMSettingsModal: React.FC<LLMSettingsModalProps> = ({ isOpen, onClose, currentNotebookId }) => {
  const [providers, setProviders] = useState<Provider[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedProvider, setSelectedProvider] = useState<string>('')
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [saving, setSaving] = useState(false)
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  
  // Seed management
  const [customSeed, setCustomSeed] = useState<string>('')
  const [useCustomSeed, setUseCustomSeed] = useState(true) // Enable by default
  const [showSeedTooltip, setShowSeedTooltip] = useState(false)

  useEffect(() => {
    if (isOpen) {
      fetchProviders()
    }
  }, [isOpen])

  const fetchProviders = async () => {
    try {
      setLoading(true)
      const response = await axios.get<Provider[]>('/api/llm/providers')
      setProviders(response.data)

      // Smart cascading fallback logic for provider/model selection
      let selectedProv = null
      let selectedMod = null

      const lmstudio = response.data.find(p => p.name === 'lmstudio')

      if (lmstudio?.available) {
        selectedProv = lmstudio.name

        // Try preferred models in order
        if (lmstudio.models.includes('qwen/qwen3-next-80b')) {
          selectedMod = 'qwen/qwen3-next-80b'
        } else if (lmstudio.models.includes('qwen/qwen3-coder-30b')) {
          selectedMod = 'qwen/qwen3-coder-30b'
        } else if (lmstudio.models.length > 0) {
          selectedMod = lmstudio.models[0]
        }
      } else {
        // LMStudio not available - use first available provider with first model
        const firstAvailable = response.data.find(p => p.available && p.models.length > 0)
        if (firstAvailable) {
          selectedProv = firstAvailable.name
          selectedMod = firstAvailable.models[0]
        }
      }

      if (selectedProv && selectedMod) {
        setSelectedProvider(selectedProv)
        setSelectedModel(selectedMod)
      }

      setLoading(false)
    } catch (error) {
      console.error('Failed to fetch providers:', error)
      setLoading(false)
    }
  }

  const handleProviderChange = (providerName: string) => {
    setSelectedProvider(providerName)
    const provider = providers.find(p => p.name === providerName)
    if (provider) {
      // Set the default model for this provider
      setSelectedModel(provider.default_model || provider.models[0] || '')
    }
  }

  const generateRandomSeed = () => {
    const seed = Math.floor(Math.random() * 2147483647) // Max 32-bit signed integer
    setCustomSeed(seed.toString())
  }

  const handleSeedToggle = (enabled: boolean) => {
    setUseCustomSeed(enabled)
    if (enabled && !customSeed) {
      generateRandomSeed()
    }
  }

  // Initialize with random seed when modal opens
  useEffect(() => {
    if (isOpen && useCustomSeed && !customSeed) {
      generateRandomSeed()
    }
  }, [isOpen, useCustomSeed, customSeed])

  const handleSave = async () => {
    if (!selectedProvider || !selectedModel) {
      setSaveMessage({ type: 'error', text: 'Please select both provider and model' })
      return
    }

    // Validate seed if custom seed is enabled
    if (useCustomSeed && customSeed) {
      const seedNum = parseInt(customSeed)
      if (isNaN(seedNum) || seedNum < 0 || seedNum > 2147483647) {
        setSaveMessage({ type: 'error', text: 'Seed must be a number between 0 and 2,147,483,647' })
        return
      }
    }

    try {
      setSaving(true)

      // Save LLM provider settings globally
      await axios.post('/api/llm/providers/select', {
        provider: selectedProvider,
        model: selectedModel
      })

      // Update current notebook's provider/model if available
      if (currentNotebookId) {
        await axios.put(`/api/notebooks/${currentNotebookId}`, {
          llm_provider: selectedProvider,
          llm_model: selectedModel,
          custom_seed: useCustomSeed && customSeed ? parseInt(customSeed) : null
        })
      }

      setSaveMessage({ type: 'success', text: 'Settings updated successfully!' })

      // Trigger footer refresh by dispatching custom event
      window.dispatchEvent(new CustomEvent('llm-settings-updated'))

      setTimeout(() => {
        onClose()
      }, 1500)
    } catch (error: any) {
      setSaveMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Failed to update provider'
      })
    } finally {
      setSaving(false)
    }
  }

  const availableProviders = providers.filter(p => p.available)
  const hasNoAvailableProviders = !loading && availableProviders.length === 0

  const currentProvider = providers.find(p => p.name === selectedProvider)

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div
          className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          onClick={onClose}
        ></div>

        {/* Modal panel */}
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-2xl sm:w-full">
          {/* Header */}
          <div className="bg-gray-50 px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">LLM Provider Settings</h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-500 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Content */}
          <div className="bg-white px-6 py-6">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader className="h-8 w-8 animate-spin text-blue-600" />
                <span className="ml-3 text-gray-600">Detecting available providers...</span>
              </div>
            ) : hasNoAvailableProviders ? (
              /* No providers available - show warning */
              <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                <div className="flex items-start">
                  <AlertCircle className="h-6 w-6 text-red-600 flex-shrink-0 mt-0.5" />
                  <div className="ml-4">
                    <h4 className="text-base font-semibold text-red-900 mb-2">
                      No LLM Providers Available
                    </h4>
                    <p className="text-sm text-red-800 mb-4">
                      Digital Article requires an LLM provider to generate code from prompts.
                      Please set up one of the following:
                    </p>
                    <div className="space-y-3 text-sm">
                      <div className="bg-white border border-red-200 rounded p-3">
                        <p className="font-medium text-red-900 mb-1">Local Options (Recommended):</p>
                        <ul className="list-disc list-inside space-y-1 text-red-800 ml-2">
                          <li>
                            Install <a href="https://lmstudio.ai/" target="_blank" rel="noopener noreferrer"
                              className="font-medium underline hover:text-red-600">LM Studio</a> and load a model
                          </li>
                          <li>
                            Install <a href="https://ollama.ai/" target="_blank" rel="noopener noreferrer"
                              className="font-medium underline hover:text-red-600">Ollama</a> and pull a model
                          </li>
                        </ul>
                      </div>
                      <div className="bg-white border border-red-200 rounded p-3">
                        <p className="font-medium text-red-900 mb-1">Cloud Options (Requires API Key):</p>
                        <ul className="list-disc list-inside space-y-1 text-red-800 ml-2">
                          <li>
                            Set <code className="bg-red-100 px-1 py-0.5 rounded">ANTHROPIC_API_KEY</code> environment variable
                          </li>
                          <li>
                            Set <code className="bg-red-100 px-1 py-0.5 rounded">OPENAI_API_KEY</code> environment variable
                          </li>
                        </ul>
                      </div>
                    </div>
                    <p className="text-xs text-red-700 mt-4">
                      After setting up a provider, restart the backend server and refresh this page.
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              /* Provider selection UI */
              <div className="space-y-5">
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
                    {currentProvider.default_model && (
                      <p className="mt-1 text-xs text-gray-500">
                        Default: {currentProvider.default_model}
                      </p>
                    )}
                  </div>
                )}

                {/* Reproducibility Settings */}
                {currentNotebookId && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center space-x-2">
                        <h4 className="text-sm font-semibold text-blue-900">Reproducibility Control</h4>
                        <div className="relative">
                          <button
                            type="button"
                            onMouseEnter={() => setShowSeedTooltip(true)}
                            onMouseLeave={() => setShowSeedTooltip(false)}
                            className="text-blue-500 hover:text-blue-700 transition-colors"
                          >
                            <HelpCircle className="h-4 w-4" />
                          </button>
                          {showSeedTooltip && (
                            <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-80 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-lg z-10">
                              <div className="font-medium mb-1">🎲 What is a seed?</div>
                              <div className="mb-2">
                                A seed ensures your notebook produces the same results every time you run it. 
                                This is crucial for scientific reproducibility and sharing reliable analyses.
                              </div>
                              <div className="text-gray-300">
                                • <strong>Same seed</strong> = Same random numbers, same results<br/>
                                • <strong>Different seed</strong> = Different random data<br/>
                                • <strong>Disable</strong> = Automatic seed based on notebook ID
                              </div>
                              <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
                            </div>
                          )}
                        </div>
                      </div>
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={useCustomSeed}
                          onChange={(e) => handleSeedToggle(e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        <span className="ml-2 text-sm font-medium text-blue-900">Custom Seed</span>
                      </label>
                    </div>

                    {useCustomSeed && (
                      <div className="space-y-3">
                        <div className="flex space-x-2">
                          <input
                            type="number"
                            value={customSeed}
                            onChange={(e) => setCustomSeed(e.target.value)}
                            placeholder="Enter seed (0-2147483647)"
                            min="0"
                            max="2147483647"
                            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm bg-white"
                          />
                          <button
                            type="button"
                            onClick={generateRandomSeed}
                            className="px-3 py-2 bg-blue-100 hover:bg-blue-200 border border-blue-300 rounded-md transition-colors flex items-center space-x-1 text-blue-700"
                            title="Generate random seed"
                          >
                            <Shuffle className="h-4 w-4" />
                            <span className="text-sm font-medium">Random</span>
                          </button>
                        </div>
                        <div className="bg-blue-100 rounded-md p-2">
                          <p className="text-xs text-blue-800">
                            <strong>🔒 Complete Reproducibility:</strong> This seed controls both AI code generation and random data to ensure identical results every time.
                          </p>
                        </div>
                      </div>
                    )}

                    {!useCustomSeed && (
                      <div className="bg-blue-100 rounded-md p-2">
                        <p className="text-xs text-blue-800">
                          <strong>🔄 Automatic Mode:</strong> Using notebook-based seed for consistent results within this notebook.
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Provider Status */}
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                  <h4 className="text-sm font-semibold text-gray-700 mb-3">Provider Status</h4>
                  <div className="space-y-2">
                    {providers.map((provider) => (
                      <div key={provider.name} className="flex items-start text-sm">
                        {provider.available ? (
                          <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
                        ) : (
                          <AlertCircle className="h-4 w-4 text-gray-400 flex-shrink-0 mt-0.5" />
                        )}
                        <div className="ml-2">
                          <span className={provider.available ? 'text-green-900 font-medium' : 'text-gray-600'}>
                            {provider.display_name}
                          </span>
                          {provider.error && (
                            <span className="text-gray-500 text-xs ml-2">({provider.error})</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Save Message */}
                {saveMessage && (
                  <div className={`rounded-lg p-4 ${
                    saveMessage.type === 'success'
                      ? 'bg-green-50 border border-green-200 text-green-800'
                      : 'bg-red-50 border border-red-200 text-red-800'
                  }`}>
                    {saveMessage.text}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Footer */}
          {!loading && !hasNoAvailableProviders && (
            <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
              <button
                onClick={onClose}
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={!selectedProvider || !selectedModel || saving}
                className="btn btn-primary flex items-center space-x-2"
              >
                {saving && <Loader className="h-4 w-4 animate-spin" />}
                <span>{saving ? 'Saving...' : 'Save Settings'}</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default LLMSettingsModal
