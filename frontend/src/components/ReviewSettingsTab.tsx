import React, { useState, useEffect, forwardRef, useImperativeHandle } from 'react'
import { AlertCircle, Loader, Info, CheckCircle } from 'lucide-react'
import axios from 'axios'
import { useToaster } from '../contexts/ToasterContext'

interface ReviewSettingsTabProps {
  notebookId?: string  // Optional notebook ID for per-notebook settings
}

export interface ReviewSettingsTabRef {
  save: () => Promise<void>
}

interface ReviewSettings {
  auto_review_enabled: boolean
  phases: {
    intent_enabled: boolean
    implementation_enabled: boolean
    results_enabled: boolean
  }
  display: {
    show_severity: 'all' | 'warnings_and_critical' | 'critical_only'
    auto_collapse: boolean
    show_suggestions: boolean
  }
  review_style: 'constructive' | 'brief' | 'detailed'
}

/**
 * ReviewSettingsTab - Review configuration UI for Settings Modal
 *
 * Allows users to configure:
 * - Auto-review toggle (automatic review after cell execution)
 * - Review phases (intent, implementation, results)
 * - Severity filtering (all, warnings+critical, critical only)
 * - Review style (constructive, brief, detailed)
 */
const ReviewSettingsTab = forwardRef<ReviewSettingsTabRef, ReviewSettingsTabProps>(({ notebookId }, ref) => {
  const toaster = useToaster()

  // Expose save function to parent via ref
  useImperativeHandle(ref, () => ({
    save: handleSave
  }))

  // State
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [settings, setSettings] = useState<ReviewSettings>({
    auto_review_enabled: false,
    phases: {
      intent_enabled: true,
      implementation_enabled: true,
      results_enabled: true,
    },
    display: {
      show_severity: 'all',
      auto_collapse: false,
      show_suggestions: true,
    },
    review_style: 'constructive',
  })

  // Load settings from backend when component mounts or notebookId changes
  useEffect(() => {
    if (notebookId) {
      loadSettings()
    }
  }, [notebookId])

  const loadSettings = async () => {
    if (!notebookId) return

    try {
      setLoading(true)
      const response = await axios.get(`/api/review/notebooks/${notebookId}/settings`)
      if (response.data) {
        setSettings(response.data)
      }
    } catch (error) {
      console.error('Error loading review settings:', error)
      // Not critical - use defaults
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!notebookId) {
      toaster.info('No notebook open - settings will be saved when you open a notebook')
      return
    }

    try {
      setSaving(true)
      await axios.put(`/api/review/notebooks/${notebookId}/settings`, settings)
      toaster.success('Review settings saved!')
    } catch (error) {
      console.error('Error saving review settings:', error)
      toaster.error('Failed to save review settings')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-3 text-gray-600">Loading review settings...</span>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Info banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <Info className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-800">
            <p className="font-medium mb-1">Automated Quality Control</p>
            <p className="text-xs">
              The review system provides automated quality checks and improvement suggestions
              for your analyses. It evaluates methodology rigor, code quality, and result interpretation.
            </p>
          </div>
        </div>
      </div>

      {/* Auto-review Toggle */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-gray-900 mb-1">
              Enable Auto-Review
            </h3>
            <p className="text-xs text-gray-600">
              Automatically review code and results after each cell execution
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={settings.auto_review_enabled}
              onChange={(e) => setSettings({ ...settings, auto_review_enabled: e.target.checked })}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
          </label>
        </div>
      </div>

      {/* Review Phases */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Review Phases</h3>
        <div className="space-y-3">
          <label className="flex items-start space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.phases.intent_enabled}
              onChange={(e) => setSettings({
                ...settings,
                phases: { ...settings.phases, intent_enabled: e.target.checked }
              })}
              className="mt-0.5 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <div className="flex-1">
              <span className="text-sm font-medium text-gray-900">Intent Review</span>
              <p className="text-xs text-gray-600">Check if the question/intent is clear and well-defined</p>
            </div>
          </label>

          <label className="flex items-start space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.phases.implementation_enabled}
              onChange={(e) => setSettings({
                ...settings,
                phases: { ...settings.phases, implementation_enabled: e.target.checked }
              })}
              className="mt-0.5 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <div className="flex-1">
              <span className="text-sm font-medium text-gray-900">Implementation Review</span>
              <p className="text-xs text-gray-600">Evaluate code quality, method appropriateness, and assumptions</p>
            </div>
          </label>

          <label className="flex items-start space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.phases.results_enabled}
              onChange={(e) => setSettings({
                ...settings,
                phases: { ...settings.phases, results_enabled: e.target.checked }
              })}
              className="mt-0.5 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <div className="flex-1">
              <span className="text-sm font-medium text-gray-900">Results Review</span>
              <p className="text-xs text-gray-600">Check result interpretation and statistical validity</p>
            </div>
          </label>
        </div>
      </div>

      {/* Display Settings */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Display Settings</h3>

        {/* Severity Filter */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Severity Filter
          </label>
          <div className="space-y-2">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="radio"
                name="severity"
                checked={settings.display.show_severity === 'all'}
                onChange={() => setSettings({
                  ...settings,
                  display: { ...settings.display, show_severity: 'all' }
                })}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
              />
              <span className="text-sm text-gray-900">Show all feedback (info, warnings, critical)</span>
            </label>
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="radio"
                name="severity"
                checked={settings.display.show_severity === 'warnings_and_critical'}
                onChange={() => setSettings({
                  ...settings,
                  display: { ...settings.display, show_severity: 'warnings_and_critical' }
                })}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
              />
              <span className="text-sm text-gray-900">Show warnings and critical only</span>
            </label>
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="radio"
                name="severity"
                checked={settings.display.show_severity === 'critical_only'}
                onChange={() => setSettings({
                  ...settings,
                  display: { ...settings.display, show_severity: 'critical_only' }
                })}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
              />
              <span className="text-sm text-gray-900">Show critical only</span>
            </label>
          </div>
        </div>

        {/* Other Display Options */}
        <div className="space-y-2 pt-3 border-t border-gray-200">
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.display.auto_collapse}
              onChange={(e) => setSettings({
                ...settings,
                display: { ...settings.display, auto_collapse: e.target.checked }
              })}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <span className="text-sm text-gray-900">Auto-collapse review feedback</span>
          </label>

          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.display.show_suggestions}
              onChange={(e) => setSettings({
                ...settings,
                display: { ...settings.display, show_suggestions: e.target.checked }
              })}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <span className="text-sm text-gray-900">Show improvement suggestions</span>
          </label>
        </div>
      </div>

      {/* Review Style */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Review Style</h3>
        <select
          value={settings.review_style}
          onChange={(e) => setSettings({ ...settings, review_style: e.target.value as ReviewSettings['review_style'] })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
        >
          <option value="constructive">Constructive with suggestions</option>
          <option value="brief">Brief and concise</option>
          <option value="detailed">Detailed and comprehensive</option>
        </select>
        <p className="text-xs text-gray-600 mt-2">
          {settings.review_style === 'constructive' && 'Balanced feedback with actionable improvement suggestions'}
          {settings.review_style === 'brief' && 'Quick highlights of key issues'}
          {settings.review_style === 'detailed' && 'In-depth analysis with extensive commentary'}
        </p>
      </div>

      {/* Note about Review vs Persona */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <AlertCircle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-yellow-800">
            <p className="font-medium mb-1">Review vs Persona</p>
            <p className="text-xs">
              <strong>Review:</strong> Quality control system that provides automated feedback and improvement suggestions.
              Works independently of your selected persona.
              <br /><br />
              <strong>Persona:</strong> Domain expert who writes the article (e.g., Clinical, Genomics).
              Go to the Persona tab to select your domain expert.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
})

ReviewSettingsTab.displayName = 'ReviewSettingsTab'

export default ReviewSettingsTab
