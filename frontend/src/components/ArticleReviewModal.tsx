import React, { useState, useEffect, useRef } from 'react'
import { X, ClipboardCheck, AlertTriangle, Info, AlertCircle, CheckCircle, ChevronDown, ChevronRight, Activity, MessageCircle, Send, Loader2, Copy, Check } from 'lucide-react'
import ExecutionDetailsModal from './ExecutionDetailsModal'
import MarkdownRenderer from './MarkdownRenderer'
import { LLMTrace, ChatMessage } from '../types'
import { chatAPI } from '../services/api'

// Enhanced TypeScript interfaces matching backend models
interface DimensionRating {
  score: number
  label: string
  summary: string
}

interface DataQualityAssessment {
  rating: DimensionRating
  provenance: string
  quality: string
  quantity: string
  appropriateness: string
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
  data_quality?: DataQualityAssessment
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
  traces?: LLMTrace[]
  notebookId: string
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
const ArticleReviewModal: React.FC<ArticleReviewModalProps> = ({ isVisible, review, traces = [], notebookId, onClose }) => {
  const [expandedDimension, setExpandedDimension] = useState<string | null>(null)
  const [expandedIssues, setExpandedIssues] = useState<Set<number>>(new Set())
  const [showExecutionDetails, setShowExecutionDetails] = useState(false)

  // Chat state
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Load chat history from localStorage on mount OR when new review arrives
  useEffect(() => {
    if (notebookId && isVisible) {
      const key = `reviewer_chat_${notebookId}`
      const saved = localStorage.getItem(key)
      if (saved) {
        try {
          const parsed = JSON.parse(saved)
          setMessages(parsed)
        } catch (e) {
          console.error('Failed to load reviewer chat history:', e)
        }
      } else {
        // Clear messages for fresh review (localStorage was cleared)
        setMessages([])
      }
    }
  }, [notebookId, isVisible, review?.reviewed_at])

  // Save chat history to localStorage when messages change
  useEffect(() => {
    if (notebookId && messages.length > 0) {
      const key = `reviewer_chat_${notebookId}`
      localStorage.setItem(key, JSON.stringify(messages))
    }
  }, [notebookId, messages])

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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

  // Send chat message
  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')

    // Add loading message
    const loadingMessage: ChatMessage = {
      id: `loading-${Date.now()}`,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      loading: true
    }
    setMessages(prev => [...prev, loadingMessage])
    setIsLoading(true)

    try {
      const response = await chatAPI.sendMessage({
        notebook_id: notebookId,
        message: userMessage.content,
        conversation_history: messages.filter(m => !m.loading),
        mode: 'reviewer'
      })

      // Replace loading message with actual response
      setMessages(prev => prev.map(msg =>
        msg.id === loadingMessage.id
          ? {
              id: Date.now().toString(),
              role: 'assistant' as const,
              content: response.message,
              timestamp: response.timestamp
            }
          : msg
      ))
    } catch (error) {
      console.error('Failed to send message:', error)
      setMessages(prev => prev.map(msg =>
        msg.id === loadingMessage.id
          ? {
              id: Date.now().toString(),
              role: 'assistant' as const,
              content: '❌ Sorry, I encountered an error. Please try again.',
              timestamp: new Date().toISOString()
            }
          : msg
      ))
    } finally {
      setIsLoading(false)
    }
  }

