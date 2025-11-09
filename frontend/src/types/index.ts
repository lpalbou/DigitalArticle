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

export interface ExecutionResult {
  success: boolean
  outputs: any[]
  error?: string
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
  type: 'csv' | 'json' | 'xlsx' | 'txt' | 'h5' | 'hdf5' | 'h5ad' | 'other'
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
  prompt: string
  cell_type: CellType
  content: string
  notebook_id: string
}

export interface CellUpdateRequest {
  prompt?: string
  code?: string
  markdown?: string
  show_code?: boolean
  tags?: string[]
  metadata?: Record<string, any>
}

export interface CellExecuteRequest {
  cell_id: string
  force_regenerate?: boolean
}

export interface CellExecuteResponse {
  cell: Cell
  result: ExecutionResult
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
