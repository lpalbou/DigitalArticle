import React, { useState, useMemo } from 'react'
import { Table, FileSpreadsheet, ChevronLeft, ChevronRight, Search, Download, Info } from 'lucide-react'

interface ExcelSheet {
  name: string
  rows?: number
  columns?: string[]
  shape?: [number, number]
  dtypes?: Record<string, string>
  sample_data?: Record<string, any>[]
  error?: string
}

interface ExcelData {
  file_type: string
  sheets: ExcelSheet[]
  total_sheets: number
  error?: string
}

interface ExcelFileViewerProps {
  data: ExcelData
  fileName: string
}

const ExcelFileViewer: React.FC<ExcelFileViewerProps> = ({ data, fileName }) => {
  const [activeSheetIndex, setActiveSheetIndex] = useState(0)
  const [searchTerm, setSearchTerm] = useState('')
  const [showDataTypes, setShowDataTypes] = useState(false)

  // Get current sheet
  const currentSheet = useMemo(() => {
    return data.sheets[activeSheetIndex] || null
  }, [data.sheets, activeSheetIndex])

  // Filter data based on search term
  const filteredData = useMemo(() => {
    if (!currentSheet?.sample_data || !searchTerm.trim()) {
      return currentSheet?.sample_data || []
    }

    const term = searchTerm.toLowerCase()
    return currentSheet.sample_data.filter(row =>
      Object.values(row).some(value =>
        String(value).toLowerCase().includes(term)
      )
    )
  }, [currentSheet, searchTerm])

  // Navigate sheets
  const goToPrevSheet = () => {
    if (activeSheetIndex > 0) {
      setActiveSheetIndex(activeSheetIndex - 1)
      setSearchTerm('')
    }
  }

  const goToNextSheet = () => {
    if (activeSheetIndex < data.sheets.length - 1) {
      setActiveSheetIndex(activeSheetIndex + 1)
      setSearchTerm('')
    }
  }

  // Handle error state
  if (data.error) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center">
        <FileSpreadsheet className="w-16 h-16 text-red-400 mb-4" />
        <h3 className="text-lg font-medium text-red-600 mb-2">Error Loading Excel File</h3>
        <p className="text-sm text-gray-500">{data.error}</p>
      </div>
    )
  }

  if (!data.sheets || data.sheets.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center">
        <FileSpreadsheet className="w-16 h-16 text-gray-400 mb-4" />
        <h3 className="text-lg font-medium text-gray-600 mb-2">No Sheets Found</h3>
        <p className="text-sm text-gray-500">This Excel file appears to be empty.</p>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header with file info */}
      <div className="px-4 py-3 bg-gradient-to-r from-green-50 to-emerald-50 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <FileSpreadsheet className="w-6 h-6 text-green-600" />
            <div>
              <h3 className="font-semibold text-gray-900">{fileName}</h3>
              <p className="text-sm text-gray-600">
                {data.total_sheets} sheet{data.total_sheets !== 1 ? 's' : ''}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowDataTypes(!showDataTypes)}
              className={`p-2 rounded-lg transition-colors ${
                showDataTypes 
                  ? 'bg-green-100 text-green-700' 
                  : 'text-gray-500 hover:bg-gray-100'
              }`}
              title="Show data types"
            >
              <Info className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Sheet tabs */}
      <div className="flex items-center border-b border-gray-200 bg-gray-50">
        {/* Navigation arrows for many sheets */}
        {data.sheets.length > 5 && (
          <button
            onClick={goToPrevSheet}
            disabled={activeSheetIndex === 0}
            className="p-2 text-gray-500 hover:text-gray-700 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
        )}
        
        {/* Sheet tabs */}
        <div className="flex-1 flex overflow-x-auto">
          {data.sheets.map((sheet, index) => (
            <button
              key={index}
              onClick={() => {
                setActiveSheetIndex(index)
                setSearchTerm('')
              }}
              className={`px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                activeSheetIndex === index
                  ? 'border-green-500 text-green-700 bg-white'
                  : 'border-transparent text-gray-600 hover:text-gray-800 hover:bg-gray-100'
              }`}
            >
              <span className="flex items-center space-x-2">
                <Table className="w-3.5 h-3.5" />
                <span>{sheet.name}</span>
                {sheet.shape && (
                  <span className="text-xs text-gray-400 font-normal">
                    ({sheet.shape[0]}×{sheet.shape[1]})
                  </span>
                )}
              </span>
            </button>
          ))}
        </div>

        {data.sheets.length > 5 && (
          <button
            onClick={goToNextSheet}
            disabled={activeSheetIndex === data.sheets.length - 1}
            className="p-2 text-gray-500 hover:text-gray-700 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Current sheet content */}
      {currentSheet && (
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Sheet error state */}
          {currentSheet.error ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
              <Table className="w-12 h-12 text-red-400 mb-3" />
              <h4 className="text-base font-medium text-red-600 mb-1">
                Error Reading Sheet: {currentSheet.name}
              </h4>
              <p className="text-sm text-gray-500">{currentSheet.error}</p>
            </div>
          ) : (
            <>
              {/* Search and info bar */}
              <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="relative">
                    <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                    <input
                      type="text"
                      placeholder="Search in data..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="pl-9 pr-4 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent w-64"
                    />
                  </div>
                  {searchTerm && (
                    <span className="text-xs text-gray-500">
                      Found {filteredData.length} of {currentSheet.sample_data?.length || 0} rows
                    </span>
                  )}
                </div>
                <div className="text-xs text-gray-500">
                  {currentSheet.rows !== undefined && (
                    <span>
                      Showing {Math.min(10, currentSheet.rows)} of {currentSheet.rows.toLocaleString()} rows
                    </span>
                  )}
                </div>
              </div>

              {/* Data types row (optional) */}
              {showDataTypes && currentSheet.dtypes && currentSheet.columns && (
                <div className="px-4 py-2 bg-blue-50 border-b border-blue-100 overflow-x-auto">
                  <div className="flex space-x-4 text-xs">
                    {currentSheet.columns.map((col, idx) => (
                      <div key={idx} className="flex items-center space-x-1">
                        <span className="font-medium text-blue-700">{col}:</span>
                        <span className="text-blue-600 font-mono">
                          {currentSheet.dtypes?.[col] || 'unknown'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Data table */}
              <div className="flex-1 overflow-auto">
                {currentSheet.columns && currentSheet.columns.length > 0 ? (
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-100 sticky top-0">
                      <tr>
                        <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider bg-gray-200 border-r border-gray-300">
                          #
                        </th>
                        {currentSheet.columns.map((col, idx) => (
                          <th
                            key={idx}
                            className="px-4 py-2 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider whitespace-nowrap bg-gray-100 border-b border-gray-300"
                          >
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-100">
                      {filteredData.length > 0 ? (
                        filteredData.map((row, rowIndex) => (
                          <tr
                            key={rowIndex}
                            className={`hover:bg-green-50 transition-colors ${
                              rowIndex % 2 === 0 ? 'bg-white' : 'bg-gray-50'
                            }`}
                          >
                            <td className="px-3 py-2 text-xs text-gray-400 font-mono bg-gray-100 border-r border-gray-200">
                              {rowIndex + 1}
                            </td>
                            {currentSheet.columns?.map((col, cellIndex) => {
                              const value = row[col]
                              const isEmpty = value === null || value === undefined || value === ''
                              const displayValue = isEmpty ? '' : String(value)
                              const isNumber = typeof value === 'number'

                              return (
                                <td
                                  key={cellIndex}
                                  className={`px-4 py-2 text-sm whitespace-nowrap ${
                                    isNumber 
                                      ? 'text-right font-mono text-blue-700' 
                                      : 'text-gray-900'
                                  }`}
                                  title={displayValue.length > 50 ? displayValue : undefined}
                                >
                                  {displayValue.length > 50 
                                    ? displayValue.substring(0, 50) + '...' 
                                    : displayValue}
                                </td>
                              )
                            })}
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td
                            colSpan={(currentSheet.columns?.length || 0) + 1}
                            className="px-4 py-8 text-center text-gray-500"
                          >
                            {searchTerm ? 'No matching rows found' : 'No data in this sheet'}
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                ) : (
                  <div className="flex flex-col items-center justify-center p-8 text-center">
                    <Table className="w-12 h-12 text-gray-300 mb-3" />
                    <p className="text-gray-500">No columns found in this sheet</p>
                  </div>
                )}
              </div>

              {/* Footer with row count */}
              {currentSheet.rows !== undefined && currentSheet.rows > 10 && (
                <div className="px-4 py-2 bg-gray-50 border-t border-gray-200 text-center">
                  <p className="text-xs text-gray-500">
                    Preview shows first 10 rows. Full sheet contains{' '}
                    <span className="font-medium">{currentSheet.rows.toLocaleString()}</span> rows ×{' '}
                    <span className="font-medium">{currentSheet.columns?.length || 0}</span> columns
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

export default ExcelFileViewer
