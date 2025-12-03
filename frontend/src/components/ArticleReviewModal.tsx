import React, { useState, useMemo } from 'react'
import { X, ClipboardCheck, AlertTriangle, Info, AlertCircle, CheckCircle, ChevronDown, ChevronRight } from 'lucide-react'
import { marked } from 'marked'

// Configure marked for review rendering
marked.setOptions({
  breaks: true,
  gfm: true,
  headerIds: false,
  mangle: false
})

// Enhanced TypeScript interfaces matching backend models
interface DimensionRating {
  score: number
  label: string
  summary: string
}

interface ResearchQuestionAssessment {
  rating: DimensionRating
  relevance: string
  clarity: string
  scope: string
}

interface MethodologyAssessment {
  rating: DimensionRating
  approach_validity: string
  assumptions: string
  reproducibility: string
}

interface ResultsCommunicationAssessment {
  rating: DimensionRating
  accuracy: string
  clarity: string
  completeness: string
  methodology_text: string
}

interface EnhancedIssue {
  severity: 'info' | 'warning' | 'critical'
  category?: string
  title: string
  description: string
  impact: string
  suggestion: string
}

interface ArticleReview {
  notebook_id: string

  // Enhanced dimensional assessments
  research_question?: ResearchQuestionAssessment
  methodology?: MethodologyAssessment
  results_communication?: ResultsCommunicationAssessment
  recommendation?: string

  // Overall
  overall_assessment: string
  rating: number

  // Detailed feedback
  strengths: string[]
  enhanced_issues?: EnhancedIssue[]
  recommendations: string[]

  reviewed_at: string
  reviewer_persona?: string
}

interface ArticleReviewModalProps {
  isVisible: boolean
  review: ArticleReview | null
  onClose: () => void
}

/**
 * ArticleReviewModal - Professional SOTA Scientific Review Display
 *
 * Displays multi-dimensional peer review following Nature/Science/Cell/PLOS practices:
 * - Dimensional ratings (Research Question, Methodology, Results Communication)
 * - Overall assessment with recommendation
 * - Strengths, issues, and recommendations with markdown rendering
 */
