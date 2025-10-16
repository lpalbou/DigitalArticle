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
  show_code: boolean
  markdown: string
  scientific_explanation: string
  tags: string[]
  metadata: Record<string, any>
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

export interface FileInfo {
  name: string
  path: string
  size: number
  type: 'csv' | 'json' | 'xlsx' | 'txt' | 'other'
  lastModified: string
  preview?: {
    rows: number
    columns: string[]
    shape: [number, number]
  }
}