// Enums for values that components can reference
export enum CellType {
  PROMPT = 'prompt',
  METHODOLOGY = 'methodology',
  CODE = 'code', 
  MARKDOWN = 'markdown'
}

export enum ExecutionStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  SUCCESS = 'success',
  ERROR = 'error',
  CANCELLED = 'cancelled'
}

export enum CellState {
  FRESH = 'fresh',
  STALE = 'stale',
  EXECUTING = 'executing'
}

export type LintSeverity = 'error' | 'warning' | 'info'

export interface LintIssue {
  severity: LintSeverity
  message: string
  rule_id?: string
  line?: number
  column?: number
  suggestion?: string
  fixable?: boolean
}

export interface LintReport {
  engine: string
  issues: LintIssue[]
}

export interface AutofixChange {
  rule_id: string
  message: string
  line?: number
}

export interface AutofixReport {
  enabled: boolean
  applied: boolean
  original_code?: string
  fixed_code?: string
  diff?: string
  changes: AutofixChange[]
  lint_before?: LintReport
  lint_after?: LintReport
}

export interface ExecutionResult {
  timestamp: string
  status: ExecutionStatus
  stdout: string
  stderr: string
  execution_time: number
  
  // Rich output data  
  plots: string[] // Base64 encoded plot images
  tables: TableData[]
  images: string[] // Base64 encoded images
  interactive_plots: PlotlyData[]
  
  // Error information
  error_type?: string
  error_message?: string
  traceback?: string

  // Statistical and validation warnings (non-fatal issues)
  warnings?: string[]

  // Static code quality feedback (lint report)
  lint_report?: LintReport

  // Deterministic safe code rewrites (autofix)
  autofix_report?: AutofixReport
}

export interface PlotlyData {
  name: string
  figure: any
  json: string
}

// LLM Trace interfaces (matching AbstractCore structure)
export interface LLMTraceUsage {
  prompt_tokens?: number
  completion_tokens?: number
  total_tokens: number
  input_tokens?: number  // AbstractCore 2.5.2+ format
  output_tokens?: number  // AbstractCore 2.5.2+ format
}

export interface LLMTraceResponse {
  content: string
  tool_calls?: any[]
  finish_reason: string
  usage: LLMTraceUsage
  generation_time_ms: number
}

export interface LLMTraceMetadata {
  session_id?: string
  step_type: 'code_generation' | 'code_fix' | 'methodology_generation'
  attempt_number: number
  notebook_id: string
  cell_id: string
  [key: string]: any  // Allow additional custom metadata
}

export interface LLMTrace {
  trace_id: string
  timestamp: string
  provider: string
  model: string
  system_prompt?: string
  prompt: string
  messages?: any[]
  parameters: Record<string, any>
  response: LLMTraceResponse
  metadata: LLMTraceMetadata
}

export interface TableData {
  name: string
  shape: [number, number]
  columns: string[]
  data: any[]
  html: string
  info: {
    dtypes: Record<string, string>
    memory_usage: Record<string, number>
  }
}

export interface FileInfo {
  name: string
  path: string
  size: number
  type:
    | 'csv'
    | 'tsv'
    | 'json'
    | 'yaml'
    | 'yml'
    | 'xlsx'
    | 'xls'
    | 'txt'
    | 'md'
    | 'h5'
    | 'hdf5'
    | 'h5ad'
    | 'image'
    | 'dicom'
    | 'nifti'
    | 'other'
  lastModified: string
  is_h5_file?: boolean
  preview?: {
    rows?: number
    columns?: string[]
    shape?: [number, number]
    [key: string]: any // Allow additional H5 metadata
  }
}

export interface Cell {
  id: string
  prompt: string
  code: string
  is_code_visible: boolean
  execution_result?: ExecutionResult
  created_at: string
  updated_at: string
  
  // Additional properties expected by components
  cell_type: CellType
  execution_count: number
  last_result?: ExecutionResult
  is_executing: boolean
  is_writing_methodology: boolean
  is_retrying: boolean  // Track if auto-retry is in progress
  retry_count: number   // Number of retry attempts
  cell_state: CellState // Content freshness state
  show_code: boolean
  markdown: string
  scientific_explanation: string
  tags: string[]
  metadata: Record<string, any>
  
  // Generation metadata (AbstractCore 2.5.2+)
  last_generation_time_ms?: number  // Generation time in milliseconds
  last_execution_timestamp?: string  // When the cell was last executed

  // LLM Execution Traces (persistent storage of all LLM interactions)
  llm_traces?: LLMTrace[]
}

export interface Notebook {
  id: string
  title: string
  cells: Cell[]
  created_at: string
  updated_at: string

  // Additional properties expected by components
  description: string
  author: string
  version: string
  tags: string[]
  metadata: Record<string, any>
  llm_model: string
  llm_provider: string
  last_context_tokens?: number  // Last known context size from generation
  abstract?: string  // Generated scientific abstract
  abstract_generated_at?: string  // When abstract was last generated
}

// API Request types
export interface CellCreateRequest {
  cell_type: CellType
  content: string
  notebook_id: string
}

export interface CellUpdateRequest {
  prompt?: string
  code?: string
  markdown?: string
  cell_type?: CellType
  show_code?: boolean
  tags?: string[]
  metadata?: Record<string, any>
}

export interface CellExecuteRequest {
  cell_id: string
  force_regenerate?: boolean
  autofix?: boolean
  clean_rerun?: boolean
  rerun_comment?: string
}

export interface CellExecuteResponse {
  cell: Cell
  result: ExecutionResult
}

// Cell status polling (for realtime-ish UX while /cells/execute is in-flight)
export interface CellStatusResponse {
  cell_id: string
  is_executing: boolean
  is_retrying: boolean
  retry_count: number
  max_retries: number
  is_writing_methodology: boolean
  methodology_attempt: number
  max_methodology_retries: number
  execution_phase?: string | null
  execution_message?: string | null
  execution_updated_at?: string | null
  has_scientific_explanation: boolean
  scientific_explanation_length: number
  scientific_explanation?: string
}

export interface NotebookCreateRequest {
  title?: string
  description?: string
  author?: string
  llm_model?: string
  llm_provider?: string
}

export interface NotebookUpdateRequest {
  title?: string
  description?: string
  author?: string
  tags?: string[]
  llm_model?: string
  llm_provider?: string
}

export interface CodeGenerationRequest {
  prompt: string
  context?: Record<string, any>
}

export interface CodeExplanationRequest {
  code: string
}

export interface CodeImprovementRequest {
  prompt: string
  code: string
  error_message?: string
}

// Chat types
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  loading?: boolean
}

export interface ChatRequest {
  notebook_id: string
  message: string
  conversation_history?: ChatMessage[]
  mode?: 'article' | 'reviewer'
}

export interface ChatResponse {
  message: string
  context_used: string[]  // Cell IDs or data sources referenced
  timestamp: string
}
