/**
 * Persona type definitions for Digital Article frontend.
 */

export type PersonaCategory = 'base' | 'domain' | 'role' | 'custom'

export type PersonaScope =
  | 'code_generation'
  | 'methodology'
  | 'chat'
  | 'abstract'
  | 'review'
  | 'all'

export type ReviewPhase = 'intent' | 'implementation' | 'results' | 'synthesis'

export type ReviewSeverity = 'info' | 'warning' | 'critical'

export type ReviewCategory =
  | 'methodology'
  | 'statistics'
  | 'interpretation'
  | 'reproducibility'
  | 'data_quality'
  | 'visualization'
  | 'code_quality'

export interface PersonaGuidance {
  scope: PersonaScope
  system_prompt_addition: string
  user_prompt_prefix: string
  user_prompt_suffix: string
  constraints: string[]
  preferences: string[]
  examples: string[]
}

export interface ReviewCapability {
  phase: ReviewPhase
  prompt_template: string
  output_format: 'structured' | 'narrative' | 'checklist'
  severity_levels: string[]
}

export interface Persona {
  id: string
  name: string
  slug: string
  description: string
  icon: string
  color: string
  category: PersonaCategory
  priority: number
  is_system: boolean
  is_active: boolean
  expertise_description: string
  domain_context: string
  methodology_style: string
  guidance: PersonaGuidance[]
  preferred_libraries: string[]
  avoid_libraries: string[]
  preferred_methods: string[]
  review_capabilities: ReviewCapability[]
  created_at: string
  updated_at: string
  created_by: string
  version: number
  tags: string[]
  compatible_with: string[]
  incompatible_with: string[]
}

export interface PersonaSelection {
  base_persona: string
  domain_personas: string[]
  role_modifier: string | null
  custom_overrides: Record<string, any>
}

export interface PersonaCombination {
  effective_guidance: Record<PersonaScope, PersonaGuidance>
  source_personas: string[]
  conflict_resolutions: string[]
}

export interface PersonaCreateRequest {
  name: string
  slug: string
  description?: string
  icon?: string
  color?: string
  category?: PersonaCategory
  priority?: number
  expertise_description?: string
  domain_context?: string
  methodology_style?: string
  guidance?: PersonaGuidance[]
  preferred_libraries?: string[]
  avoid_libraries?: string[]
  preferred_methods?: string[]
  review_capabilities?: ReviewCapability[]
  tags?: string[]
  compatible_with?: string[]
  incompatible_with?: string[]
}

export interface PersonaUpdateRequest {
  name?: string
  description?: string
  icon?: string
  color?: string
  priority?: number
  is_active?: boolean
  expertise_description?: string
  domain_context?: string
  methodology_style?: string
  guidance?: PersonaGuidance[]
  preferred_libraries?: string[]
  avoid_libraries?: string[]
  preferred_methods?: string[]
  review_capabilities?: ReviewCapability[]
  tags?: string[]
  compatible_with?: string[]
  incompatible_with?: string[]
}

export interface PersonaSelectionUpdateRequest {
  base_persona: string
  domain_personas?: string[]
  role_modifier?: string | null
  custom_overrides?: Record<string, any>
}

// Review types

export interface ReviewFinding {
  severity: ReviewSeverity
  category: ReviewCategory
  message: string
  suggestion?: string
  cell_id?: string
  line_number?: number
}

export interface CellReview {
  cell_id: string
  findings: ReviewFinding[]
  overall_quality: 'good' | 'acceptable' | 'needs_attention'
  reviewed_at: string
  reviewer_persona?: string
}

export interface ArticleReview {
  notebook_id: string
  overall_assessment: string
  rating: number  // 1-5
  strengths: string[]
  issues: ReviewFinding[]
  recommendations: string[]
  reviewed_at: string
  reviewer_persona?: string
}

export interface ReviewPhaseSettings {
  intent_enabled: boolean
  implementation_enabled: boolean
  results_enabled: boolean
}

export interface ReviewDisplaySettings {
  show_severity: 'all' | 'warnings_and_critical' | 'critical_only'
  auto_collapse: boolean
  show_suggestions: boolean
}

export interface ReviewSettings {
  auto_review_enabled: boolean
  phases: ReviewPhaseSettings
  display: ReviewDisplaySettings
  review_style: 'constructive' | 'brief' | 'detailed'
}

export interface ReviewCellRequest {
  cell_id: string
  notebook_id: string
  force?: boolean
}

export interface ReviewArticleRequest {
  notebook_id: string
  force?: boolean
}

export interface ReviewSettingsUpdateRequest {
  auto_review_enabled?: boolean
  phases?: ReviewPhaseSettings
  display?: ReviewDisplaySettings
  review_style?: string
}
