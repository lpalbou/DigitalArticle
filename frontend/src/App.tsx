import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import NotebookContainer from './components/NotebookContainer'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Routes>
          <Route path="/" element={<NotebookContainer />} />
          <Route path="/notebook/:notebookId" element={<NotebookContainer />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App
