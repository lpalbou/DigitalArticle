import React, { useState, useEffect, forwardRef, useImperativeHandle } from 'react'
import { AlertCircle, Loader, Info, ChevronDown, ChevronRight } from 'lucide-react'
import axios from 'axios'
import { Persona, PersonaSelection } from '../types/persona'
import PersonaCard from './PersonaCard'
import { useToaster } from '../contexts/ToasterContext'

interface PersonaTabProps {
  notebookId?: string  // Optional notebook ID for per-notebook selection
}

export interface PersonaTabRef {
  save: () => Promise<void>
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
const PersonaTab = forwardRef<PersonaTabRef, PersonaTabProps>(({ notebookId }, ref) => {
  const toaster = useToaster()

  // Expose save function to parent via ref
  useImperativeHandle(ref, () => ({
    save: handleSave
  }))

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
  const [expandedPersona, setExpandedPersona] = useState<string | null>(null)
  const [combinedPreview, setCombinedPreview] = useState<any>(null)
  const [loadingPreview, setLoadingPreview] = useState(false)

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
      return
    }

    try {
      setSaving(true)
      await axios.put(`/api/personas/notebooks/${notebookId}/personas`, selection)
    } catch (error) {
      console.error('Error saving persona selection:', error)
      toaster.error('Failed to save persona selection')
    } finally {
      setSaving(false)
    }
  }

  // Fetch combined persona preview when selection changes
  useEffect(() => {
    const fetchCombined = async () => {
      if (!selection.base_persona) return

      setLoadingPreview(true)
      try {
        const response = await axios.post('/api/personas/combine', selection)
        setCombinedPreview(response.data)
      } catch (error) {
        console.error('Failed to fetch combined preview:', error)
        setCombinedPreview(null)
      } finally {
        setLoadingPreview(false)
      }
    }

    // Debounce to avoid too many API calls
    const timeoutId = setTimeout(fetchCombined, 300)
    return () => clearTimeout(timeoutId)
  }, [selection])

  // Group personas by category
  const basePersonas = personas.filter(p => p.category === 'base')
  const domainPersonas = personas.filter(p => p.category === 'domain')
  const rolePersonas = personas.filter(p => p.category === 'role')
  const customPersonas = personas.filter(p => p.category === 'custom')

  // Toggle domain persona selection
  const toggleDomainPersona = (slug: string) => {
    const isSelected = selection.domain_personas.includes(slug)
    setSelection({
      ...selection,
      domain_personas: isSelected
        ? selection.domain_personas.filter(s => s !== slug)
        : [...selection.domain_personas, slug]
    })
  }

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

  // Persona details component (inline)
  const PersonaDetails: React.FC<{ persona: Persona }> = ({ persona }) => (
    <div className="mt-3 p-4 bg-gray-50 rounded-lg border border-gray-200 text-sm">
      {persona.expertise_description && (
        <div className="mb-3">
          <h4 className="font-medium text-gray-900 mb-1">Expertise</h4>
          <p className="text-gray-700">{persona.expertise_description}</p>
        </div>
      )}

      {persona.preferred_libraries && persona.preferred_libraries.length > 0 && (
        <div className="mb-3">
          <h5 className="text-xs font-semibold text-gray-600 uppercase mb-1.5">Preferred Libraries</h5>
          <div className="flex flex-wrap gap-1">
            {persona.preferred_libraries.map((lib: string) => (
              <span key={lib} className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded font-medium">
                {lib}
              </span>
            ))}
          </div>
        </div>
      )}

      {persona.guidance && persona.guidance.length > 0 && (
        <div>
          <h5 className="text-xs font-semibold text-gray-600 uppercase mb-1.5">Key Constraints</h5>
          <ul className="text-xs text-gray-600 list-disc list-inside space-y-0.5">
            {persona.guidance
              .find((g: any) => g.scope === 'code_generation')
              ?.constraints?.slice(0, 3)
              .map((c: string, i: number) => (
                <li key={i}>{c}</li>
              ))}
          </ul>
        </div>
      )}
    </div>
  )

