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
import ReviewPanel from './ReviewPanel'

interface ResultPanelProps {
  result: ExecutionResult
  cellReview?: any  // Cell review data from cell.metadata['review']
  onRefreshReview?: () => void  // Callback to refresh review
}

const ResultPanel: React.FC<ResultPanelProps> = ({ result, cellReview, onRefreshReview }) => {
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

      {/* Statistical Warnings Banner (Passive Mode) */}
      {!hasError && result.warnings && result.warnings.length > 0 && (
        <div className="mb-4 bg-orange-50 border-l-4 border-orange-400 rounded-r-lg shadow-sm">
          <div
            className="flex items-start justify-between p-4 cursor-pointer hover:bg-orange-100 transition-colors"
            onClick={() => setWarningsCollapsed(!warningsCollapsed)}
          >
            <div className="flex items-start space-x-3 flex-1">
              <AlertCircle className="h-5 w-5 text-orange-500 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <div className="font-semibold text-orange-800 mb-1">
                  Statistical Validation Warnings ({result.warnings.length})
                </div>
                <div className="text-sm text-orange-700">
                  {warningsCollapsed ? 'Click to expand and review warnings' : 'Review the warnings below before proceeding'}
                </div>
              </div>
            </div>
            {warningsCollapsed ? (
              <ChevronRight className="h-5 w-5 text-orange-600 flex-shrink-0" />
            ) : (
              <ChevronDown className="h-5 w-5 text-orange-600 flex-shrink-0" />
            )}
          </div>

          {!warningsCollapsed && (
            <div className="px-4 pb-4 space-y-2">
              {result.warnings.map((warning: string, idx: number) => (
                <div
                  key={idx}
                  className="p-3 bg-white rounded border border-orange-200 text-sm text-gray-700"
                >
                  {warning}
                </div>
              ))}
              <div className="mt-3 pt-3 border-t border-orange-200 text-xs text-orange-700">
                <strong>Passive Mode:</strong> These warnings indicate potential methodological issues.
                You can continue working, but consider reviewing the analysis methodology or consulting a domain expert.
              </div>
            </div>
          )}
        </div>
      )}

      {(() => {
        // Extract orphaned labels from broken html-type tables
        const orphanedLabels: string[] = [];
        result.tables.forEach((t: any) => {
          // Empty html tables (broken captures)
          if (t.type === 'html' && (!t.content || t.content === null) && t.label) {
            orphanedLabels.push(t.label);
          }
          // Plotly html tables that duplicate interactive_plots
          if (t.type === 'html' && t.content && t.content.includes('plotly') && t.label) {
            orphanedLabels.push(t.label);
          }
        });

        return (
          <>
            {/* Analysis Results */}
            {result.tables.filter((t: any) => {
              // Filter for display source
              if (t.source !== 'display') return false;
              // Skip html-type tables with no content (broken old captures)
              if (t.type === 'html' && (!t.content || t.content === null)) return false;
              // Skip plotly html tables (duplicates of interactive_plots)
              if (t.type === 'html' && t.content && t.content.includes('plotly')) return false;
              return true;
            }).map((table: any, index: number) => {
        const displayType = table.type || 'table';
        return (
          <div key={`table-${index}`} className="mb-4 bg-white rounded-lg border border-gray-200 overflow-hidden shadow-sm">
            {table.label && (
              <div className="px-4 py-2 bg-blue-50 border-b border-gray-200">
                <h4 className="text-sm font-semibold text-gray-900">{table.label}</h4>
              </div>
            )}
            <div className="p-4">
              {displayType === 'table' && <TableDisplay table={table} />}
              {displayType === 'html' && (
                // Fallback: if html type has no content but has data, treat as image (backward compat)
                table.content ? (
                  <div className="prose max-w-none" dangerouslySetInnerHTML={{ __html: table.content }} />
                ) : table.data ? (
                  <img
                    src={`data:image/png;base64,${table.data}`}
                    alt={table.label || 'Figure'}
                    className="max-w-full h-auto"
                  />
                ) : null
              )}
              {displayType === 'json' && (
                <pre className="bg-gray-50 p-3 rounded text-xs overflow-x-auto font-mono">
                  <code className="text-gray-800">{table.content}</code>
                </pre>
              )}
              {displayType === 'text' && (
                <pre className="bg-gray-50 p-3 rounded text-sm overflow-x-auto whitespace-pre-wrap font-mono">
                  {table.content}
                </pre>
              )}
              {displayType === 'model' && (
                <div className="bg-gradient-to-r from-purple-50 to-blue-50 p-4 rounded-lg border border-purple-200">
                  <div className="flex items-center mb-3">
                    <BarChart3 className="h-5 w-5 text-purple-600 mr-2" />
                    <span className="font-semibold text-purple-900">Machine Learning Model</span>
                  </div>
                  <pre className="bg-white p-3 rounded text-xs overflow-x-auto font-mono border">
                    <code className="text-gray-800">{table.content}</code>
                  </pre>
                </div>
              )}
              {displayType === 'image' && (
                <img
                  src={`data:image/png;base64,${table.data}`}
                  alt={table.label || 'Figure'}
                  className="max-w-full h-auto"
                />
              )}
            </div>
          </div>
        );
      })}

            {/* Matplotlib Plots */}
            {result.plots.map((plot: any, index: number) => {
              const plotData = typeof plot === 'string' ? plot : plot.data;
              let plotLabel = typeof plot === 'object' && plot.label ? plot.label : null;
              const isDisplayed = typeof plot === 'object' && plot.source === 'display';

              // If no label and there's an orphaned label, use it
              if (!plotLabel && orphanedLabels.length > index) {
                plotLabel = orphanedLabels[index];
              }

        // Skip if no plot data
        if (!plotData) return null;

              return (
                <div key={`plot-${index}`} className="mb-4 bg-white rounded-lg border border-gray-200 overflow-hidden shadow-sm">
                  {plotLabel && (
                    <div className="px-4 py-2 bg-blue-50 border-b border-gray-200">
                      <h4 className="text-sm font-semibold text-gray-900">{plotLabel}</h4>
                    </div>
                  )}
                  <div className="p-4">
              <img
                src={`data:image/png;base64,${plotData}`}
                alt={plotLabel || `Plot ${index + 1}`}
                className="max-w-full h-auto"
              />
                  </div>
                </div>
              );
            })}

            {/* Interactive Plotly Plots */}
            {result.interactive_plots.map((plot: any, index: number) => {
              let plotLabel = plot.label;

              // If no label and there are orphaned labels, try to use them
              // (offset by number of regular plots that already consumed orphaned labels)
              if (!plotLabel && orphanedLabels.length > 0) {
                const orphanedIndex = result.plots.length + index;
                if (orphanedIndex < orphanedLabels.length) {
                  plotLabel = orphanedLabels[orphanedIndex];
                }
              }

              return (
                <div key={`interactive-${index}`} className="mb-4 bg-white rounded-lg border border-gray-200 overflow-hidden shadow-sm">
                  {plotLabel && (
                    <div className="px-4 py-2 bg-blue-50 border-b border-gray-200">
                      <h4 className="text-sm font-semibold text-gray-900">{plotLabel}</h4>
                    </div>
                  )}
                  <div className="p-4">
                    <Plot
                      data={plot.figure.data}
                      layout={{
                        ...plot.figure.layout,
                        autosize: true
                      }}
                      config={{
                        responsive: true,
                        displayModeBar: true,
                        displaylogo: false
                      }}
                      style={{ width: '100%', height: '600px' }}
                      useResizeHandler={true}
                    />
                  </div>
                </div>
              );
            })}
          </>
        );
      })()}


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

      {/* Review Panel - Show review findings if available */}
      {cellReview && (
        <ReviewPanel review={cellReview} onRefresh={onRefreshReview} />
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

// Simplified console output - tables are now parsed on backend and shown in Tables section
const ConsoleOutput: React.FC<{ output: string }> = ({ output }) => {
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="bg-gray-50 px-3 py-2 border-b flex items-center justify-between">
        <span className="text-xs text-gray-600">Console Output</span>
        <span className="text-xs text-gray-400 italic">
          Tables are parsed automatically and shown above
        </span>
      </div>

      {/* Content */}
      <div className="bg-white p-3">
        <pre className="text-xs font-mono overflow-x-auto whitespace-pre text-gray-800">
          {output}
        </pre>
      </div>
    </div>
  )
}

// Analysis Results Tables Section - Expanded by default, shows tables parsed from stdout
const AnalysisResultsTablesSection: React.FC<{ tables: TableData[] }> = ({ tables }) => {
  const [isExpanded, setIsExpanded] = React.useState(true) // Expanded by default

  return (
    <div className="mb-4">
      {/* Collapsible Header */}
      <div
        className="flex items-center justify-between p-3 bg-blue-50 border border-blue-200 rounded-lg cursor-pointer hover:bg-blue-100 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center space-x-2">
          <Table className="h-4 w-4 text-blue-600" />
          <span className="text-sm font-medium text-blue-700">
            Analysis Results
          </span>
          <span className="text-xs text-blue-500 bg-blue-200 px-2 py-0.5 rounded">
            {tables.length} table{tables.length !== 1 ? 's' : ''}
          </span>
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-xs text-blue-600">
            {isExpanded ? 'Click to fold' : 'Click to expand'}
          </span>
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-blue-600" />
          ) : (
            <ChevronRight className="h-4 w-4 text-blue-600" />
          )}
        </div>
      </div>

      {/* Collapsible Content */}
      {isExpanded && (
        <div className="mt-2 space-y-4">
          {tables.map((table, index) => (
            <div key={index} className="bg-white rounded-lg border border-blue-200 overflow-hidden shadow-sm">
              <TableDisplay table={table} />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// Collapsible Data Tables Section Component - Intermediary data from variables
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
