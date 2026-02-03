import React, { useEffect, useMemo, useRef, useState } from 'react'
import { X, HelpCircle, FileText, Mail, Search, ExternalLink } from 'lucide-react'
import MarkdownRenderer from './MarkdownRenderer'
import { helpAPI, HelpInfoResponse, HelpSearchHit } from '../services/api'

interface HelpModalProps {
  isOpen: boolean
  onClose: () => void
}

type HelpTab = 'docs' | 'pdf' | 'contact'

const HelpModal: React.FC<HelpModalProps> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState<HelpTab>('docs')
  const [loading, setLoading] = useState(false)
  const [info, setInfo] = useState<HelpInfoResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [selectedDocId, setSelectedDocId] = useState<string | null>(null)
  const [selectedDocTitle, setSelectedDocTitle] = useState<string>('')
  const [docContent, setDocContent] = useState<string>('')
  const [docLoading, setDocLoading] = useState(false)

  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<HelpSearchHit[] | null>(null)
  const searchTimerRef = useRef<number | null>(null)

  // Close on ESC + prevent body scroll
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) onClose()
    }

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'hidden'
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'unset'
    }
  }, [isOpen, onClose])

  // Load help info (docs index + contact + pdf availability)
  useEffect(() => {
    if (!isOpen) return

    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await helpAPI.getInfo()
        setInfo(data)

        // Default selection: overview.md if present, otherwise first doc
        const preferred = data.docs.find(d => d.doc_id === 'overview.md') || data.docs[0]
        if (preferred) {
          setSelectedDocId(preferred.doc_id)
          setSelectedDocTitle(preferred.title)
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load help info')
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [isOpen])

  // Load selected doc content
  useEffect(() => {
    if (!isOpen) return
    if (!selectedDocId) return

    const loadDoc = async () => {
      setDocLoading(true)
      try {
        const doc = await helpAPI.getDoc(selectedDocId)
        setSelectedDocTitle(doc.title || selectedDocId)
        setDocContent(doc.content || '')
      } catch (e) {
        setDocContent('')
        setError(e instanceof Error ? e.message : 'Failed to load documentation')
      } finally {
        setDocLoading(false)
      }
    }

    loadDoc()
  }, [isOpen, selectedDocId])

  // Search (debounced)
  useEffect(() => {
    if (!isOpen) return

    const q = searchQuery.trim()
    if (!q) {
      setSearchResults(null)
      return
    }

    // Debounce to avoid spamming the backend
    if (searchTimerRef.current) {
      window.clearTimeout(searchTimerRef.current)
    }
    searchTimerRef.current = window.setTimeout(async () => {
      try {
        const results = await helpAPI.search(q, 25)
        setSearchResults(results)
      } catch {
        // Don’t block the UI on search failures
        setSearchResults([])
      }
    }, 250)

    return () => {
      if (searchTimerRef.current) window.clearTimeout(searchTimerRef.current)
    }
  }, [isOpen, searchQuery])

  const docsList = useMemo(() => info?.docs || [], [info])

  if (!isOpen) return null

  const contactEmail = info?.contact_email || 'lpalbou@gmail.com'
  const pdfUrl = info?.pdf_url || '/api/help/digital-article.pdf'

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        {/* Backdrop */}
        <div
          className="fixed inset-0 bg-gray-900/50 transition-opacity"
          onClick={onClose}
        />

        {/* Modal */}
        <div className="inline-block align-bottom bg-white rounded-xl text-left overflow-hidden shadow-2xl transform transition-all sm:my-8 sm:align-middle w-full max-w-5xl">
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-50 text-blue-700">
                <HelpCircle className="h-5 w-5" />
              </div>
              <div>
                <div className="text-lg font-semibold text-gray-900">Help & Documentation</div>
                <div className="text-xs text-gray-500">
                  Search internal docs and access the Digital Article overview.
                </div>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              title="Close"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Tabs */}
          <div className="px-6 pt-4">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveTab('docs')}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === 'docs'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <span className="inline-flex items-center gap-2">
                  <FileText className="h-4 w-4" /> Docs
                </span>
              </button>
              <button
                onClick={() => setActiveTab('pdf')}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === 'pdf'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <span className="inline-flex items-center gap-2">
                  <FileText className="h-4 w-4" /> PDF
                </span>
              </button>
              <button
                onClick={() => setActiveTab('contact')}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === 'contact'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <span className="inline-flex items-center gap-2">
                  <Mail className="h-4 w-4" /> Contact
                </span>
              </button>
            </div>
          </div>

          {/* Body */}
          <div className="px-6 py-4">
            {loading && (
              <div className="flex items-center gap-3 text-gray-600">
                <div className="animate-spin h-5 w-5 border-2 border-blue-600 border-t-transparent rounded-full" />
                Loading help…
              </div>
            )}

            {!loading && error && (
              <div className="p-3 rounded-lg bg-red-50 text-red-700 text-sm">{error}</div>
            )}

            {!loading && activeTab === 'docs' && (
              <div className="grid grid-cols-12 gap-4">
                {/* Left: search + list */}
                <div className="col-span-12 md:col-span-4">
                  <div className="relative mb-3">
                    <Search className="h-4 w-4 text-gray-400 absolute left-3 top-3" />
                    <input
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search docs…"
                      className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div className="border border-gray-200 rounded-lg overflow-hidden">
                    <div className="bg-gray-50 px-3 py-2 text-xs text-gray-600 flex items-center justify-between">
                      <span>{searchResults ? `Matches (${searchResults.length})` : `Docs (${docsList.length})`}</span>
                      {searchQuery.trim() && (
                        <button
                          onClick={() => setSearchQuery('')}
                          className="text-xs text-blue-600 hover:text-blue-700"
                        >
                          Clear
                        </button>
                      )}
                    </div>

                    <div className="max-h-[60vh] overflow-y-auto">
                      {(searchResults ?? docsList).map((item: any) => {
                        const docId = item.doc_id
                        const title = item.title
                        const isSelected = docId === selectedDocId
                        return (
                          <button
                            key={docId}
                            onClick={() => {
                              setSelectedDocId(docId)
                              setActiveTab('docs')
                            }}
                            className={`w-full text-left px-3 py-2 border-t border-gray-100 hover:bg-gray-50 transition-colors ${
                              isSelected ? 'bg-blue-50' : 'bg-white'
                            }`}
                          >
                            <div className={`text-sm font-medium ${isSelected ? 'text-blue-800' : 'text-gray-900'}`}>
                              {title}
                            </div>
                            {'snippet' in item && item.snippet ? (
                              <div className="text-xs text-gray-600 mt-1 line-clamp-2">{item.snippet}</div>
                            ) : (
                              <div className="text-xs text-gray-500 mt-1">{docId}</div>
                            )}
                          </button>
                        )
                      })}
                      {(searchResults ?? docsList).length === 0 && (
                        <div className="p-4 text-sm text-gray-600">No results.</div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Right: content */}
                <div className="col-span-12 md:col-span-8">
                  <div className="border border-gray-200 rounded-lg overflow-hidden">
                    <div className="bg-gray-50 px-4 py-2 flex items-center justify-between">
                      <div className="text-sm font-medium text-gray-800">
                        {selectedDocTitle || 'Documentation'}
                      </div>
                      {selectedDocId && (
                        <div className="text-xs text-gray-500">{selectedDocId}</div>
                      )}
                    </div>
                    <div className="p-4 max-h-[60vh] overflow-y-auto">
                      {docLoading ? (
                        <div className="flex items-center gap-3 text-gray-600">
                          <div className="animate-spin h-5 w-5 border-2 border-blue-600 border-t-transparent rounded-full" />
                          Loading doc…
                        </div>
                      ) : (
                        <MarkdownRenderer content={docContent || '*No content*'} />
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {!loading && activeTab === 'pdf' && (
              <div className="border border-gray-200 rounded-lg overflow-hidden">
                <div className="bg-gray-50 px-4 py-2 flex items-center justify-between">
                  <div className="text-sm font-medium text-gray-800">Digital Article — overview (PDF)</div>
                  <a
                    href={pdfUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700"
                    title="Open PDF in a new tab"
                  >
                    Open <ExternalLink className="h-4 w-4" />
                  </a>
                </div>
                {info?.pdf_available ? (
                  <iframe
                    title="Digital Article PDF"
                    src={pdfUrl}
                    className="w-full h-[70vh] bg-white"
                  />
                ) : (
                  <div className="p-4 text-sm text-gray-700">
                    <div className="font-medium">PDF not available on this deployment.</div>
                    <div className="text-gray-600 mt-1">
                      Use the <span className="font-medium">Docs</span> tab or contact support via <span className="font-medium">Help → Contact</span>.
                    </div>
                  </div>
                )}
              </div>
            )}

            {!loading && activeTab === 'contact' && (
              <div className="border border-gray-200 rounded-lg p-4">
                <div className="text-sm text-gray-800">
                  Need help or want to reach the team?
                </div>
                <div className="mt-2">
                  <a
                    href={`mailto:${contactEmail}`}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <Mail className="h-4 w-4" />
                    Contact: {contactEmail}
                  </a>
                </div>
                <div className="mt-3 text-xs text-gray-500">
                  If this address is not correct for your organization, contact your administrator.
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
            <div className="text-xs text-gray-500">
              Tip: In the PDF tab, use your browser PDF viewer search (Ctrl/⌘+F).
            </div>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default HelpModal