  return (
    <div className="space-y-6">
      {/* Info banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <Info className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-800">
            <p className="font-medium mb-1">How Personas Work</p>
            <p className="text-xs">
              Personas define domain experts who write your digital article. Select the persona
              that best matches your analysis domain (clinical trials, genomics, real-world data, etc.).
            </p>
          </div>
        </div>
      </div>

      {/* Current Selection Summary */}
      {(selection.base_persona || selection.domain_personas.length > 0) && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Current Selection</h4>
          <div className="flex flex-wrap gap-2">
            {selection.base_persona && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 border border-blue-200">
                Base: {selection.base_persona}
              </span>
            )}
            {selection.domain_personas.map(slug => (
              <span
                key={slug}
                className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800 border border-purple-200"
              >
                Domain: {slug}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Base Personas - Radio Select */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">
          Select Base Persona <span className="text-red-500">*</span>
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {basePersonas.map(persona => (
            <div key={persona.slug}>
              <div className="relative">
                <PersonaCard
                  persona={persona}
                  isSelected={selection.base_persona === persona.slug}
                  onSelect={() => setSelection({ ...selection, base_persona: persona.slug })}
                  selectionMode="radio"
                />
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    setExpandedPersona(expandedPersona === persona.slug ? null : persona.slug)
                  }}
                  className="absolute bottom-2 right-2 p-1 hover:bg-gray-200 rounded transition-colors z-10"
                  title={expandedPersona === persona.slug ? "Hide details" : "Show details"}
                >
                  {expandedPersona === persona.slug ? (
                    <ChevronDown className="h-4 w-4 text-gray-600" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-gray-600" />
                  )}
                </button>
              </div>
              {expandedPersona === persona.slug && <PersonaDetails persona={persona} />}
            </div>
          ))}
          {customPersonas.map(persona => (
            <div key={persona.slug}>
              <div className="relative">
                <PersonaCard
                  persona={persona}
                  isSelected={selection.base_persona === persona.slug}
                  onSelect={() => setSelection({ ...selection, base_persona: persona.slug })}
                  selectionMode="radio"
                />
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    setExpandedPersona(expandedPersona === persona.slug ? null : persona.slug)
                  }}
                  className="absolute bottom-2 right-2 p-1 hover:bg-gray-200 rounded transition-colors z-10"
                  title={expandedPersona === persona.slug ? "Hide details" : "Show details"}
                >
                  {expandedPersona === persona.slug ? (
                    <ChevronDown className="h-4 w-4 text-gray-600" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-gray-600" />
                  )}
                </button>
              </div>
              {expandedPersona === persona.slug && <PersonaDetails persona={persona} />}
            </div>
          ))}
        </div>
      </div>

      {/* Domain Personas - Checkbox Multi-Select */}
      {domainPersonas.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            Add Domain Specializations <span className="text-gray-500 text-xs font-normal">(Optional)</span>
          </h3>
          <p className="text-xs text-gray-600 mb-3">
            Domain personas add specialized expertise to your base persona. You can select multiple.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {domainPersonas.map(persona => (
              <div key={persona.slug}>
                <div className="relative">
                  <PersonaCard
                    persona={persona}
                    isSelected={selection.domain_personas.includes(persona.slug)}
                    onSelect={() => toggleDomainPersona(persona.slug)}
                    selectionMode="checkbox"
                  />
                  <button
                    onClick={() => setExpandedPersona(expandedPersona === persona.slug ? null : persona.slug)}
                    className="absolute top-2 right-2 p-1 hover:bg-gray-100 rounded transition-colors"
                    title={expandedPersona === persona.slug ? "Hide details" : "Show details"}
                  >
                    {expandedPersona === persona.slug ? (
                      <ChevronDown className="h-4 w-4 text-gray-600" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-gray-600" />
                    )}
                  </button>
                </div>
                {expandedPersona === persona.slug && <PersonaDetails persona={persona} />}
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-500 mt-2">
            💡 Domain personas combine their expertise with your base persona
          </p>
        </div>
      )}

      {/* Combined Guidance Preview */}
      {selection.domain_personas.length > 0 && (
        <div className="p-4 bg-purple-50 border border-purple-200 rounded-lg">
          <h4 className="text-sm font-semibold text-purple-900 mb-2 flex items-center gap-2">
            Combined Guidance Preview
            {loadingPreview && <Loader className="h-4 w-4 animate-spin text-purple-600" />}
          </h4>
          {!loadingPreview && combinedPreview ? (
            <div className="text-sm text-purple-800 space-y-2">
              <div>
                <span className="font-medium">Active Personas:</span>{' '}
                {combinedPreview.source_personas?.join(' + ') || 'N/A'}
              </div>
              {combinedPreview.effective_guidance?.code_generation?.constraints?.length > 0 && (
                <div>
                  <span className="font-medium">Active Constraints:</span>{' '}
                  {combinedPreview.effective_guidance.code_generation.constraints.length}
                </div>
              )}
              {combinedPreview.effective_guidance?.code_generation?.preferences?.length > 0 && (
                <div>
                  <span className="font-medium">Preferences:</span>{' '}
                  {combinedPreview.effective_guidance.code_generation.preferences.length}
                </div>
              )}
              {combinedPreview.conflict_resolutions && combinedPreview.conflict_resolutions.length > 0 && (
                <div className="mt-2 pt-2 border-t border-purple-300">
                  <span className="font-medium text-xs">Conflicts Resolved:</span>{' '}
                  <span className="text-xs">{combinedPreview.conflict_resolutions.length}</span>
                </div>
              )}
            </div>
          ) : !loadingPreview ? (
            <p className="text-sm text-purple-700">Select domain personas to see combined guidance</p>
          ) : null}
        </div>
      )}
    </div>
  )
})

PersonaTab.displayName = 'PersonaTab'

export default PersonaTab
