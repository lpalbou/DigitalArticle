import React from 'react'
import { Link } from 'react-router-dom'
import { BookOpen, Plus, Save, Download } from 'lucide-react'

interface HeaderProps {
  onNewNotebook?: () => void
  onSaveNotebook?: () => void
  onExportNotebook?: () => void
  notebookTitle?: string
}

const Header: React.FC<HeaderProps> = ({
  onNewNotebook,
  onSaveNotebook,
  onExportNotebook,
  notebookTitle = 'Untitled Notebook'
}) => {
  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo and Title */}
          <div className="flex items-center space-x-4">
            <Link to="/" className="flex items-center space-x-2 text-blue-600 hover:text-blue-700">
              <BookOpen className="h-8 w-8" />
              <span className="text-xl font-bold">Reverse Analytics</span>
            </Link>
            <div className="h-6 border-l border-gray-300" />
            <h1 className="text-lg font-semibold text-gray-800">{notebookTitle}</h1>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center space-x-3">
            <button
              onClick={onNewNotebook}
              className="btn btn-secondary flex items-center space-x-2"
              title="New Notebook"
            >
              <Plus className="h-4 w-4" />
              <span>New</span>
            </button>

            <button
              onClick={onSaveNotebook}
              className="btn btn-primary flex items-center space-x-2"
              title="Save Notebook"
            >
              <Save className="h-4 w-4" />
              <span>Save</span>
            </button>

            <button
              onClick={onExportNotebook}
              className="btn btn-secondary flex items-center space-x-2"
              title="Export Notebook"
            >
              <Download className="h-4 w-4" />
              <span>Export</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}

export default Header
