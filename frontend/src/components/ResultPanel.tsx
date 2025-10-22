import React, { useMemo, useState } from 'react'
import Plot from 'react-plotly.js'
import { 
  AlertCircle, 
  CheckCircle, 
  Image as ImageIcon, 
  BarChart3, 
  Table, 
  ChevronRight, 
  ChevronDown,
  ChevronUp,
  ChevronsUpDown,
  Search,
  Eye as EyeIcon
} from 'lucide-react'
import { ExecutionResult, ExecutionStatus, TableData } from '../types'

interface ResultPanelProps {
  result: ExecutionResult
}

const ResultPanel: React.FC<ResultPanelProps> = ({ result }) => {
  const [warningsCollapsed, setWarningsCollapsed] = useState(true)

  const hasOutput = useMemo(() => {
    return result.stdout ||
           result.plots.length > 0 ||
           result.tables.length > 0 ||
           result.interactive_plots.length > 0 ||
           result.images.length > 0
  }, [result])

  const hasError = result.status === ExecutionStatus.ERROR

  if (result.status === ExecutionStatus.PENDING) {
    return null
  }

  return (
    <div className="result-panel">
      {/* Status Header - Only show for errors */}
      {hasError && (
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <AlertCircle className="h-5 w-5 text-red-500" />
            <span className="font-medium text-red-700">
              Execution Failed
            </span>
            <span className="text-sm text-gray-500">
              ({result.execution_time.toFixed(2)}s)
            </span>
          </div>
        </div>
      )}

      {/* Error Display */}
      {hasError && (
        <div className="error-message mb-4">
          <div className="font-medium mb-2">
            {result.error_type}: {result.error_message}
          </div>
          {result.traceback && (
            <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
              {result.traceback}
            </pre>
          )}
        </div>
      )}

      {/* Tables - Intermediary/Source Data (shown first) */}
      {result.tables.length > 0 && (
        <DataTablesSection tables={result.tables} />
      )}

      {/* Standard Output - Analysis Results */}
      {result.stdout && (
        <div className="mb-4">
          <div className="flex items-center space-x-2 mb-2">
            <span className="text-sm font-medium text-gray-700">Analysis Results</span>
          </div>
          <ConsoleOutput output={result.stdout} />
        </div>
      )}

      {/* Standard Error (non-fatal) - Collapsible Warnings */}
      {result.stderr && !hasError && (
        <div className="mb-4">
          <div
            className="flex items-center space-x-2 mb-2 cursor-pointer hover:bg-gray-50 p-2 rounded -ml-2"
            onClick={() => setWarningsCollapsed(!warningsCollapsed)}
          >
            {warningsCollapsed ? (
              <ChevronRight className="h-4 w-4 text-gray-500" />
            ) : (
              <ChevronDown className="h-4 w-4 text-gray-500" />
            )}
            <span className="text-sm font-medium text-gray-700">Warnings</span>
            <span className="text-xs text-gray-500">
              ({warningsCollapsed ? 'click to expand' : 'click to collapse'})
            </span>
          </div>
          {!warningsCollapsed && (
            <pre className="bg-yellow-50 border border-yellow-200 p-3 rounded text-sm overflow-x-auto whitespace-pre-wrap">
              {result.stderr}
            </pre>
          )}
        </div>
      )}

      {/* Matplotlib Plots */}
      {result.plots.length > 0 && (
        <div className="mb-4">
          <div className="flex items-center space-x-2 mb-2">
            <BarChart3 className="h-4 w-4" />
            <span className="text-sm font-medium text-gray-700">Plots</span>
          </div>
          <div className="grid gap-4">
            {result.plots.map((plot, index) => (
              <div key={index} className="plot-container">
                <img
                  src={`data:image/png;base64,${plot}`}
                  alt={`Plot ${index + 1}`}
                  className="max-w-full h-auto"
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Interactive Plotly Plots */}
      {result.interactive_plots.length > 0 && (
        <div className="mb-4">
          <div className="flex items-center space-x-2 mb-2">
            <BarChart3 className="h-4 w-4" />
            <span className="text-sm font-medium text-gray-700">Interactive Plots</span>
          </div>
          <div className="grid gap-4">
            {result.interactive_plots.map((plot, index) => (
              <div key={index} className="plot-container">
                <Plot
                  data={plot.figure.data}
                  layout={plot.figure.layout}
                  config={{
                    responsive: true,
                    displayModeBar: true,
                    displaylogo: false
                  }}
                  style={{ width: '100%', height: '400px' }}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Images */}
      {result.images.length > 0 && (
        <div className="mb-4">
          <div className="flex items-center space-x-2 mb-2">
            <ImageIcon className="h-4 w-4" />
            <span className="text-sm font-medium text-gray-700">Images</span>
          </div>
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
            {result.images.map((image, index) => (
              <div key={index} className="plot-container">
                <img
                  src={`data:image/png;base64,${image}`}
                  alt={`Image ${index + 1}`}
                  className="max-w-full h-auto"
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No Output Message */}
      {!hasError && !hasOutput && (
        <div className="text-center text-gray-500 py-8">
          <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-500" />
          <p>Code executed successfully with no output</p>
        </div>
      )}
    </div>
  )
}

// Component for displaying data tables with advanced features
const TableDisplay: React.FC<{ table: TableData }> = ({ table }) => {
  const [showFullTable, setShowFullTable] = React.useState(false)
  const [searchTerm, setSearchTerm] = React.useState('')
  const [sortConfig, setSortConfig] = React.useState<{column: string, direction: 'asc' | 'desc'} | null>(null)
  const [hiddenColumns, setHiddenColumns] = React.useState<Set<string>>(new Set())
  const [currentPage, setCurrentPage] = React.useState(1)
  const [pageSize, setPageSize] = React.useState(10)
  const [columnWidths, setColumnWidths] = React.useState<Record<string, number>>({})

  // Filter data based on search term
  const filteredData = React.useMemo(() => {
    if (!searchTerm) return table.data
    
    return table.data.filter(row =>
      table.columns.some(column => {
        const value = formatCellValue(row[column]).toLowerCase()
        return value.includes(searchTerm.toLowerCase())
      })
    )
  }, [table.data, table.columns, searchTerm])

  // Sort data
  const sortedData = React.useMemo(() => {
    if (!sortConfig) return filteredData

    return [...filteredData].sort((a, b) => {
      const aVal = a[sortConfig.column]
      const bVal = b[sortConfig.column]
      
      // Handle null/undefined values
      if (aVal == null && bVal == null) return 0
      if (aVal == null) return sortConfig.direction === 'asc' ? -1 : 1
      if (bVal == null) return sortConfig.direction === 'asc' ? 1 : -1
      
      // Compare values
      let comparison = 0
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        comparison = aVal - bVal
      } else {
        comparison = String(aVal).localeCompare(String(bVal))
      }
      
      return sortConfig.direction === 'asc' ? comparison : -comparison
    })
  }, [filteredData, sortConfig])

  // Paginate data
  const paginatedData = React.useMemo(() => {
    if (showFullTable) return sortedData
    
    const startIndex = (currentPage - 1) * pageSize
    return sortedData.slice(startIndex, startIndex + pageSize)
  }, [sortedData, currentPage, pageSize, showFullTable])

  // Visible columns
  const visibleColumns = React.useMemo(() => {
    return table.columns.filter(column => !hiddenColumns.has(column))
  }, [table.columns, hiddenColumns])

  const totalPages = Math.ceil(sortedData.length / pageSize)

  const handleSort = (column: string) => {
    setSortConfig(current => {
      if (current?.column === column) {
        return current.direction === 'asc' 
          ? { column, direction: 'desc' }
          : null
      }
      return { column, direction: 'asc' }
    })
  }

  const toggleColumn = (column: string) => {
    setHiddenColumns(current => {
      const newSet = new Set(current)
      if (newSet.has(column)) {
        newSet.delete(column)
      } else {
        newSet.add(column)
      }
      return newSet
    })
  }

  const SortIcon = ({ column }: { column: string }) => {
    if (sortConfig?.column !== column) {
      return <ChevronsUpDown className="h-3 w-3 text-gray-400" />
    }
    return sortConfig.direction === 'asc' 
      ? <ChevronUp className="h-3 w-3 text-blue-600" />
      : <ChevronDown className="h-3 w-3 text-blue-600" />
  }

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden bg-white shadow-sm">
      {/* Enhanced Table Header with Controls */}
      <div className="bg-gray-50 px-4 py-3 border-b space-y-3">
        {/* Title and Info Row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <span className="font-medium text-sm text-gray-900">{table.name}</span>
            <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
              {sortedData.length} rows × {visibleColumns.length} columns
            </span>
          </div>
          
          <div className="flex items-center space-x-2">
            {/* Column Visibility Toggle */}
            <div className="relative group">
              <button className="text-xs text-gray-600 hover:text-gray-800 flex items-center space-x-1 px-2 py-1 rounded hover:bg-gray-100">
                <EyeIcon className="h-3 w-3" />
                <span>Columns</span>
              </button>
              <div className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-md shadow-lg z-10 hidden group-hover:block min-w-48">
                <div className="p-2 space-y-1 max-h-48 overflow-y-auto">
                  {table.columns.map(column => (
                    <label key={column} className="flex items-center space-x-2 text-xs hover:bg-gray-50 p-1 rounded cursor-pointer">
                      <input
                        type="checkbox"
                        checked={!hiddenColumns.has(column)}
                        onChange={() => toggleColumn(column)}
                        className="w-3 h-3 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                      />
                      <span className="truncate">{column}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            {/* Full Table Toggle */}
            {table.data.length > pageSize && (
              <button
                onClick={() => setShowFullTable(!showFullTable)}
                className="text-xs text-blue-600 hover:text-blue-700 px-2 py-1 rounded hover:bg-blue-50"
              >
                {showFullTable ? 'Paginate' : `Show All ${table.data.length}`}
              </button>
            )}
          </div>
        </div>

        {/* Search and Controls Row */}
        <div className="flex items-center justify-between space-x-4">
          {/* Search */}
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 h-3 w-3 text-gray-400" />
            <input
              type="text"
              placeholder="Search table data..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-7 pr-3 py-1 text-xs border border-gray-300 rounded-md focus:ring-1 focus:ring-blue-500 focus:border-blue-500 w-full"
            />
          </div>

          {/* Page Size Selector */}
          {!showFullTable && (
            <div className="flex items-center space-x-2 text-xs">
              <span className="text-gray-600">Show:</span>
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value))
                  setCurrentPage(1)
                }}
                className="border border-gray-300 rounded px-2 py-1 text-xs focus:ring-1 focus:ring-blue-500"
              >
                <option value={5}>5</option>
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
              </select>
            </div>
          )}
        </div>
      </div>

      {/* Enhanced Table Content */}
      <div className="relative">
        <div className="overflow-x-auto max-h-[70vh] enhanced-table-scroll">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50 sticky top-0 z-10">
              <tr>
                {visibleColumns.map((column) => (
                  <th
                    key={column}
                    className="group px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none border-r border-gray-200 last:border-r-0"
                    onClick={() => handleSort(column)}
                    style={{ minWidth: columnWidths[column] || 120 }}
                  >
                    <div className="flex items-center justify-between">
                      <span className="truncate pr-2" title={column}>{column}</span>
                      <SortIcon column={column} />
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {paginatedData.map((row, index) => (
                <tr key={index} className="hover:bg-gray-50 transition-colors">
                  {visibleColumns.map((column) => (
                    <td
                      key={column}
                      className="px-4 py-3 text-sm text-gray-900 border-r border-gray-100 last:border-r-0"
                      style={{ minWidth: columnWidths[column] || 120 }}
                    >
                      <div className="truncate" title={formatCellValue(row[column])}>
                        {formatCellValue(row[column])}
                      </div>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Enhanced Footer with Pagination */}
      <div className="bg-gray-50 px-4 py-3 border-t">
        {!showFullTable && totalPages > 1 ? (
          <div className="flex items-center justify-between">
            <div className="text-xs text-gray-600">
              Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, sortedData.length)} of {sortedData.length} results
              {searchTerm && ` (filtered from ${table.data.length} total)`}
            </div>
            
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                className="px-2 py-1 text-xs border border-gray-300 rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
              >
                Previous
              </button>
              
              <div className="flex items-center space-x-1">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  const page = i + Math.max(1, currentPage - 2)
                  if (page > totalPages) return null
                  
                  return (
                    <button
                      key={page}
                      onClick={() => setCurrentPage(page)}
                      className={`px-2 py-1 text-xs border rounded ${
                        currentPage === page
                          ? 'bg-blue-600 text-white border-blue-600'
                          : 'border-gray-300 hover:bg-gray-100'
                      }`}
                    >
                      {page}
                    </button>
                  )
                })}
              </div>
              
              <button
                onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                disabled={currentPage === totalPages}
                className="px-2 py-1 text-xs border border-gray-300 rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
              >
                Next
              </button>
            </div>
          </div>
        ) : (
          <div className="text-xs text-gray-600 text-center">
            {showFullTable ? `Showing all ${sortedData.length} rows` : `Showing ${paginatedData.length} rows`}
            {searchTerm && ` (filtered from ${table.data.length} total)`}
          </div>
        )}
      </div>
    </div>
  )
}

// Helper function to format cell values
const formatCellValue = (value: any): string => {
  if (value === null || value === undefined) {
    return '-'
  }
  if (typeof value === 'number') {
    return Number.isInteger(value) ? value.toString() : value.toFixed(4)
  }
  if (typeof value === 'boolean') {
    return value ? 'True' : 'False'
  }
  return String(value)
}

// Smart console output component that detects and handles tabular data
const ConsoleOutput: React.FC<{ output: string }> = ({ output }) => {
  const [viewMode, setViewMode] = React.useState<'auto' | 'raw' | 'table'>('auto')
  
  // Detect if output looks like tabular data based on repetitive patterns/structure
  const isTabularData = React.useMemo(() => {
    const lines = output.trim().split('\n').filter(line => line.trim())
    if (lines.length < 2) return false
    
    // Check for consistent structure across multiple lines
    const hasConsistentSpacing = () => {
      const dataLines = lines.filter(line => line.trim() && !line.includes('Generated') && !line.includes('First few'))
      if (dataLines.length < 2) return false
      
      // Analyze spacing patterns in each line
      const spacingPatterns = dataLines.map(line => {
        const matches = [...line.matchAll(/\s{2,}/g)]
        return matches.map(match => match.index).sort((a, b) => a - b)
      })
      
      if (spacingPatterns.length < 2) return false
      
      // Check if spacing patterns are similar (allowing some variance)
      const firstPattern = spacingPatterns[0]
      if (!firstPattern || firstPattern.length < 1) return false
      
      return spacingPatterns.slice(1).every(pattern => {
        if (!pattern || Math.abs(pattern.length - firstPattern.length) > 2) return false
        
        // Check if column positions are roughly aligned (within 3 characters)
        return pattern.every((pos, i) => {
          const expectedPos = firstPattern[i]
          return expectedPos !== undefined && Math.abs(pos - expectedPos) <= 3
        })
      })
    }
    
    // Check for repetitive data patterns
    const hasRepetitiveStructure = () => {
      const dataLines = lines.filter(line => line.trim() && !line.includes('Generated') && !line.includes('First few'))
      if (dataLines.length < 2) return false
      
      // Look for lines that start with similar patterns (like row indices, IDs, etc.)
      const startsWithNumbers = dataLines.filter(line => /^\s*\d+/.test(line)).length
      const startsWithWords = dataLines.filter(line => /^\s*[A-Z]\w+/.test(line)).length
      
      // If most lines start with numbers or consistent word patterns, it's likely tabular
      return (startsWithNumbers >= dataLines.length * 0.6) || (startsWithWords >= dataLines.length * 0.6)
    }
    
    // Check for multiple columns of data
    const hasMultipleColumns = () => {
      const dataLines = lines.filter(line => line.trim() && !line.includes('Generated') && !line.includes('First few'))
      return dataLines.some(line => (line.match(/\s{2,}/g) || []).length >= 1)
    }
    
    // Check for mixed data types (numbers, words) which is common in tables
    const hasMixedDataTypes = () => {
      const content = lines.join(' ')
      const hasNumbers = /\d+(\.\d+)?/.test(content)
      const hasWords = /[A-Za-z]{2,}/.test(content)
      return hasNumbers && hasWords
    }
    
    return hasConsistentSpacing() || (hasRepetitiveStructure() && hasMultipleColumns() && hasMixedDataTypes())
  }, [output])
  
  // Parse tabular data into structured format
  const parseTabularData = React.useMemo(() => {
    if (!isTabularData) return null
    
    const lines = output.trim().split('\n').filter(line => line.trim())
    if (lines.length < 2) return null
    
    // Filter out descriptive lines, keep only data lines
    const dataLines = lines.filter(line => 
      line.trim() && 
      !line.includes('Generated') && 
      !line.includes('First few') &&
      !line.includes('dataset with')
    )
    
    if (dataLines.length < 2) return null
    
    // Find the header line - look for a line with column names (letters/underscores)
    let headerIndex = -1
    for (let i = 0; i < Math.min(3, dataLines.length); i++) {
      const line = dataLines[i].trim()
      // Look for lines that contain column headers (mix of letters, numbers, underscores)
      if (/[A-Z_]/.test(line) && (line.match(/\s{2,}/g) || []).length >= 1) {
        headerIndex = i
        break
      }
    }
    
    // If no clear header found, create generic column names based on first data row
    let columns: string[] = []
    let actualDataLines: string[] = []
    
    if (headerIndex === -1) {
      // Use first data line to determine column structure
      const firstDataLine = dataLines[0]
      const spaceMatches = [...firstDataLine.matchAll(/\s{2,}/g)]
      const numColumns = spaceMatches.length + 1
      columns = Array.from({ length: numColumns }, (_, i) => `Column ${i + 1}`)
      actualDataLines = dataLines
    } else {
      const headerLine = dataLines[headerIndex]
      actualDataLines = dataLines.slice(headerIndex + 1)
      
      // Extract column positions by finding consistent spacing
      const columnPositions: number[] = []
      const headerSpaces = [...headerLine.matchAll(/\s{2,}/g)]
      
      columnPositions.push(0) // First column starts at 0
      headerSpaces.forEach(match => {
        if (match.index !== undefined) {
          columnPositions.push(match.index + match[0].length)
        }
      })
      
      // Extract column names
      for (let i = 0; i < columnPositions.length; i++) {
        const start = columnPositions[i]
        const end = columnPositions[i + 1] || headerLine.length
        const columnName = headerLine.slice(start, end).trim()
        if (columnName) columns.push(columnName)
      }
    }
    
    // Use the first data line to establish column positions
    const referenceLine = actualDataLines[0] || dataLines[0]
    const columnPositions: number[] = []
    const spaces = [...referenceLine.matchAll(/\s{2,}/g)]
    
    columnPositions.push(0)
    spaces.forEach(match => {
      if (match.index !== undefined) {
        columnPositions.push(match.index + match[0].length)
      }
    })
    
    // Ensure we have enough columns
    while (columns.length < columnPositions.length) {
      columns.push(`Column ${columns.length + 1}`)
    }
    
    // Extract data rows
    const rows: string[][] = []
    actualDataLines.forEach(line => {
      if (!line.trim()) return
      
      const row: string[] = []
      for (let i = 0; i < columnPositions.length; i++) {
        const start = columnPositions[i]
        const end = columnPositions[i + 1] || line.length
        const cellValue = line.slice(start, end).trim()
        row.push(cellValue || '-')
      }
      
      // Ensure row has same number of columns as headers
      while (row.length < columns.length) {
        row.push('-')
      }
      
      if (row.some(cell => cell && cell !== '-')) { // Only add non-empty rows
        rows.push(row.slice(0, columns.length)) // Trim to match column count
      }
    })
    
    return { columns, rows }
  }, [output, isTabularData])
  
  const effectiveViewMode = viewMode === 'auto' ? (isTabularData ? 'table' : 'raw') : viewMode
  
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      {/* View Mode Controls */}
      <div className="bg-gray-50 px-3 py-2 border-b flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-600">Console Output</span>
          {isTabularData && (
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
              Tabular data detected
            </span>
          )}
          <span className="text-xs text-gray-400">
            Mode: {effectiveViewMode}
          </span>
        </div>
        
        <div className="flex items-center space-x-1">
          <button
            onClick={() => setViewMode('auto')}
            className={`text-xs px-2 py-1 rounded transition-colors ${
              viewMode === 'auto' 
                ? 'bg-blue-600 text-white' 
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            Auto
          </button>
          <button
            onClick={() => setViewMode('table')}
            className={`text-xs px-2 py-1 rounded transition-colors ${
              viewMode === 'table' 
                ? 'bg-blue-600 text-white' 
                : parseTabularData 
                  ? 'text-gray-600 hover:bg-gray-100'
                  : 'text-gray-400 cursor-not-allowed'
            }`}
            disabled={!parseTabularData}
          >
            Table
          </button>
          <button
            onClick={() => setViewMode('raw')}
            className={`text-xs px-2 py-1 rounded transition-colors ${
              viewMode === 'raw' 
                ? 'bg-blue-600 text-white' 
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            Raw
          </button>
        </div>
      </div>
      
      {/* Content Display */}
      <div className="bg-white">
        {effectiveViewMode === 'table' && parseTabularData ? (
          <div className="overflow-x-auto max-h-96 enhanced-table-scroll">
            <table className="min-w-full text-xs">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  {parseTabularData.columns.map((column, index) => (
                    <th
                      key={index}
                      className="px-3 py-2 text-left font-medium text-gray-700 border-r border-gray-200 last:border-r-0"
                      style={{ minWidth: '100px' }}
                    >
                      <div className="truncate" title={column}>
                        {column}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {parseTabularData.rows.map((row, rowIndex) => (
                  <tr key={rowIndex} className="hover:bg-gray-50">
                    {row.map((cell, cellIndex) => (
                      <td
                        key={cellIndex}
                        className="px-3 py-2 text-gray-900 border-r border-gray-100 last:border-r-0 font-mono"
                        style={{ minWidth: '100px' }}
                      >
                        <div className="truncate" title={cell}>
                          {cell || '-'}
                        </div>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="bg-gray-50 p-3">
            <div className="text-xs text-gray-500 mb-2 border-b border-gray-200 pb-2">
              Raw console output (no formatting applied)
            </div>
            <pre className="text-xs font-mono overflow-x-auto whitespace-pre text-gray-800 bg-white p-2 rounded border">
              {output}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}

// Collapsible Data Tables Section Component
const DataTablesSection: React.FC<{ tables: TableData[] }> = ({ tables }) => {
  const [isExpanded, setIsExpanded] = React.useState(false) // Folded by default
  
  return (
    <div className="mb-4">
      {/* Collapsible Header */}
      <div 
        className="flex items-center justify-between p-3 bg-gray-50 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center space-x-2">
          <Table className="h-4 w-4 text-gray-600" />
          <span className="text-sm font-medium text-gray-700">
            Intermediary Data Tables
          </span>
          <span className="text-xs text-gray-500 bg-gray-200 px-2 py-0.5 rounded">
            {tables.length} table{tables.length !== 1 ? 's' : ''}
          </span>
        </div>
        
        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-500">
            {isExpanded ? 'Click to fold' : 'Click to expand'}
          </span>
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-gray-500" />
          ) : (
            <ChevronRight className="h-4 w-4 text-gray-500" />
          )}
        </div>
      </div>
      
      {/* Collapsible Content */}
      {isExpanded && (
        <div className="mt-2 space-y-4 p-3 bg-gray-50 border border-gray-200 border-t-0 rounded-b-lg">
          <div className="text-xs text-gray-600 mb-3 p-2 bg-blue-50 border border-blue-200 rounded">
            <strong>Note:</strong> These are intermediate DataFrames and variables created during code execution, 
            not the final analysis results. The main results are shown in the "Analysis Results" section below.
          </div>
          
          {tables.map((table, index) => (
            <div key={index} className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              <TableDisplay table={table} />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ResultPanel
