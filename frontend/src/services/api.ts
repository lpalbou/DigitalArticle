/**
 * API client service for communicating with the Reverse Analytics Notebook backend.
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
  CodeGenerationRequest,
  CodeExplanationRequest,
  CodeImprovementRequest
} from '../types'

// Create axios instance with base configuration
const api = axios.create({
  baseURL: '/api',
  timeout: 30000, // 30 second timeout
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
  export: async (notebookId: string, format: 'json' | 'html' | 'markdown' = 'json'): Promise<string> => {
    const response: AxiosResponse<string> = await api.get(`/notebooks/${notebookId}/export`, {
      params: { format }
    })
    return response.data
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
  execute: async (request: CellExecuteRequest): Promise<ExecutionResult> => {
    const response: AxiosResponse<ExecutionResult> = await api.post('/cells/execute', request)
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

  // Get LLM status
  getStatus: async (): Promise<{ provider: string; model: string; status: string }> => {
    const response: AxiosResponse<{ provider: string; model: string; status: string }> = await api.get('/llm/status')
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

export default api
