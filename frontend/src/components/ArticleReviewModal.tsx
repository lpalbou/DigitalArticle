import React from 'react'
import { X, ClipboardCheck, AlertTriangle, Info, AlertCircle, CheckCircle } from 'lucide-react'

interface ArticleReview {
  notebook_id: string
  overall_assessment: string
  overall_quality: 'excellent' | 'good' | 'adequate' | 'needs_improvement' | 'poor'
  strengths: string[]
  issues: Array<{
    severity: 'info' | 'warning' | 'critical'
    message: string
    suggestion?: string
  }>
  recommendations: string[]
  timestamp: string
}

interface ArticleReviewModalProps {
  isVisible: boolean
  review: ArticleReview | null
  onClose: () => void
}

/**
 * ArticleReviewModal - Display comprehensive article review
 *
 * Simple, clean modal showing:
 * - Overall quality assessment
 * - Key strengths
 * - Issues by severity
 * - Recommendations
 */
const ArticleReviewModal: React.FC<ArticleReviewModalProps> = ({ isVisible, review, onClose }) => {
  if (!isVisible || !review) return null

  // Quality badge styling
  const getQualityBadge = (quality: string) => {
    switch (quality) {
      case 'excellent':
        return { bg: 'bg-green-100', text: 'text-green-800', icon: <CheckCircle className="h-5 w-5" /> }
      case 'good':
        return { bg: 'bg-blue-100', text: 'text-blue-800', icon: <CheckCircle className="h-5 w-5" /> }
      case 'adequate':
        return { bg: 'bg-yellow-100', text: 'text-yellow-800', icon: <Info className="h-5 w-5" /> }
      case 'needs_improvement':
        return { bg: 'bg-orange-100', text: 'text-orange-800', icon: <AlertTriangle className="h-5 w-5" /> }
      case 'poor':
        return { bg: 'bg-red-100', text: 'text-red-800', icon: <AlertCircle className="h-5 w-5" /> }
      default:
        return { bg: 'bg-gray-100', text: 'text-gray-800', icon: <Info className="h-5 w-5" /> }
    }
  }

  const qualityStyle = getQualityBadge(review.overall_quality)

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <ClipboardCheck className="h-6 w-6 text-blue-600" />
            <h2 className="text-xl font-semibold text-gray-900">Article Review</h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Overall Quality */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Overall Quality</h3>
            <div className={`inline-flex items-center space-x-2 px-4 py-2 rounded-lg ${qualityStyle.bg}`}>
              {qualityStyle.icon}
              <span className={`font-medium ${qualityStyle.text} capitalize`}>
                {review.overall_quality.replace('_', ' ')}
              </span>
            </div>
          </div>

          {/* Overall Assessment */}
          {review.overall_assessment && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Assessment</h3>
              <p className="text-gray-700 leading-relaxed">{review.overall_assessment}</p>
            </div>
          )}

          {/* Strengths */}
          {review.strengths && review.strengths.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Strengths</h3>
              <ul className="space-y-2">
                {review.strengths.map((strength, index) => (
                  <li key={index} className="flex items-start space-x-2">
                    <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">{strength}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Issues */}
          {review.issues && review.issues.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Issues</h3>
              <div className="space-y-2">
                {review.issues.map((issue, index) => {
                  const issueSeverity = issue.severity || 'info'
                  const issueStyle =
                    issueSeverity === 'critical'
                      ? { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-800', icon: <AlertCircle className="h-4 w-4 text-red-600" /> }
                      : issueSeverity === 'warning'
                      ? { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-800', icon: <AlertTriangle className="h-4 w-4 text-yellow-600" /> }
                      : { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-800', icon: <Info className="h-4 w-4 text-blue-600" /> }

                  return (
                    <div key={index} className={`p-3 rounded-md border ${issueStyle.bg} ${issueStyle.border}`}>
                      <div className="flex items-start space-x-2">
                        {issueStyle.icon}
                        <div className="flex-1">
                          <p className={`text-sm ${issueStyle.text}`}>{issue.message}</p>
                          {issue.suggestion && (
                            <p className={`text-xs ${issueStyle.text} opacity-75 mt-1`}>
                              💡 {issue.suggestion}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {review.recommendations && review.recommendations.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Recommendations</h3>
              <ul className="space-y-2">
                {review.recommendations.map((rec, index) => (
                  <li key={index} className="flex items-start space-x-2">
                    <span className="text-blue-600 font-bold flex-shrink-0">{index + 1}.</span>
                    <span className="text-gray-700">{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Timestamp */}
          {review.timestamp && (
            <p className="text-xs text-gray-500 pt-4 border-t border-gray-200">
              Reviewed: {new Date(review.timestamp).toLocaleString()}
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end p-6 border-t border-gray-200">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

export default ArticleReviewModal
