import React, { useState } from 'react'
import { X, Save, Loader } from 'lucide-react'
import { Persona, PersonaCreateRequest, PersonaCategory } from '../types/persona'
import { useToaster } from '../contexts/ToasterContext'
import axios from 'axios'

interface PersonaEditorProps {
  isOpen: boolean
  onClose: () => void
  persona?: Persona  // If provided, edit mode; otherwise create mode
  onSaved?: () => void  // Callback after successful save
}

/**
 * PersonaEditor - Modal for creating/editing custom personas
 *
 * MVP Implementation:
 * - Basic form for essential fields
 * - Create/update functionality
 * - Simple validation
 *
 * Future Enhancements:
 * - Guidance editor (per scope)
 * - Library preferences
 * - Review capabilities editor
 * - JSON import/export
 * - Clone from existing
 */
const PersonaEditor: React.FC<PersonaEditorProps> = ({
  isOpen,
  onClose,
  persona,
  onSaved,
}) => {
  const toaster = useToaster()
  const [saving, setSaving] = useState(false)

  // Form state (simplified MVP)
  const [name, setName] = useState(persona?.name || '')
  const [slug, setSlug] = useState(persona?.slug || '')
  const [description, setDescription] = useState(persona?.description || '')
  const [category, setCategory] = useState<PersonaCategory>(persona?.category || 'custom')
  const [icon, setIcon] = useState(persona?.icon || 'user')
  const [color, setColor] = useState(persona?.color || '#6366f1')

  const handleSave = async () => {
    // Basic validation
    if (!name || !slug) {
      toaster.error('Name and slug are required')
      return
    }

    try {
      setSaving(true)

      const request: PersonaCreateRequest = {
        name,
        slug,
        description,
        category,
        icon,
        color,
        priority: 100,  // Default priority
        expertise_description: '',
        domain_context: '',
        methodology_style: '',
        guidance: [],
        preferred_libraries: [],
        avoid_libraries: [],
        preferred_methods: [],
        review_capabilities: [],
        tags: [],
        compatible_with: [],
        incompatible_with: [],
      }

      if (persona) {
        // Update existing
        await axios.put(`/api/personas/${persona.slug}`, request)
        toaster.success('Persona updated!')
      } else {
        // Create new
        await axios.post('/api/personas', request)
        toaster.success('Persona created!')
      }

      onSaved?.()
      onClose()
    } catch (error: any) {
      console.error('Error saving persona:', error)
      toaster.error(error.response?.data?.detail || 'Failed to save persona')
    } finally {
      setSaving(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900">
            {persona ? 'Edit Persona' : 'Create Custom Persona'}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-6 overflow-y-auto space-y-4">
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-sm text-yellow-800">
              <strong>MVP Implementation:</strong> This is a simplified persona editor.
              Advanced features (guidance templates, library preferences) coming soon.
            </p>
          </div>

          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Financial Analyst"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Slug */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Slug <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={slug}
              onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-'))}
              placeholder="e.g., financial-analyst"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              disabled={!!persona}  // Can't change slug for existing persona
            />
            <p className="text-xs text-gray-500 mt-1">
              URL-safe identifier (lowercase, hyphens only){persona && ' - Cannot be changed'}
            </p>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of this persona's expertise..."
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Category */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Category
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value as PersonaCategory)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
            >
              <option value="custom">Custom</option>
              <option value="domain">Domain</option>
              <option value="role">Role</option>
            </select>
          </div>

          {/* Icon & Color */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Icon (Lucide name)
              </label>
              <input
                type="text"
                value={icon}
                onChange={(e) => setIcon(e.target.value)}
                placeholder="e.g., user, chart, code"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Color (hex)
              </label>
              <div className="flex space-x-2">
                <input
                  type="color"
                  value={color}
                  onChange={(e) => setColor(e.target.value)}
                  className="h-10 w-16 border border-gray-300 rounded-md"
                />
                <input
                  type="text"
                  value={color}
                  onChange={(e) => setColor(e.target.value)}
                  placeholder="#6366f1"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !name || !slug}
            className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-2"
          >
            {saving && <Loader className="h-4 w-4 animate-spin" />}
            <Save className="h-4 w-4" />
            <span>{saving ? 'Saving...' : persona ? 'Update' : 'Create'}</span>
          </button>
        </div>
      </div>
    </div>
  )
}

export default PersonaEditor
