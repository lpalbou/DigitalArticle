import React, { useMemo, useState } from 'react'
import Plot from 'react-plotly.js'
import { AlertCircle, CheckCircle, Image as ImageIcon, BarChart3, Table, ChevronRight, ChevronDown } from 'lucide-react'
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
      {/* Status Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          {hasError ? (
            <AlertCircle className="h-5 w-5 text-red-500" />
          ) : (
            <CheckCircle className="h-5 w-5 text-green-500" />
          )}
          <span className={`font-medium ${hasError ? 'text-red-700' : 'text-green-700'}`}>
            {hasError ? 'Execution Failed' : 'Execution Successful'}
          </span>
          <span className="text-sm text-gray-500">
            ({result.execution_time.toFixed(2)}s)
          </span>
        </div>
      </div>

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

      {/* Standard Output */}
      {result.stdout && (
        <div className="mb-4">
          <div className="flex items-center space-x-2 mb-2">
            <span className="text-sm font-medium text-gray-700">Output</span>
          </div>
          <pre className="bg-gray-100 p-3 rounded text-sm overflow-x-auto whitespace-pre-wrap">
            {result.stdout}
          </pre>
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

      {/* Tables */}
      {result.tables.length > 0 && (
        <div className="mb-4">
          <div className="flex items-center space-x-2 mb-2">
            <Table className="h-4 w-4" />
            <span className="text-sm font-medium text-gray-700">Data Tables</span>
          </div>
          <div className="space-y-4">
            {result.tables.map((table, index) => (
              <TableDisplay key={index} table={table} />
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

// Component for displaying data tables
const TableDisplay: React.FC<{ table: TableData }> = ({ table }) => {
  const [showFullTable, setShowFullTable] = React.useState(false)
  const displayData = showFullTable ? table.data : table.data.slice(0, 10)

  return (
    <div className="border border-gray-200 rounded-md overflow-hidden">
      {/* Table Header */}
      <div className="bg-gray-50 px-4 py-2 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <span className="font-medium text-sm">{table.name}</span>
            <span className="text-xs text-gray-500">
              {table.shape[0]} rows × {table.shape[1]} columns
            </span>
          </div>
          {table.data.length > 10 && (
            <button
              onClick={() => setShowFullTable(!showFullTable)}
              className="text-xs text-blue-600 hover:text-blue-700"
            >
              {showFullTable ? 'Show Less' : `Show All ${table.data.length} rows`}
            </button>
          )}
        </div>
      </div>

      {/* Table Content */}
      <div className="overflow-x-auto max-h-96">
        <table className="output-table">
          <thead>
            <tr>
              {table.columns.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {displayData.map((row, index) => (
              <tr key={index}>
                {table.columns.map((column) => (
                  <td key={column}>
                    {formatCellValue(row[column])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Table Footer */}
      {table.data.length > 10 && !showFullTable && (
        <div className="bg-gray-50 px-4 py-2 text-xs text-gray-500 text-center">
          Showing 10 of {table.data.length} rows
        </div>
      )}
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

export default ResultPanel
