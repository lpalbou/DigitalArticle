import React, { useState, useEffect } from 'react'
import { AlertCircle, Loader, Info } from 'lucide-react'
import axios from 'axios'
import { Persona, PersonaSelection } from '../types/persona'
import PersonaCard from './PersonaCard'
import { useToaster } from '../contexts/ToasterContext'

interface PersonaTabProps {
  notebookId?: string  // Optional notebook ID for per-notebook selection
}

/**
 * PersonaTab - Main persona selection UI for Settings Modal
 *
 * Design Philosophy:
 * - Simple, clean selection interface
 * - Organized by category (Base personas first)
 * - Clear indication of current selection
 * - Save button (consistent with SettingsModal pattern)
 *
 * Architecture:
 * - Fetches personas from API
 * - Maintains local selection state
 * - Saves to notebook metadata on Save click
 */
const PersonaTab: React.FC<PersonaTabProps> = ({ notebookId }) => {
  const toaster = useToaster()

  // State
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [personas, setPersonas] = useState<Persona[]>([])
  const [selection, setSelection] = useState<PersonaSelection>({
    base_persona: 'generic',  // Default to generic
    domain_personas: [],
    role_modifier: null,
    custom_overrides: {},
  })

  // Load personas from API
  useEffect(() => {
    loadPersonas()
    if (notebookId) {
      loadNotebookPersonas()
    }
  }, [notebookId])

  const loadPersonas = async () => {
    try {
      setLoading(true)
      const response = await axios.get('/api/personas')
      setPersonas(response.data)
    } catch (error) {
      console.error('Error loading personas:', error)
      toaster.error('Failed to load personas')
    } finally {
      setLoading(false)
    }
  }

  const loadNotebookPersonas = async () => {
    if (!notebookId) return

    try {
      const response = await axios.get(`/api/personas/notebooks/${notebookId}/personas`)
      if (response.data) {
        setSelection(response.data)
      }
    } catch (error) {
      console.error('Error loading notebook personas:', error)
      // Not critical - notebook might not have personas set yet
    }
  }

  const handleSave = async () => {
    if (!notebookId) {
      toaster.info('No notebook open - persona will be saved when you open a notebook')
      return
    }

    try {
      setSaving(true)
      await axios.put(`/api/personas/notebooks/${notebookId}/personas`, selection)
      toaster.success('Persona selection saved!')
    } catch (error) {
      console.error('Error saving persona selection:', error)
      toaster.error('Failed to save persona selection')
    } finally {
      setSaving(false)
    }
  }

  // Group personas by category
  const basePersonas = personas.filter(p => p.category === 'base')
  const domainPersonas = personas.filter(p => p.category === 'domain')
  const rolePersonas = personas.filter(p => p.category === 'role')
  const customPersonas = personas.filter(p => p.category === 'custom')

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-3 text-gray-600">Loading personas...</span>
      </div>
    )
  }

  if (personas.length === 0) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
        <div className="flex items-start">
          <AlertCircle className="h-6 w-6 text-yellow-600 flex-shrink-0 mt-0.5" />
          <div className="ml-4">
            <h4 className="text-base font-semibold text-yellow-900 mb-2">
              No Personas Available
            </h4>
            <p className="text-sm text-yellow-800">
              System personas should be available by default. Check your installation.
            </p>
          </div>
        </div>
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
            <p className="font-medium mb-1">How Personas Work</p>
            <p className="text-xs">
              Personas define specialized AI assistants for different domains. Select one
              <strong> base persona</strong> (required) and optionally add domain-specific
              personas for enhanced capabilities.
            </p>
          </div>
        </div>
      </div>

      {/* Current Selection Summary */}
      {selection.base_persona && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Current Selection</h4>
          <div className="flex flex-wrap gap-2">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 border border-blue-200">
              Base: {selection.base_persona}
            </span>
            {selection.domain_personas.map(slug => (
              <span
                key={slug}
                className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800 border border-purple-200"
              >
                Domain: {slug}
              </span>
            ))}
            {selection.role_modifier && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800 border border-orange-200">
                Role: {selection.role_modifier}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Base Personas (Required - Radio Select) */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">
          Base Persona <span className="text-red-500">*</span>
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {basePersonas.map(persona => (
            <PersonaCard
              key={persona.slug}
              persona={persona}
              isSelected={selection.base_persona === persona.slug}
              onSelect={() => setSelection({ ...selection, base_persona: persona.slug })}
              selectionMode="radio"
            />
          ))}
        </div>
      </div>

      {/* Domain Personas (Optional - Multi-select) */}
      {domainPersonas.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            Domain Personas <span className="text-gray-500 text-xs font-normal">(Optional)</span>
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {domainPersonas.map(persona => (
              <PersonaCard
                key={persona.slug}
                persona={persona}
                isSelected={selection.domain_personas.includes(persona.slug)}
                onSelect={() => {
                  const isCurrentlySelected = selection.domain_personas.includes(persona.slug)
                  setSelection({
                    ...selection,
                    domain_personas: isCurrentlySelected
                      ? selection.domain_personas.filter(s => s !== persona.slug)
                      : [...selection.domain_personas, persona.slug],
                  })
                }}
                selectionMode="checkbox"
              />
            ))}
          </div>
          <p className="text-xs text-gray-500 mt-2">
            💡 Select multiple domain personas to combine their expertise
          </p>
        </div>
      )}

      {/* Role Personas (Optional - Radio Select) */}
      {rolePersonas.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            Role Modifier <span className="text-gray-500 text-xs font-normal">(Optional)</span>
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {rolePersonas.map(persona => (
              <PersonaCard
                key={persona.slug}
                persona={persona}
                isSelected={selection.role_modifier === persona.slug}
                onSelect={() =>
                  setSelection({
                    ...selection,
                    role_modifier:
                      selection.role_modifier === persona.slug ? null : persona.slug,
                  })
                }
                selectionMode="radio"
              />
            ))}
          </div>
        </div>
      )}

      {/* Custom Personas */}
      {customPersonas.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            Custom Personas
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {customPersonas.map(persona => (
              <PersonaCard
                key={persona.slug}
                persona={persona}
                isSelected={selection.base_persona === persona.slug}
                onSelect={() => setSelection({ ...selection, base_persona: persona.slug })}
                selectionMode="radio"
              />
            ))}
          </div>
        </div>
      )}

      {/* Save Button */}
      <div className="pt-4 border-t border-gray-200">
        <button
          onClick={handleSave}
          disabled={saving || !notebookId}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
        >
          {saving && <Loader className="h-4 w-4 animate-spin" />}
          <span>{saving ? 'Saving...' : notebookId ? 'Save Persona Selection' : 'Open a notebook to save'}</span>
        </button>
      </div>
    </div>
  )
}

export default PersonaTab
