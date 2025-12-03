import React from 'react'
import { ClipboardCheck, AlertTriangle, Info, AlertCircle, RefreshCw } from 'lucide-react'

interface ReviewFinding {
  phase: string
  severity: 'info' | 'warning' | 'critical'
  message: string
  suggestion?: string
}

interface CellReview {
  cell_id: string
  phase: string
  findings: ReviewFinding[]
  overall_assessment: string
  timestamp: string
}

interface ReviewPanelProps {
  review: CellReview | null
  onRefresh?: () => void
}

/**
 * ReviewPanel - Display cell review findings with severity-coded styling
 *
 * Shows:
 * - Review findings organized by severity
 * - Color-coded indicators (blue=info, yellow=warning, red=critical)
 * - Overall assessment
 * - Refresh button to re-run review
 */
const ReviewPanel: React.FC<ReviewPanelProps> = ({ review, onRefresh }) => {
  if (!review || !review.findings || review.findings.length === 0) {
    return null
  }

  // Severity styling
  const getSeverityStyles = (severity: string) => {
    switch (severity) {
      case 'critical':
        return {
          bg: 'bg-red-50',
          border: 'border-red-200',
          text: 'text-red-800',
          icon: <AlertCircle className="h-4 w-4 text-red-600" />
        }
      case 'warning':
        return {
          bg: 'bg-yellow-50',
          border: 'border-yellow-200',
          text: 'text-yellow-800',
          icon: <AlertTriangle className="h-4 w-4 text-yellow-600" />
        }
      case 'info':
      default:
        return {
          bg: 'bg-blue-50',
          border: 'border-blue-200',
          text: 'text-blue-800',
          icon: <Info className="h-4 w-4 text-blue-600" />
        }
    }
  }

  return (
    <div className="border-t border-gray-200 mt-4 pt-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-gray-700 flex items-center">
          <ClipboardCheck className="h-4 w-4 mr-2 text-gray-600" />
          Review Feedback
        </h4>
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="text-xs text-gray-600 hover:text-gray-800 flex items-center space-x-1"
            title="Refresh review"
          >
            <RefreshCw className="h-3 w-3" />
            <span>Refresh</span>
          </button>
        )}
      </div>

      {/* Overall Assessment */}
      {review.overall_assessment && (
        <div className="mb-3 p-3 bg-gray-50 border border-gray-200 rounded-md">
          <p className="text-sm text-gray-700">{review.overall_assessment}</p>
        </div>
      )}

      {/* Findings */}
      <div className="space-y-2">
        {review.findings.map((finding, index) => {
          const styles = getSeverityStyles(finding.severity)

          return (
            <div
              key={index}
              className={`p-3 rounded-md border ${styles.bg} ${styles.border}`}
            >
              <div className="flex items-start space-x-2">
                <div className="flex-shrink-0 mt-0.5">
                  {styles.icon}
                </div>
                <div className="flex-1 min-w-0">
                  {/* Phase badge */}
                  <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium mb-1 ${styles.text} bg-white bg-opacity-50`}>
                    {finding.phase}
                  </span>

                  {/* Message */}
                  <p className={`text-sm ${styles.text} mt-1`}>
                    {finding.message}
                  </p>

                  {/* Suggestion */}
                  {finding.suggestion && (
                    <p className={`text-xs ${styles.text} mt-2 opacity-75`}>
                      💡 {finding.suggestion}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Timestamp */}
      {review.timestamp && (
        <p className="text-xs text-gray-500 mt-3">
          Reviewed: {new Date(review.timestamp).toLocaleString()}
        </p>
      )}
    </div>
  )
}

export default ReviewPanel