const ArticleReviewModal: React.FC<ArticleReviewModalProps> = ({ isVisible, review, onClose }) => {
  const [expandedDimension, setExpandedDimension] = useState<string | null>(null)
  const [expandedIssues, setExpandedIssues] = useState<Set<number>>(new Set())

  // Memoize marked configuration
  useMemo(() => {
    marked.setOptions({
      breaks: true,
      gfm: true,
      headerIds: false,
      mangle: false
    })
  }, [])

  if (!isVisible || !review) return null

  // Helper to convert rating to quality badge
  const getRatingBadge = (rating: number) => {
    if (rating >= 5) {
      return { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-800', icon: <CheckCircle className="h-5 w-5" />, label: 'Excellent' }
    } else if (rating >= 4) {
      return { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-800', icon: <CheckCircle className="h-5 w-5" />, label: 'Good' }
    } else if (rating >= 3) {
      return { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-800', icon: <Info className="h-5 w-5" />, label: 'Adequate' }
    } else if (rating >= 2) {
      return { bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-800', icon: <AlertTriangle className="h-5 w-5" />, label: 'Needs Improvement' }
    } else {
      return { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-800', icon: <AlertCircle className="h-5 w-5" />, label: 'Poor' }
    }
  }

  // Helper to get recommendation badge style
  const getRecommendationStyle = (rec?: string) => {
    const recommendation = rec || 'Minor Revisions'
    if (recommendation.toLowerCase().includes('accept')) {
      return { bg: 'bg-green-100', text: 'text-green-800', label: '✓ Accept' }
    } else if (recommendation.toLowerCase().includes('major')) {
      return { bg: 'bg-orange-100', text: 'text-orange-800', label: 'Major Revisions' }
    } else if (recommendation.toLowerCase().includes('reject')) {
      return { bg: 'bg-red-100', text: 'text-red-800', label: '✗ Reject' }
    } else {
      return { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Minor Revisions' }
    }
  }

  const qualityStyle = getRatingBadge(review.rating)
  const recommendationStyle = getRecommendationStyle(review.recommendation)

  const toggleIssue = (index: number) => {
    const newExpanded = new Set(expandedIssues)
    if (newExpanded.has(index)) {
      newExpanded.delete(index)
    } else {
      newExpanded.add(index)
    }
    setExpandedIssues(newExpanded)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-5xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center space-x-3">
            <ClipboardCheck className="h-6 w-6 text-blue-600" />
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Article Review</h2>
              <p className="text-xs text-gray-600">Scientific Peer Review</p>
            </div>
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
          {/* Overall Assessment */}
          <div className="border border-gray-200 rounded-lg p-5 bg-gray-50">
            <div className="flex items-start justify-between mb-3">
              <div className={`flex items-center space-x-3 px-4 py-2 rounded-lg border ${qualityStyle.bg} ${qualityStyle.border}`}>
                {qualityStyle.icon}
                <span className={`font-semibold ${qualityStyle.text}`}>
                  {qualityStyle.label}
                </span>
                <span className={`text-lg font-bold ${qualityStyle.text}`}>
                  {'★'.repeat(review.rating)}{'☆'.repeat(5 - review.rating)}
                </span>
              </div>
              <div className={`px-4 py-2 rounded-lg font-medium ${recommendationStyle.bg} ${recommendationStyle.text}`}>
                {recommendationStyle.label}
              </div>
            </div>
            <div className="review-markdown prose max-w-none" dangerouslySetInnerHTML={{ __html: marked.parse(review.overall_assessment) }} />
          </div>

          {/* Dimensional Assessment Cards */}
          {review.research_question && (
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <button
                onClick={() => setExpandedDimension(expandedDimension === 'rq' ? null : 'rq')}
                className="w-full px-5 py-4 bg-blue-50 hover:bg-blue-100 transition-colors"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-3">
                    {expandedDimension === 'rq' ? <ChevronDown className="h-5 w-5 text-blue-600" /> : <ChevronRight className="h-5 w-5 text-blue-600" />}
                    <span className="font-semibold text-gray-900">Research Question Assessment</span>
                  </div>
                  <div className="flex items-center space-x-3">
                    <span className="text-sm text-gray-600">{review.research_question.rating.label}</span>
                    <span className="text-yellow-500 font-semibold">
                      {'★'.repeat(review.research_question.rating.score)}{'☆'.repeat(5 - review.research_question.rating.score)}
                    </span>
                  </div>
                </div>
                <p className="text-sm text-gray-700 italic text-left pl-8">{review.research_question.rating.summary}</p>
              </button>
              {expandedDimension === 'rq' && (
                <div className="p-5 bg-white space-y-4 border-t border-gray-200">
                  <div>
                    <h4 className="text-sm font-semibold text-gray-800 mb-1">Relevance</h4>
                    <div className="review-markdown prose-sm max-w-none" dangerouslySetInnerHTML={{ __html: marked.parse(review.research_question.relevance) }} />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-800 mb-1">Clarity</h4>
                    <div className="review-markdown prose-sm max-w-none" dangerouslySetInnerHTML={{ __html: marked.parse(review.research_question.clarity) }} />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-800 mb-1">Scope</h4>
                    <div className="review-markdown prose-sm max-w-none" dangerouslySetInnerHTML={{ __html: marked.parse(review.research_question.scope) }} />
                  </div>
                </div>
              )}
            </div>
          )}

          {review.methodology && (
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <button
                onClick={() => setExpandedDimension(expandedDimension === 'method' ? null : 'method')}
                className="w-full px-5 py-4 bg-purple-50 hover:bg-purple-100 transition-colors"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-3">
                    {expandedDimension === 'method' ? <ChevronDown className="h-5 w-5 text-purple-600" /> : <ChevronRight className="h-5 w-5 text-purple-600" />}
                    <span className="font-semibold text-gray-900">Methodology Assessment</span>
                  </div>
                  <div className="flex items-center space-x-3">
                    <span className="text-sm text-gray-600">{review.methodology.rating.label}</span>
                    <span className="text-yellow-500 font-semibold">
                      {'★'.repeat(review.methodology.rating.score)}{'☆'.repeat(5 - review.methodology.rating.score)}
                    </span>
                  </div>
                </div>
                <p className="text-sm text-gray-700 italic text-left pl-8">{review.methodology.rating.summary}</p>
              </button>
              {expandedDimension === 'method' && (
                <div className="p-5 bg-white space-y-4 border-t border-gray-200">
                  <div>
                    <h4 className="text-sm font-semibold text-gray-800 mb-1">Approach Validity</h4>
                    <div className="review-markdown prose-sm max-w-none" dangerouslySetInnerHTML={{ __html: marked.parse(review.methodology.approach_validity) }} />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-800 mb-1">Assumptions</h4>
                    <div className="review-markdown prose-sm max-w-none" dangerouslySetInnerHTML={{ __html: marked.parse(review.methodology.assumptions) }} />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-800 mb-1">Reproducibility</h4>
                    <div className="review-markdown prose-sm max-w-none" dangerouslySetInnerHTML={{ __html: marked.parse(review.methodology.reproducibility) }} />
                  </div>
                </div>
              )}
            </div>
          )}

          {review.results_communication && (
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <button
                onClick={() => setExpandedDimension(expandedDimension === 'results' ? null : 'results')}
                className="w-full px-5 py-4 bg-green-50 hover:bg-green-100 transition-colors"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-3">
                    {expandedDimension === 'results' ? <ChevronDown className="h-5 w-5 text-green-600" /> : <ChevronRight className="h-5 w-5 text-green-600" />}
                    <span className="font-semibold text-gray-900">Results Communication Assessment</span>
                  </div>
                  <div className="flex items-center space-x-3">
                    <span className="text-sm text-gray-600">{review.results_communication.rating.label}</span>
                    <span className="text-yellow-500 font-semibold">
                      {'★'.repeat(review.results_communication.rating.score)}{'☆'.repeat(5 - review.results_communication.rating.score)}
                    </span>
                  </div>
                </div>
                <p className="text-sm text-gray-700 italic text-left pl-8">{review.results_communication.rating.summary}</p>
              </button>
              {expandedDimension === 'results' && (
                <div className="p-5 bg-white space-y-4 border-t border-gray-200">
                  <div>
                    <h4 className="text-sm font-semibold text-gray-800 mb-1">Accuracy</h4>
                    <div className="review-markdown prose-sm max-w-none" dangerouslySetInnerHTML={{ __html: marked.parse(review.results_communication.accuracy) }} />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-800 mb-1">Clarity</h4>
                    <div className="review-markdown prose-sm max-w-none" dangerouslySetInnerHTML={{ __html: marked.parse(review.results_communication.clarity) }} />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-800 mb-1">Completeness</h4>
                    <div className="review-markdown prose-sm max-w-none" dangerouslySetInnerHTML={{ __html: marked.parse(review.results_communication.completeness) }} />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-800 mb-1">Methodology Text</h4>
                    <div className="review-markdown prose-sm max-w-none" dangerouslySetInnerHTML={{ __html: marked.parse(review.results_communication.methodology_text) }} />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Strengths */}
          {review.strengths && review.strengths.length > 0 && (
            <div>
              <h3 className="text-base font-semibold text-gray-900 mb-3 flex items-center space-x-2">
                <CheckCircle className="h-5 w-5 text-green-600" />
                <span>Key Strengths</span>
              </h3>
              <ul className="space-y-2">
                {review.strengths.map((strength, index) => (
                  <li key={index} className="flex items-start space-x-3 bg-green-50 border border-green-100 rounded-lg p-3">
                    <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0 mt-1" />
                    <div className="review-markdown prose-sm max-w-none flex-1" dangerouslySetInnerHTML={{ __html: marked.parse(strength) }} />
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Areas for Improvement (Enhanced Issues) */}
          {review.enhanced_issues && review.enhanced_issues.length > 0 && (
            <div>
              <h3 className="text-base font-semibold text-gray-900 mb-3 flex items-center space-x-2">
                <AlertTriangle className="h-5 w-5 text-amber-600" />
                <span>Areas for Improvement</span>
              </h3>
              <div className="space-y-3">
                {review.enhanced_issues.map((issue, index) => {
                  const isExpanded = expandedIssues.has(index)
                  const issueSeverity = issue.severity || 'info'
                  const issueStyle =
                    issueSeverity === 'critical'
                      ? { bg: 'bg-red-50', border: 'border-red-200', headerBg: 'bg-red-100', text: 'text-red-800', icon: <AlertCircle className="h-4 w-4 text-red-600" />, badge: 'Critical' }
                      : issueSeverity === 'warning'
                      ? { bg: 'bg-amber-50', border: 'border-amber-200', headerBg: 'bg-amber-100', text: 'text-amber-800', icon: <AlertTriangle className="h-4 w-4 text-amber-600" />, badge: 'Warning' }
                      : { bg: 'bg-blue-50', border: 'border-blue-200', headerBg: 'bg-blue-100', text: 'text-blue-800', icon: <Info className="h-4 w-4 text-blue-600" />, badge: 'Info' }

                  return (
                    <div key={index} className={`border ${issueStyle.border} ${issueStyle.bg} rounded-lg overflow-hidden`}>
                      <button
                        onClick={() => toggleIssue(index)}
                        className={`w-full px-4 py-3 flex items-center justify-between ${issueStyle.headerBg} hover:opacity-80 transition-opacity`}
                      >
                        <div className="flex items-center space-x-3 flex-1 text-left">
                          {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                          {issueStyle.icon}
                          <span className={`font-semibold text-sm ${issueStyle.text}`}>{issue.title}</span>
                        </div>
                        <span className={`text-xs font-medium ${issueStyle.text} px-2 py-1 bg-white rounded`}>
                          {issueStyle.badge}
                        </span>
                      </button>
                      {isExpanded && (
                        <div className="p-4 space-y-3 bg-white border-t">
                          <div>
                            <h5 className="text-xs font-semibold text-gray-700 mb-1">Description</h5>
                            <div className="review-markdown prose-sm max-w-none" dangerouslySetInnerHTML={{ __html: marked.parse(issue.description) }} />
                          </div>
                          <div>
                            <h5 className="text-xs font-semibold text-gray-700 mb-1">Impact</h5>
                            <div className="review-markdown prose-sm max-w-none" dangerouslySetInnerHTML={{ __html: marked.parse(issue.impact) }} />
                          </div>
                          <div>
                            <h5 className="text-xs font-semibold text-gray-700 mb-1">💡 Suggestion</h5>
                            <div className="review-markdown prose-sm max-w-none" dangerouslySetInnerHTML={{ __html: marked.parse(issue.suggestion) }} />
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {review.recommendations && review.recommendations.length > 0 && (
            <div>
              <h3 className="text-base font-semibold text-gray-900 mb-3">Recommendations for Improvement</h3>
              <ul className="space-y-2">
                {review.recommendations.map((rec, index) => (
                  <li key={index} className="flex items-start space-x-3 bg-blue-50 border border-blue-100 rounded-lg p-3">
                    <span className="text-blue-700 font-bold flex-shrink-0 text-sm">{index + 1}.</span>
                    <div className="review-markdown prose-sm max-w-none flex-1" dangerouslySetInnerHTML={{ __html: marked.parse(rec) }} />
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-between items-center p-6 border-t border-gray-200 bg-gray-50">
          {review.reviewed_at && (
            <p className="text-xs text-gray-500">
              Reviewed: {new Date(review.reviewed_at).toLocaleString()}
            </p>
          )}
          <button
            onClick={onClose}
            className="px-5 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors font-medium"
          >
            Close
          </button>
        </div>
      </div>

      {/* Markdown styles matching chat panel */}
      <style>{`
        .review-markdown h1, .review-markdown h2, .review-markdown h3 {
          font-weight: 600;
          margin-top: 0.75em;
          margin-bottom: 0.5em;
          line-height: 1.3;
        }
        .review-markdown h1 { font-size: 1.25em; }
        .review-markdown h2 { font-size: 1.15em; }
        .review-markdown h3 { font-size: 1.1em; }

        .review-markdown p {
          margin: 0.5em 0;
        }

        .review-markdown strong {
          font-weight: 600;
          color: inherit;
        }

        .review-markdown em {
          font-style: italic;
        }

        .review-markdown ul, .review-markdown ol {
          margin: 0.5em 0;
          padding-left: 1.5em;
        }

        .review-markdown li {
          margin: 0.25em 0;
        }

        .review-markdown code {
          background-color: rgba(0, 0, 0, 0.05);
          padding: 0.125em 0.25em;
          border-radius: 0.25em;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
          font-size: 0.9em;
        }

        .review-markdown pre {
          background-color: rgba(0, 0, 0, 0.05);
          padding: 0.75em;
          border-radius: 0.375em;
          overflow-x: auto;
          margin: 0.5em 0;
        }

        .review-markdown pre code {
          background-color: transparent;
          padding: 0;
        }

        .review-markdown a {
          color: #2563eb;
          text-decoration: underline;
        }

        .review-markdown blockquote {
          border-left: 3px solid rgba(0, 0, 0, 0.1);
          padding-left: 1em;
          margin: 0.5em 0;
          color: rgba(0, 0, 0, 0.7);
        }
      `}</style>
    </div>
  )
}

export default ArticleReviewModal
