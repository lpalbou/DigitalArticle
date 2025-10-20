import React from 'react'
import { Loader2, FileText, Brain, Sparkles } from 'lucide-react'

interface PDFGenerationModalProps {
  isVisible: boolean
  stage: 'analyzing' | 'generating_content' | 'creating_pdf' | 'complete'
}

const PDFGenerationModal: React.FC<PDFGenerationModalProps> = ({
  isVisible,
  stage
}) => {
  if (!isVisible) return null

  const getStageInfo = () => {
    switch (stage) {
      case 'analyzing':
        return {
          icon: <Brain className="h-8 w-8 text-blue-500" />,
          title: 'Analyzing Content',
          description: 'Examining notebook cells and extracting insights...',
          progress: 25
        }
      case 'generating_content':
        return {
          icon: <Sparkles className="h-8 w-8 text-purple-500" />,
          title: 'Generating Scientific Content',
          description: 'Creating abstract, introduction, and conclusions with AI...',
          progress: 60
        }
      case 'creating_pdf':
        return {
          icon: <FileText className="h-8 w-8 text-green-500" />,
          title: 'Creating PDF Document',
          description: 'Formatting and assembling the scientific article...',
          progress: 90
        }
      case 'complete':
        return {
          icon: <FileText className="h-8 w-8 text-green-500" />,
          title: 'PDF Generated Successfully',
          description: 'Your scientific article is ready for download.',
          progress: 100
        }
      default:
        return {
          icon: <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />,
          title: 'Processing',
          description: 'Preparing your scientific article...',
          progress: 0
        }
    }
  }

  const stageInfo = getStageInfo()

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"></div>

        {/* Modal panel */}
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <div className="bg-white px-6 pt-6 pb-4">
            <div className="flex flex-col items-center">
              {/* Icon */}
              <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-gray-100 mb-4">
                {stage === 'complete' ? stageInfo.icon : <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />}
              </div>

              {/* Title */}
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-2">
                {stageInfo.title}
              </h3>

              {/* Description */}
              <p className="text-sm text-gray-500 text-center mb-6">
                {stageInfo.description}
              </p>

              {/* Progress bar */}
              <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
                <div 
                  className="bg-blue-600 h-2 rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${stageInfo.progress}%` }}
                ></div>
              </div>

              {/* Progress percentage */}
              <div className="text-sm text-gray-600 mb-4">
                {stageInfo.progress}% Complete
              </div>

              {/* Stage indicators */}
              <div className="flex space-x-4 text-xs text-gray-500">
                <div className={`flex items-center space-x-1 ${stage === 'analyzing' || stageInfo.progress > 25 ? 'text-blue-600' : ''}`}>
                  <div className={`w-2 h-2 rounded-full ${stageInfo.progress > 25 ? 'bg-blue-600' : 'bg-gray-300'}`}></div>
                  <span>Analyze</span>
                </div>
                <div className={`flex items-center space-x-1 ${stage === 'generating_content' || stageInfo.progress > 60 ? 'text-purple-600' : ''}`}>
                  <div className={`w-2 h-2 rounded-full ${stageInfo.progress > 60 ? 'bg-purple-600' : 'bg-gray-300'}`}></div>
                  <span>Generate</span>
                </div>
                <div className={`flex items-center space-x-1 ${stage === 'creating_pdf' || stageInfo.progress > 90 ? 'text-green-600' : ''}`}>
                  <div className={`w-2 h-2 rounded-full ${stageInfo.progress > 90 ? 'bg-green-600' : 'bg-gray-300'}`}></div>
                  <span>Create PDF</span>
                </div>
              </div>
            </div>
          </div>

          {stage === 'complete' && (
            <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
              <button
                type="button"
                className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-green-600 text-base font-medium text-white hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 sm:ml-3 sm:w-auto sm:text-sm"
                onClick={() => window.location.reload()} // Simple way to close modal
              >
                Continue
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default PDFGenerationModal