  const copyMessage = async (content: string, id: string) => {
    try {
      await navigator.clipboard.writeText(content)
      setCopiedId(id)
      setTimeout(() => setCopiedId(null), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-7xl w-full max-h-[90vh] overflow-hidden flex">
        {/* LEFT: Review Content (50%) */}
        <div className="w-[50%] flex flex-col border-r border-gray-200">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50">
            <div className="flex items-center space-x-3">
              <ClipboardCheck className="h-6 w-6 text-blue-600" />
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Article Review</h2>
                <p className="text-xs text-gray-600">Scientific Peer Review</p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              {/* Execution Details Button - Icon Only */}
              {traces && traces.length > 0 && (
                <button
                  onClick={() => setShowExecutionDetails(true)}
                  className="relative p-2 bg-blue-50 text-blue-600 rounded-md hover:bg-blue-100 transition-colors"
                  title="View review execution details"
                >
                  <Activity className="h-4 w-4" />
                  {traces.length > 0 && (
                    <span className="absolute -top-1 -right-1 bg-blue-600 text-white text-xs rounded-full h-4 w-4 flex items-center justify-center">
                      {traces.length}
                    </span>
                  )}
                </button>
              )}
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="h-6 w-6" />
              </button>
            </div>
          </div>

          {/* Review Content - Scrollable */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
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
            <MarkdownRenderer content={review.overall_assessment} variant="compact" />
          </div>

          {/* Dimensional Assessment Cards */}
          {review.data_quality && (
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <button
                onClick={() => setExpandedDimension(expandedDimension === 'dq' ? null : 'dq')}
                className="w-full px-5 py-4 bg-purple-50 hover:bg-purple-100 transition-colors"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-3">
                    {expandedDimension === 'dq' ? <ChevronDown className="h-5 w-5 text-purple-600" /> : <ChevronRight className="h-5 w-5 text-purple-600" />}
                    <span className="font-semibold text-gray-900">Data Quality Assessment</span>
                  </div>
                  <div className="flex items-center space-x-3">
                    <span className="text-sm text-gray-600">{review.data_quality.rating.label}</span>
                    <span className="text-yellow-500 font-semibold">
                      {'★'.repeat(review.data_quality.rating.score)}{'☆'.repeat(5 - review.data_quality.rating.score)}
                    </span>
                  </div>
                </div>
                <p className="text-sm text-gray-700 italic text-left pl-8">{review.data_quality.rating.summary}</p>
              </button>
              {expandedDimension === 'dq' && (
                <div className="p-5 bg-white space-y-4 border-t border-gray-200">
                  <div>
                    <h4 className="text-sm font-semibold text-gray-800 mb-1">Provenance</h4>
                    <MarkdownRenderer content={review.data_quality.provenance} variant="compact" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-800 mb-1">Quality</h4>
                    <MarkdownRenderer content={review.data_quality.quality} variant="compact" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-800 mb-1">Quantity</h4>
                    <MarkdownRenderer content={review.data_quality.quantity} variant="compact" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-800 mb-1">Appropriateness</h4>
                    <MarkdownRenderer content={review.data_quality.appropriateness} variant="compact" />
                  </div>
                </div>
              )}
            </div>
          )}

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
                    <MarkdownRenderer content={review.research_question.relevance} variant="compact" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-800 mb-1">Clarity</h4>
                    <MarkdownRenderer content={review.research_question.clarity} variant="compact" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-800 mb-1">Scope</h4>
                    <MarkdownRenderer content={review.research_question.scope} variant="compact" />
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
                    <MarkdownRenderer content={review.methodology.approach_validity} variant="compact" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-800 mb-1">Assumptions</h4>
                    <MarkdownRenderer content={review.methodology.assumptions} variant="compact" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-800 mb-1">Reproducibility</h4>
                    <MarkdownRenderer content={review.methodology.reproducibility} variant="compact" />
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
                    <MarkdownRenderer content={review.results_communication.accuracy} variant="compact" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-800 mb-1">Clarity</h4>
                    <MarkdownRenderer content={review.results_communication.clarity} variant="compact" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-800 mb-1">Completeness</h4>
                    <MarkdownRenderer content={review.results_communication.completeness} variant="compact" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-800 mb-1">Methodology Text</h4>
                    <MarkdownRenderer content={review.results_communication.methodology_text} variant="compact" />
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
                    <MarkdownRenderer content={strength} variant="compact" className="flex-1" />
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
                            <MarkdownRenderer content={issue.description} variant="compact" />
                          </div>
                          <div>
                            <h5 className="text-xs font-semibold text-gray-700 mb-1">Impact</h5>
                            <MarkdownRenderer content={issue.impact} variant="compact" />
                          </div>
                          <div>
                            <h5 className="text-xs font-semibold text-gray-700 mb-1">💡 Suggestion</h5>
                            <MarkdownRenderer content={issue.suggestion} variant="compact" />
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
                    <MarkdownRenderer content={rec} variant="compact" className="flex-1" />
                  </li>
                ))}
              </ul>
            </div>
          )}
          </div>
        </div>

        {/* RIGHT: Embedded Chat (50%) */}
        <div className="w-[50%] flex flex-col bg-gray-50">
          {/* Chat Header - Amber for reviewer mode */}
          <div className="bg-amber-600 text-white p-4">
            <div className="flex items-center space-x-2">
              <MessageCircle className="h-5 w-5" />
              <div>
                <h3 className="font-semibold">Discuss Review</h3>
                <p className="text-xs opacity-90">Ask follow-up questions</p>
              </div>
            </div>
          </div>

          {/* Hint Banner */}
          <div className="bg-amber-50 border-b border-amber-200 p-3">
            <p className="text-sm text-amber-800">
              💬 <strong>Ask the reviewer follow-up questions</strong> about findings, suggestions, or how to address issues.
            </p>
          </div>

          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="text-center py-8">
                <MessageCircle className="h-12 w-12 text-gray-300 mx-auto mb-3" />
                <p className="text-sm text-gray-500">Ask the reviewer about the review findings!</p>
              </div>
            ) : (
              messages.map((message) => (
                <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[90%] rounded-lg px-4 py-2 ${
                    message.role === 'user'
                      ? 'bg-amber-600 text-white'
                      : 'bg-white text-gray-900 border border-gray-200'
                  }`}>
                    {message.loading ? (
                      <div className="flex items-center space-x-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span className="text-sm text-gray-600">Thinking...</span>
                      </div>
                    ) : (
                      <>
                        <MarkdownRenderer
                          content={message.content}
                          variant={message.role === 'user' ? 'inverted' : 'compact'}
                          className="text-sm leading-relaxed"
                        />
                        {message.role === 'assistant' && (
                          <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-200">
                            <span className="text-xs text-gray-500">
                              {new Date(message.timestamp).toLocaleTimeString([], {
                                hour: '2-digit',
                                minute: '2-digit'
                              })}
                            </span>
                            <button
                              onClick={() => copyMessage(message.content, message.id)}
                              className="text-gray-500 hover:text-gray-700 transition-colors"
                              title="Copy message"
                            >
                              {copiedId === message.id ? (
                                <Check className="h-3 w-3 text-green-500" />
                              ) : (
                                <Copy className="h-3 w-3" />
                              )}
                            </button>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Chat Input */}
          <div className="border-t border-gray-200 p-4 bg-white">
            <div className="flex space-x-2">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about the review..."
                className="flex-1 resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                rows={2}
                disabled={isLoading}
              />
              <button
                onClick={handleSendMessage}
                disabled={!inputValue.trim() || isLoading}
                className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
                title="Send message"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Execution Details Modal */}
      {showExecutionDetails && (
        <ExecutionDetailsModal
          isVisible={showExecutionDetails}
          cellId=""
          notebookId=""
          traces={traces}
          executionResult={null}
          onClose={() => setShowExecutionDetails(false)}
        />
      )}

    </div>
  )
}

export default ArticleReviewModal
