/**
 * API client service for communicating with the Digital Article backend.
 * Provides methods for managing notebooks, cells, and LLM operations.
 */

import axios, { AxiosResponse } from 'axios'
import {
  Notebook,
  Cell,
  ExecutionResult,
  NotebookCreateRequest,
  NotebookUpdateRequest,
  CellCreateRequest,
  CellUpdateRequest,
  CellExecuteRequest,
  CellExecuteResponse,
  CodeGenerationRequest,
  CodeExplanationRequest,
  CodeImprovementRequest
} from '../types'

// Create axios instance with base configuration
const api = axios.create({
  baseURL: '/api',
  // No timeout - allow operations to run as long as needed
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// Notebook API
export const notebookAPI = {
  // Create a new notebook
  create: async (request: NotebookCreateRequest): Promise<Notebook> => {
    const response: AxiosResponse<Notebook> = await api.post('/notebooks/', request)
    return response.data
  },

  // Get all notebooks
  list: async (): Promise<Notebook[]> => {
    const response: AxiosResponse<Notebook[]> = await api.get('/notebooks/')
    return response.data
  },

  // Get notebook summaries for browsing
  getSummaries: async (): Promise<any[]> => {
    const response: AxiosResponse<any[]> = await api.get('/notebooks/summaries')
    return response.data
  },

  // Cell state management
  markCellsAsStale: async (notebookId: string, fromCellIndex: number): Promise<void> => {
    await api.post(`/notebooks/${notebookId}/cells/mark-stale`, null, {
      params: { from_cell_index: fromCellIndex }
    })
  },

  markCellAsFresh: async (notebookId: string, cellId: string): Promise<void> => {
    await api.post(`/notebooks/${notebookId}/cells/${cellId}/mark-fresh`)
  },

  bulkUpdateCellStates: async (notebookId: string, cellUpdates: Array<{cell_id: string, state: string}>): Promise<void> => {
    await api.post(`/notebooks/${notebookId}/cells/bulk-update-states`, cellUpdates)
  },

  getCellsBelow: async (notebookId: string, cellId: string): Promise<{cell_index: number, cells_below_count: number, cells_below: Array<{id: string, cell_type: string}>}> => {
    const response = await api.get(`/notebooks/${notebookId}/cells/${cellId}/cells-below`)
    return response.data
  },

  // Get a specific notebook by ID
  get: async (notebookId: string): Promise<Notebook> => {
    const response: AxiosResponse<Notebook> = await api.get(`/notebooks/${notebookId}`)
    return response.data
  },

  // Update a notebook
  update: async (notebookId: string, request: NotebookUpdateRequest): Promise<Notebook> => {
    const response: AxiosResponse<Notebook> = await api.put(`/notebooks/${notebookId}`, request)
    return response.data
  },

  // Delete a notebook
  delete: async (notebookId: string): Promise<void> => {
    await api.delete(`/notebooks/${notebookId}`)
  },

  // Export a notebook
  export: async (notebookId: string, format: 'json' | 'jsonld' | 'analysis' | 'profile' | 'html' | 'markdown' = 'json'): Promise<string> => {
    const response: AxiosResponse<any> = await api.get(`/notebooks/${notebookId}/export`, {
      params: { format }
    })

    // Handle the case where JSON/JSON-LD is automatically parsed by axios
    if ((format === 'json' || format === 'jsonld' || format === 'analysis' || format === 'profile') && typeof response.data === 'object') {
      return JSON.stringify(response.data, null, 2)
    }

    return response.data
  },

  exportPDF: async (notebookId: string, includeCode: boolean = false): Promise<Blob> => {
    const response: AxiosResponse<Blob> = await api.get(`/notebooks/${notebookId}/export`, {
      params: { format: 'pdf', include_code: includeCode },
      responseType: 'blob'
    })
    return response.data
  },

  // Generate abstract for the entire digital article
  generateAbstract: async (notebookId: string): Promise<string> => {
    const response: AxiosResponse<{ abstract: string }> = await api.post(`/notebooks/${notebookId}/generate-abstract`)
    return response.data.abstract
  },
}

// Cell API
export const cellAPI = {
  // Create a new cell
  create: async (request: CellCreateRequest): Promise<Cell> => {
    const response: AxiosResponse<Cell> = await api.post('/cells/', request)
    return response.data
  },

  // Update a cell
  update: async (notebookId: string, cellId: string, request: CellUpdateRequest): Promise<Cell> => {
    const response: AxiosResponse<Cell> = await api.put(`/cells/${notebookId}/${cellId}`, request)
    return response.data
  },

  // Delete a cell
  delete: async (notebookId: string, cellId: string): Promise<void> => {
    await api.delete(`/cells/${notebookId}/${cellId}`)
  },

  // Execute a cell
  execute: async (request: CellExecuteRequest): Promise<CellExecuteResponse> => {
    const response: AxiosResponse<CellExecuteResponse> = await api.post('/cells/execute', request)
    return response.data
  },

  // Get cell status (including methodology writing status)
  getStatus: async (cellId: string): Promise<{
    cell_id: string;
    is_executing: boolean;
    is_writing_methodology: boolean;
    has_scientific_explanation: boolean;
    scientific_explanation: string;
  }> => {
    const response = await api.get(`/cells/${cellId}/status`)
    return response.data
  },

  // Get variables in execution context
  getVariables: async (notebookId: string, cellId: string): Promise<{ variables: any }> => {
    const response: AxiosResponse<{ variables: any }> = await api.get(`/cells/${notebookId}/${cellId}/variables`)
    return response.data
  },

  // Clear execution context
  clearContext: async (notebookId: string): Promise<{ message: string }> => {
    const response: AxiosResponse<{ message: string }> = await api.post(`/cells/${notebookId}/clear`)
    return response.data
  },

  // Get LLM execution traces for a cell
  getTraces: async (cellId: string): Promise<{ cell_id: string; traces: any[]; source: string }> => {
    const response: AxiosResponse<{ cell_id: string; traces: any[]; source: string }> = await api.get(`/cells/${cellId}/traces`)
    return response.data
  },
}

// LLM API
export const llmAPI = {
  // Generate code from prompt
  generateCode: async (request: CodeGenerationRequest): Promise<{ code: string }> => {
    const response: AxiosResponse<{ code: string }> = await api.post('/llm/generate-code', request)
    return response.data
  },

  // Explain code
  explainCode: async (request: CodeExplanationRequest): Promise<{ explanation: string }> => {
    const response: AxiosResponse<{ explanation: string }> = await api.post('/llm/explain-code', request)
    return response.data
  },

  // Improve code
  improveCode: async (request: CodeImprovementRequest): Promise<{ improved_code: string }> => {
    const response: AxiosResponse<{ improved_code: string }> = await api.post('/llm/improve-code', request)
    return response.data
  },

  // Get current global LLM configuration
  getConfig: async (): Promise<{ provider: string; model: string; config_file: string }> => {
    const response = await api.get('/llm/config')
    return response.data
  },

  // Get LLM status with token configuration
  getStatus: async (notebookId?: string): Promise<{
    provider: string;
    model: string;
    status: string;
    max_tokens: number | null;
    max_input_tokens: number | null;
    max_output_tokens: number | null;
    token_summary?: string;
    error_message?: string;
    active_context_tokens?: number | null;
  }> => {
    const params = notebookId ? { notebook_id: notebookId } : {}
    const response = await api.get('/llm/status', { params })
    return response.data
  },
}

// Files API
export const filesAPI = {
  // List files for a notebook
  list: async (notebookId: string): Promise<any[]> => {
    const response: AxiosResponse<any[]> = await api.get(`/files/${notebookId}`)
    return response.data
  },

  // Get file content
  getContent: async (notebookId: string, filePath: string): Promise<{
    content: string;
    content_type: string;
    size: number;
  }> => {
    const response = await api.get(`/files/${notebookId}/content`, {
      params: { file_path: filePath }
    })
    return response.data
  },

  // Upload file
  upload: async (notebookId: string, file: File): Promise<any[]> => {
    const formData = new FormData()
    formData.append('file', file)
    
    const response: AxiosResponse<any[]> = await api.post(`/files/${notebookId}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  // Delete file
  delete: async (notebookId: string, fileName: string): Promise<{ message: string }> => {
    const response: AxiosResponse<{ message: string }> = await api.delete(`/files/${notebookId}/${fileName}`)
    return response.data
  },
}

// Error types for better error handling
export class APIError extends Error {
  constructor(
    message: string,
    public status?: number,
    public response?: any
  ) {
    super(message)
    this.name = 'APIError'
  }
}

// Utility functions
export const handleAPIError = (error: any): APIError => {
  if (error.response) {
    // Server responded with an error status
    const message = error.response.data?.detail || error.response.statusText || 'Unknown server error'
    
    // Log full error details to console for debugging
    console.error('🚨 API Error Details:', {
      status: error.response.status,
      message: message,
      fullResponse: error.response.data,
      url: error.response.config?.url
    })
    
    // If we have a detailed error response, use that as the message
    if (error.response.data && typeof error.response.data === 'object' && error.response.data.stack_trace) {
      return new APIError(
        `EXECUTION ERROR:\n${error.response.data.error_message}\n\nSTACK TRACE:\n${error.response.data.stack_trace}`,
        error.response.status,
        error.response.data
      )
    }
    
    return new APIError(message, error.response.status, error.response.data)
  } else if (error.request) {
    // Request was made but no response received
    console.error('🚨 Network Error:', error.request)
    return new APIError('Network error: Unable to connect to server')
  } else {
    // Something else happened
    console.error('🚨 Unknown Error:', error.message)
    return new APIError(error.message || 'Unknown error occurred')
  }
}

// Download file utility
export const downloadFile = (content: string, filename: string, mimeType: string = 'application/json') => {
  const blob = new Blob([content], { type: mimeType })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

/**
 * Get the current system user
 */
export const getCurrentUser = async (): Promise<string> => {
  try {
    // Try to get from backend first
    const response = await api.get('/system/user')
    return response.data.username
  } catch (error) {
    // Fallback to a reasonable default if backend doesn't support it
    console.warn('Could not get system user from backend, using fallback')
    
    // Use the known username as fallback
    return 'albou' // Fallback to known user
  }
}

export default api
