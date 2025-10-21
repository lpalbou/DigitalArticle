import React, { useState, useEffect, useRef } from 'react'
import { ChevronDown, Clock, Plus, Search, BookOpen } from 'lucide-react'
import { notebookAPI, handleAPIError } from '../services/api'

interface ArticleSummary {
  id: string
  title: string
  description: string
  author: string
  latest_activity: string
  statistics: {
    total_cells: number
    executed_cells: number
    cells_with_prompts: number
    cells_with_code: number
    cells_with_methodology: number
    cells_with_markdown: number
    execution_rate: number
  }
  status: {
    has_content: boolean
    has_results: boolean
    is_empty: boolean
  }
}

interface ArticleQuickAccessProps {
  currentArticleId?: string
  currentArticleTitle?: string
  onSelectArticle: (articleId: string) => void
  onNewArticle: () => void
  onBrowseAll: () => void
}

const ArticleQuickAccess: React.FC<ArticleQuickAccessProps> = ({
  currentArticleId,
  currentArticleTitle,
  onSelectArticle,
  onNewArticle,
  onBrowseAll
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const [recentArticles, setRecentArticles] = useState<ArticleSummary[]>([])
  const [loading, setLoading] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Load recent articles when dropdown opens
  useEffect(() => {
    if (isOpen && recentArticles.length === 0) {
      loadRecentArticles()
    }
  }, [isOpen])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const loadRecentArticles = async () => {
    setLoading(true)
    
    try {
      const summaries = await notebookAPI.getSummaries()
      // Get the 8 most recent articles (excluding current if present)
      const filtered = summaries
        .filter(article => article.id !== currentArticleId)
        .slice(0, 8)
      setRecentArticles(filtered)
    } catch (err) {
      console.error('Failed to load recent articles:', handleAPIError(err))
    } finally {
      setLoading(false)
    }
  }

  const handleSelectArticle = (articleId: string) => {
    onSelectArticle(articleId)
    setIsOpen(false)
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
    
    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays}d ago`
    if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`
    return `${Math.floor(diffDays / 30)}mo ago`
  }

  const getStatusColor = (article: ArticleSummary) => {
    if (article.status.is_empty) return 'bg-gray-100'
    if (article.status.has_results) return 'bg-green-100'
    if (article.status.has_content) return 'bg-yellow-100'
    return 'bg-gray-100'
  }

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-3 py-2 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
        title="Switch Digital Article"
      >
        <BookOpen className="h-4 w-4 text-gray-500" />
        <span className="max-w-48 truncate text-gray-700">
          {currentArticleTitle || 'Select Article'}
        </span>
        <ChevronDown className={`h-4 w-4 text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-80 bg-white border border-gray-200 rounded-md shadow-lg z-50">
          {/* Header */}
          <div className="px-4 py-3 border-b border-gray-100">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-gray-900">Recent Articles</h3>
              <button
                onClick={() => {
                  onBrowseAll()
                  setIsOpen(false)
                }}
                className="text-xs text-blue-600 hover:text-blue-700 flex items-center space-x-1"
              >
                <Search className="h-3 w-3" />
                <span>Browse All</span>
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="max-h-80 overflow-y-auto">
            {loading ? (
              <div className="px-4 py-6 text-center">
                <div className="animate-spin h-5 w-5 border-2 border-blue-600 border-t-transparent rounded-full mx-auto mb-2" />
                <p className="text-xs text-gray-500">Loading articles...</p>
              </div>
            ) : recentArticles.length === 0 ? (
              <div className="px-4 py-6 text-center">
                <BookOpen className="h-8 w-8 text-gray-400 mx-auto mb-2" />
                <p className="text-sm text-gray-500 mb-3">No other articles found</p>
                <button
                  onClick={() => {
                    onNewArticle()
                    setIsOpen(false)
                  }}
                  className="text-xs text-blue-600 hover:text-blue-700"
                >
                  Create your first article
                </button>
              </div>
            ) : (
              <div className="py-2">
                {recentArticles.map((article) => (
                  <button
                    key={article.id}
                    onClick={() => handleSelectArticle(article.id)}
                    className="w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors border-b border-gray-50 last:border-b-0"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-1">
                          <div className={`w-2 h-2 rounded-full ${getStatusColor(article)}`} />
                          <h4 className="text-sm font-medium text-gray-900 truncate">
                            {article.title}
                          </h4>
                        </div>
                        
                        {article.description && (
                          <p className="text-xs text-gray-600 mb-2 line-clamp-1">
                            {article.description}
                          </p>
                        )}
                        
                        <div className="flex items-center justify-between text-xs text-gray-500">
                          <div className="flex items-center space-x-1">
                            <Clock className="h-3 w-3" />
                            <span>{formatDate(article.latest_activity)}</span>
                          </div>
                          <div className="flex items-center space-x-2">
                            <span>{article.statistics.total_cells} cells</span>
                            {article.statistics.execution_rate > 0 && (
                              <span className="text-green-600">
                                {article.statistics.execution_rate}%
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-4 py-3 border-t border-gray-100 bg-gray-50">
            <div className="flex items-center justify-between">
              <button
                onClick={() => {
                  onNewArticle()
                  setIsOpen(false)
                }}
                className="flex items-center space-x-1 text-xs text-blue-600 hover:text-blue-700"
              >
                <Plus className="h-3 w-3" />
                <span>New Article</span>
              </button>
              
              <button
                onClick={() => {
                  onBrowseAll()
                  setIsOpen(false)
                }}
                className="text-xs text-gray-600 hover:text-gray-700"
              >
                Browse All →
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ArticleQuickAccess
