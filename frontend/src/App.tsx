import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import NotebookContainer from './components/NotebookContainer'
import { ToasterProvider } from './contexts/ToasterContext'
import { ModelDownloadProvider } from './contexts/ModelDownloadContext'

function App() {
  return (
    <ToasterProvider>
      <ModelDownloadProvider>
        <Router>
          <div className="min-h-screen bg-gray-50">
            <Routes>
              <Route path="/" element={<NotebookContainer />} />
              <Route path="/notebook/:notebookId" element={<NotebookContainer />} />
            </Routes>
          </div>
        </Router>
      </ModelDownloadProvider>
    </ToasterProvider>
  )
}

export default App
