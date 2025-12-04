import React from 'react'
import { Check } from 'lucide-react'
import * as Icons from 'lucide-react'
import { Persona } from '../types/persona'

interface PersonaCardProps {
  persona: Persona
  isSelected: boolean
  onSelect: () => void
  selectionMode: 'radio' | 'checkbox'  // radio for base, checkbox for domains
}

/**
 * PersonaCard - Display individual persona with selection state
 *
 * Design: Clean card with icon, name, description, and selection indicator
 * Simple click-to-select interaction
 */
const PersonaCard: React.FC<PersonaCardProps> = ({
  persona,
  isSelected,
  onSelect,
  selectionMode,
}) => {
  // Get icon component dynamically
  const getIcon = (iconName: string) => {
    const IconComponent = (Icons as any)[iconName]
    return IconComponent || Icons.User
  }

  const Icon = getIcon(persona.icon)

  return (
    <button
      onClick={onSelect}
      className={`relative w-full text-left p-4 rounded-lg border-2 transition-all ${
        isSelected
          ? 'border-blue-500 bg-blue-50'
          : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'
      }`}
    >
      {/* Selection indicator */}
      {isSelected && (
        <div className="absolute top-2 right-2">
          <div className="bg-blue-500 text-white rounded-full p-1">
            <Check className="h-3 w-3" />
          </div>
        </div>
      )}

      {/* Icon with persona color */}
      <div className="flex items-start space-x-3">
        <div
          className="flex-shrink-0 p-2 rounded-lg"
          style={{ backgroundColor: `${persona.color}20` }}
        >
          <Icon className="h-5 w-5" style={{ color: persona.color }} />
        </div>

        <div className="flex-1 min-w-0">
          {/* Name */}
          <h4 className="text-sm font-semibold text-gray-900 mb-1">
            {persona.name}
          </h4>

          {/* Description */}
          <p className="text-xs text-gray-600 line-clamp-2">
            {persona.description}
          </p>

          {/* Category badge */}
          <div className="mt-2">
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
              {persona.category}
            </span>
            {persona.is_system && (
              <span className="ml-1 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                system
              </span>
            )}
          </div>
        </div>
      </div>
    </button>
  )
}

export default PersonaCard
