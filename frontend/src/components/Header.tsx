import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { BookOpen, Plus, Save, Download, AlertTriangle, ChevronDown, Settings, ClipboardCheck } from 'lucide-react'
import SettingsModal from './SettingsModal'
import ArticleQuickAccess from './ArticleQuickAccess'
import ArticleBrowserModal from './ArticleBrowserModal'

interface HeaderProps {
  onNewNotebook?: () => void
  onSaveNotebook?: () => void
  onExportNotebook?: () => void
  onExportSemantic?: () => void
  onViewKnowledgeGraph?: (graphType: 'analysis' | 'profile') => void
  onExportPDF?: (includeCode: boolean) => void
  onSelectNotebook?: (notebookId: string) => void
  onDeleteNotebook?: (notebookId: string) => void
  onReviewArticle?: () => void
  isGeneratingPDF?: boolean
  isReviewingArticle?: boolean
  currentNotebookId?: string
  currentNotebookTitle?: string
}

const Header: React.FC<HeaderProps> = ({
  onNewNotebook,
  onSaveNotebook,
  onExportNotebook,
  onExportSemantic,
  onViewKnowledgeGraph,
  onExportPDF,
  onSelectNotebook,
  onDeleteNotebook,
  onReviewArticle,
  isGeneratingPDF = false,
  isReviewingArticle = false,
  currentNotebookId,
  currentNotebookTitle
}) => {
  const [showConfirmModal, setShowConfirmModal] = useState(false)
  const [showExportDropdown, setShowExportDropdown] = useState(false)
  const [showSettingsModal, setShowSettingsModal] = useState(false)
  const [showBrowserModal, setShowBrowserModal] = useState(false)

  const handleNewNotebook = () => {
    setShowConfirmModal(true)
  }

  const confirmNewNotebook = () => {
    setShowConfirmModal(false)
    onNewNotebook?.()
  }

  const cancelNewNotebook = () => {
    setShowConfirmModal(false)
  }

  return (
    <>
      <header className="fixed top-0 left-0 right-0 z-50 bg-white shadow-sm border-b border-gray-200">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            {/* Logo and Article Selector */}
            <div className="flex items-center space-x-4">
              <Link to="/" className="flex items-center space-x-2 text-blue-600 hover:text-blue-700">
                <BookOpen className="h-8 w-8" />
                <span className="text-xl font-bold">Digital Article</span>
              </Link>
              
              {/* Article Quick Access */}
              <ArticleQuickAccess
                currentArticleId={currentNotebookId}
                currentArticleTitle={currentNotebookTitle}
                onSelectArticle={(id) => onSelectNotebook?.(id)}
                onNewArticle={() => onNewNotebook?.()}
                onBrowseAll={() => setShowBrowserModal(true)}
              />
            </div>

            {/* Action Buttons */}
            <div className="flex items-center space-x-2">
              {/* Settings Icon */}
              <button
                onClick={() => setShowSettingsModal(true)}
                className="p-2.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                title="Settings"
              >
                <Settings className="h-5 w-5" />
              </button>

              {/* New Button */}
              <button
                onClick={handleNewNotebook}
                className="inline-flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium rounded-lg transition-colors"
                title="New Digital Article"
              >
                <Plus className="h-4 w-4" />
                <span>New</span>
              </button>

              {/* Review Article Button */}
              {currentNotebookId && (
                <button
                  onClick={onReviewArticle}
                  disabled={isReviewingArticle}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-purple-50 hover:bg-purple-100 text-purple-700 font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Review Article Quality"
                >
                  <ClipboardCheck className="h-4 w-4" />
                  <span>{isReviewingArticle ? 'Reviewing...' : 'Review'}</span>
                </button>
              )}

              {/* Save Dropdown (consolidates Save + Export) */}
              <div className="relative">
                <button
                  onClick={() => setShowExportDropdown(!showExportDropdown)}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Save Digital Article"
                  disabled={isGeneratingPDF}
                >
                  <Save className="h-4 w-4" />
                  <span>{isGeneratingPDF ? 'Generating...' : 'Save'}</span>
                  <ChevronDown className="h-4 w-4" />
                </button>

                {showExportDropdown && (
                  <>
                    {/* Invisible overlay to close dropdown when clicking outside */}
                    <div
                      className="fixed inset-0 z-40"
                      onClick={() => setShowExportDropdown(false)}
                    ></div>
                    <div className="absolute right-0 mt-2 w-56 bg-white border border-gray-200 rounded-md shadow-lg z-50">
                    <div className="py-1">
                      <button
                        onClick={() => {
                          onSaveNotebook?.()
                          setShowExportDropdown(false)
                        }}
                        className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center space-x-2"
                      >
                        <Save className="h-4 w-4" />
                        <span>Save Digital Article</span>
                      </button>

                      <div className="border-t border-gray-200 my-1"></div>

                      <button
                        onClick={() => {
                          onExportNotebook?.()
                          setShowExportDropdown(false)
                        }}
                        className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center space-x-2"
                      >
                        <Download className="h-4 w-4" />
                        <span>Export as JSON</span>
                      </button>

                      <button
                        onClick={() => {
                          onExportSemantic?.()
                          setShowExportDropdown(false)
                        }}
                        className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center space-x-2"
                      >
                        <Download className="h-4 w-4" />
                        <span>Export as JSON-LD</span>
                      </button>

                      <button
                        onClick={() => {
                          onExportPDF?.(false)
                          setShowExportDropdown(false)
                        }}
                        className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center space-x-2"
                      >
                        <Download className="h-4 w-4" />
                        <span>Export as PDF</span>
                      </button>
                      
                      <button
                        onClick={() => {
                          onExportPDF?.(true)
                          setShowExportDropdown(false)
                        }}
                        className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center space-x-2"
                      >
                        <Download className="h-4 w-4" />
                        <span>Export PDF with Code</span>
                      </button>

                      <div className="border-t border-gray-200 my-1"></div>

                      <button
                        onClick={() => {
                          onViewKnowledgeGraph?.('analysis')
                          setShowExportDropdown(false)
                        }}
                        className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center space-x-2"
                      >
                        <span>🔬</span>
                        <span>View Analysis Flow</span>
                      </button>

                      <button
                        onClick={() => {
                          onViewKnowledgeGraph?.('profile')
                          setShowExportDropdown(false)
                        }}
                        className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center space-x-2"
                      >
                        <span>👤</span>
                        <span>View Data & Skills Profile</span>
                      </button>
                    </div>
                  </div>
                  </>
                )}
              </div>
            </div>

          </div>
        </div>
      </header>

      {/* Settings Modal */}
      {showSettingsModal && (
        <SettingsModal
          isOpen={showSettingsModal}
          onClose={() => setShowSettingsModal(false)}
          notebookId={currentNotebookId}
        />
      )}

      {/* Article Browser Modal */}
      <ArticleBrowserModal
        isOpen={showBrowserModal}
        onClose={() => setShowBrowserModal(false)}
        onSelectArticle={(id) => onSelectNotebook?.(id)}
        onDeleteArticle={onDeleteNotebook}
        currentArticleId={currentNotebookId}
      />

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            {/* Background overlay */}
            <div 
              className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
              onClick={cancelNewNotebook}
            ></div>

            {/* Modal panel */}
            <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <div className="sm:flex sm:items-start">
                  <div className="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-red-100 sm:mx-0 sm:h-10 sm:w-10">
                    <AlertTriangle className="h-6 w-6 text-red-600" />
                  </div>
                  <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
                    <h3 className="text-lg leading-6 font-medium text-gray-900">
                      Create New Digital Article?
                    </h3>
                    <div className="mt-2">
                      <p className="text-sm text-gray-500">
                        Are you sure you want to create a new digital article? Any unsaved changes to the current article will be lost.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button
                  type="button"
                  className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-red-600 text-base font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 sm:ml-3 sm:w-auto sm:text-sm"
                  onClick={confirmNewNotebook}
                >
                  Yes, Create New
                </button>
                <button
                  type="button"
                  className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                  onClick={cancelNewNotebook}
                >
                  No, Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default Header
