import React, { useState, useEffect, useMemo, useRef } from 'react'
import { 
  X, 
  Search, 
  User, 
  FileText, 
  Play, 
  BookOpen, 
  Trash2, 
  ExternalLink,
  Filter,
  Clock,
  CheckCircle,
  AlertCircle,
  Circle
} from 'lucide-react'
import { notebookAPI, handleAPIError } from '../services/api'

interface ArticleSummary {
  id: string
  title: string
  description: string
  author: string
  created_at: string
  updated_at: string
  latest_activity: string
  tags: string[]
  llm_provider: string
  llm_model: string
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

interface ArticleBrowserModalProps {
  isOpen: boolean
  onClose: () => void
  onSelectArticle: (articleId: string) => void
  onDeleteArticle?: (articleId: string) => void
  currentArticleId?: string
}

type SortField = 'title' | 'updated_at' | 'created_at' | 'execution_rate'
type SortDirection = 'asc' | 'desc'

const ArticleBrowserModal: React.FC<ArticleBrowserModalProps> = ({
  isOpen,
  onClose,
  onSelectArticle,
  onDeleteArticle,
  currentArticleId
}) => {
  const [articles, setArticles] = useState<ArticleSummary[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [sortField, setSortField] = useState<SortField>('updated_at')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [filterStatus, setFilterStatus] = useState<'all' | 'with_content' | 'with_results' | 'empty'>('all')
  const scrollContainerRef = useRef<HTMLDivElement>(null)

  // Load articles when modal opens
  useEffect(() => {
    if (isOpen) {
      loadArticles()
    }
  }, [isOpen])

  const loadArticles = async (preserveScroll: boolean = false) => {
    // Store current scroll position if we want to preserve it
    const scrollTop = preserveScroll ? (scrollContainerRef.current?.scrollTop || 0) : 0
    
    setLoading(true)
    setError(null)
    
    try {
      const summaries = await notebookAPI.getSummaries()
      setArticles(summaries)
      
      // Restore scroll position if requested
      if (preserveScroll) {
        requestAnimationFrame(() => {
          if (scrollContainerRef.current) {
            scrollContainerRef.current.scrollTop = scrollTop
          }
        })
      }
    } catch (err) {
      const apiError = handleAPIError(err)
      setError(apiError.message)
    } finally {
      setLoading(false)
    }
  }

  // Filter and sort articles
  const filteredAndSortedArticles = useMemo(() => {
    const filtered = articles.filter(article => {
      // Search filter
      const matchesSearch = searchQuery === '' || 
        article.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        article.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        article.author.toLowerCase().includes(searchQuery.toLowerCase())

      // Status filter
      const matchesStatus = filterStatus === 'all' ||
        (filterStatus === 'with_content' && article.status.has_content) ||
        (filterStatus === 'with_results' && article.status.has_results) ||
        (filterStatus === 'empty' && article.status.is_empty)

      return matchesSearch && matchesStatus
    })

    // Sort
    filtered.sort((a, b) => {
      let aValue: any, bValue: any

      switch (sortField) {
        case 'title':
          aValue = a.title.toLowerCase()
          bValue = b.title.toLowerCase()
          break
        case 'created_at':
          aValue = new Date(a.created_at).getTime()
          bValue = new Date(b.created_at).getTime()
          break
        case 'updated_at':
          aValue = new Date(a.latest_activity).getTime()
          bValue = new Date(b.latest_activity).getTime()
          break
        case 'execution_rate':
          aValue = a.statistics.execution_rate
          bValue = b.statistics.execution_rate
          break
        default:
          return 0
      }

      if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1
      if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1
      return 0
    })

    return filtered
  }, [articles, searchQuery, sortField, sortDirection, filterStatus])

  const handleSelectArticle = (articleId: string) => {
    onSelectArticle(articleId)
    onClose()
  }

  const handleDeleteArticle = async (articleId: string, event: React.MouseEvent) => {
    event.stopPropagation()
    
    if (!onDeleteArticle) return
    
    if (window.confirm('Are you sure you want to delete this digital article? This action cannot be undone.')) {
      // Store current scroll position
      const scrollTop = scrollContainerRef.current?.scrollTop || 0
      
      // Optimistically remove the article from the list (immediate UI feedback)
      const originalArticles = [...articles]
      setArticles(prev => prev.filter(article => article.id !== articleId))
      
      try {
        await onDeleteArticle(articleId)
        // Success - the optimistic update was correct, no need to reload
        
        // Restore scroll position after the DOM updates
        requestAnimationFrame(() => {
          if (scrollContainerRef.current) {
            scrollContainerRef.current.scrollTop = scrollTop
          }
        })
        
      } catch (err) {
        // Error - restore the original list and show error
        setArticles(originalArticles)
        const apiError = handleAPIError(err)
        setError(apiError.message)
        
        // Restore scroll position
        requestAnimationFrame(() => {
          if (scrollContainerRef.current) {
            scrollContainerRef.current.scrollTop = scrollTop
          }
        })
      }
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
    
    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays} days ago`
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
    if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`
    return `${Math.floor(diffDays / 365)} years ago`
  }

  const getStatusIcon = (article: ArticleSummary) => {
    if (article.status.is_empty) return <Circle className="h-4 w-4 text-gray-400" />
    if (article.status.has_results) return <CheckCircle className="h-4 w-4 text-green-500" />
    if (article.status.has_content) return <AlertCircle className="h-4 w-4 text-yellow-500" />
    return <Circle className="h-4 w-4 text-gray-400" />
  }

  const getStatusText = (article: ArticleSummary) => {
    if (article.status.is_empty) return 'Empty'
    if (article.status.has_results) return 'Complete'
    if (article.status.has_content) return 'Draft'
    return 'Empty'
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div 
          className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          onClick={onClose}
        />

        {/* Modal panel */}
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-6xl sm:w-full">
          {/* Header */}
          <div className="bg-white px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg leading-6 font-medium text-gray-900">
                  Browse Digital Articles
                </h3>
                <p className="mt-1 text-sm text-gray-500">
                  {filteredAndSortedArticles.length} of {articles.length} articles
                </p>
              </div>
              <button
                onClick={onClose}
                className="bg-white rounded-md text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <X className="h-6 w-6" />
              </button>
            </div>

            {/* Search and filters */}
            <div className="mt-4 flex flex-col sm:flex-row gap-4">
              {/* Search */}
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search articles..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              {/* Status filter */}
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value as any)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Articles</option>
                <option value="with_results">Complete</option>
                <option value="with_content">Draft</option>
                <option value="empty">Empty</option>
              </select>

              {/* Sort */}
              <div className="flex items-center space-x-2">
                <Filter className="h-4 w-4 text-gray-400" />
                <select
                  value={`${sortField}_${sortDirection}`}
                  onChange={(e) => {
                    const [field, direction] = e.target.value.split('_')
                    setSortField(field as SortField)
                    setSortDirection(direction as SortDirection)
                  }}
                  className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="updated_at_desc">Latest First</option>
                  <option value="updated_at_asc">Oldest First</option>
                  <option value="title_asc">Title A-Z</option>
                  <option value="title_desc">Title Z-A</option>
                  <option value="created_at_desc">Newest Created</option>
                  <option value="created_at_asc">Oldest Created</option>
                  <option value="execution_rate_desc">Most Complete</option>
                  <option value="execution_rate_asc">Least Complete</option>
                </select>
              </div>
            </div>
          </div>

          {/* Content */}
          <div 
            ref={scrollContainerRef}
            className="bg-gray-50 px-6 py-4 max-h-96 overflow-y-auto"
          >
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full" />
                <span className="ml-3 text-gray-600">Loading articles...</span>
              </div>
            ) : error ? (
              <div className="text-center py-12">
                <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
                <p className="text-gray-600 mb-4">{error}</p>
                <button
                  onClick={() => loadArticles(false)}
                  className="btn btn-primary"
                >
                  Try Again
                </button>
              </div>
            ) : filteredAndSortedArticles.length === 0 ? (
              <div className="text-center py-12">
                <BookOpen className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600">
                  {searchQuery || filterStatus !== 'all' ? 'No articles match your criteria' : 'No digital articles found'}
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {filteredAndSortedArticles.map((article) => (
                  <div
                    key={article.id}
                    onClick={() => handleSelectArticle(article.id)}
                    className={`bg-white rounded-lg border p-4 cursor-pointer hover:border-blue-300 hover:shadow-md transition-all ${
                      currentArticleId === article.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        {/* Title and status */}
                        <div className="flex items-center space-x-2 mb-2">
                          {getStatusIcon(article)}
                          <h4 className="text-lg font-medium text-gray-900 truncate">
                            {article.title}
                          </h4>
                          <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded-full">
                            {getStatusText(article)}
                          </span>
                          {currentArticleId === article.id && (
                            <span className="text-xs px-2 py-1 bg-blue-100 text-blue-600 rounded-full">
                              Current
                            </span>
                          )}
                        </div>

                        {/* Description */}
                        {article.description && (
                          <p className="text-sm text-gray-600 mb-3 line-clamp-2">
                            {article.description}
                          </p>
                        )}

                        {/* Metadata row */}
                        <div className="flex items-center space-x-4 text-xs text-gray-500 mb-3">
                          <div className="flex items-center space-x-1">
                            <User className="h-3 w-3" />
                            <span>{article.author}</span>
                          </div>
                          <div className="flex items-center space-x-1">
                            <Clock className="h-3 w-3" />
                            <span>{formatDate(article.latest_activity)}</span>
                          </div>
                          <div className="flex items-center space-x-1">
                            <FileText className="h-3 w-3" />
                            <span>{article.statistics.total_cells} cells</span>
                          </div>
                          {article.statistics.execution_rate > 0 && (
                            <div className="flex items-center space-x-1">
                              <Play className="h-3 w-3" />
                              <span>{article.statistics.execution_rate}% executed</span>
                            </div>
                          )}
                        </div>

                        {/* Statistics */}
                        <div className="flex items-center space-x-4 text-xs">
                          {article.statistics.cells_with_prompts > 0 && (
                            <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded">
                              {article.statistics.cells_with_prompts} prompts
                            </span>
                          )}
                          {article.statistics.cells_with_code > 0 && (
                            <span className="px-2 py-1 bg-green-100 text-green-700 rounded">
                              {article.statistics.cells_with_code} code
                            </span>
                          )}
                          {article.statistics.cells_with_methodology > 0 && (
                            <span className="px-2 py-1 bg-orange-100 text-orange-700 rounded">
                              {article.statistics.cells_with_methodology} methodology
                            </span>
                          )}
                          {article.statistics.cells_with_markdown > 0 && (
                            <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded">
                              {article.statistics.cells_with_markdown} docs
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center space-x-2 ml-4">
                        {onDeleteArticle && (
                          <button
                            onClick={(e) => handleDeleteArticle(article.id, e)}
                            className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
                            title="Delete article"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                        <ExternalLink className="h-4 w-4 text-gray-400" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="bg-gray-50 px-6 py-3 border-t border-gray-200">
            <div className="flex items-center justify-between text-sm text-gray-500">
              <div>
                Showing {filteredAndSortedArticles.length} articles
              </div>
              <div className="flex items-center space-x-4">
                <button
                  onClick={() => loadArticles(true)}
                  className="text-blue-600 hover:text-blue-700"
                >
                  Refresh
                </button>
                <button
                  onClick={onClose}
                  className="btn btn-secondary"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ArticleBrowserModal
