import React from 'react'
import { Link } from 'react-router-dom'
import { BookOpen, Plus, Save, Download } from 'lucide-react'

interface HeaderProps {
  onNewNotebook?: () => void
  onSaveNotebook?: () => void
  onExportNotebook?: () => void
}

const Header: React.FC<HeaderProps> = ({
  onNewNotebook,
  onSaveNotebook,
  onExportNotebook
}) => {
  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo and Title */}
          <div className="flex items-center space-x-4">
            <Link to="/" className="flex items-center space-x-2 text-blue-600 hover:text-blue-700">
              <BookOpen className="h-8 w-8" />
              <span className="text-xl font-bold">Digital Article</span>
            </Link>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center space-x-3">
            <button
              onClick={onNewNotebook}
              className="btn btn-secondary flex items-center space-x-2"
              title="New Digital Article"
            >
              <Plus className="h-4 w-4" />
              <span>New</span>
            </button>

            <button
              onClick={onSaveNotebook}
              className="btn btn-primary flex items-center space-x-2"
              title="Save Digital Article"
            >
              <Save className="h-4 w-4" />
              <span>Save</span>
            </button>

            <button
              onClick={onExportNotebook}
              className="btn btn-secondary flex items-center space-x-2"
              title="Export Digital Article"
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
