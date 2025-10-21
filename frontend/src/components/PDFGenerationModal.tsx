import React from 'react'
import { Loader2, FileText, Brain, Sparkles } from 'lucide-react'

interface PDFGenerationModalProps {
  isVisible: boolean
  stage: 'analyzing' | 'regenerating_abstract' | 'planning_article' | 'writing_introduction' | 'writing_methodology' | 'writing_results' | 'writing_discussion' | 'writing_conclusions' | 'creating_pdf' | 'complete'
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
          progress: 5
        }
      case 'regenerating_abstract':
        return {
          icon: <Sparkles className="h-8 w-8 text-blue-500" />,
          title: 'Regenerating Abstract',
          description: 'Creating current abstract based on all research data...',
          progress: 15
        }
      case 'planning_article':
        return {
          icon: <Brain className="h-8 w-8 text-purple-500" />,
          title: 'Planning Article Structure',
          description: 'AI is analyzing research and creating article outline...',
          progress: 25
        }
      case 'writing_introduction':
        return {
          icon: <Sparkles className="h-8 w-8 text-purple-500" />,
          title: 'Writing Introduction',
          description: 'Crafting compelling introduction with context and objectives...',
          progress: 35
        }
      case 'writing_methodology':
        return {
          icon: <Sparkles className="h-8 w-8 text-purple-500" />,
          title: 'Writing Methodology',
          description: 'Describing analytical approaches and implementation details...',
          progress: 50
        }
      case 'writing_results':
        return {
          icon: <Sparkles className="h-8 w-8 text-purple-500" />,
          title: 'Writing Results',
          description: 'Presenting key findings with empirical evidence...',
          progress: 65
        }
      case 'writing_discussion':
        return {
          icon: <Sparkles className="h-8 w-8 text-purple-500" />,
          title: 'Writing Discussion',
          description: 'Interpreting results and discussing implications...',
          progress: 75
        }
      case 'writing_conclusions':
        return {
          icon: <Sparkles className="h-8 w-8 text-purple-500" />,
          title: 'Writing Conclusions',
          description: 'Summarizing contributions and future directions...',
          progress: 85
        }
      case 'creating_pdf':
        return {
          icon: <FileText className="h-8 w-8 text-green-500" />,
          title: 'Creating PDF Document',
          description: 'Formatting article with figures and assembling final PDF...',
          progress: 95
        }
      case 'complete':
        return {
          icon: <FileText className="h-8 w-8 text-green-500" />,
          title: 'Scientific Article Generated',
          description: 'Your publication-ready article is ready for download.',
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
              <div className="flex flex-wrap justify-center gap-2 text-xs text-gray-500">
                <div className={`flex items-center space-x-1 ${stageInfo.progress > 5 ? 'text-blue-600' : ''}`}>
                  <div className={`w-2 h-2 rounded-full ${stageInfo.progress > 5 ? 'bg-blue-600' : 'bg-gray-300'}`}></div>
                  <span>Analyze</span>
                </div>
                <div className={`flex items-center space-x-1 ${stageInfo.progress > 15 ? 'text-blue-600' : ''}`}>
                  <div className={`w-2 h-2 rounded-full ${stageInfo.progress > 15 ? 'bg-blue-600' : 'bg-gray-300'}`}></div>
                  <span>Abstract</span>
                </div>
                <div className={`flex items-center space-x-1 ${stageInfo.progress > 25 ? 'text-purple-600' : ''}`}>
                  <div className={`w-2 h-2 rounded-full ${stageInfo.progress > 25 ? 'bg-purple-600' : 'bg-gray-300'}`}></div>
                  <span>Plan</span>
                </div>
                <div className={`flex items-center space-x-1 ${stageInfo.progress > 35 ? 'text-purple-600' : ''}`}>
                  <div className={`w-2 h-2 rounded-full ${stageInfo.progress > 35 ? 'bg-purple-600' : 'bg-gray-300'}`}></div>
                  <span>Intro</span>
                </div>
                <div className={`flex items-center space-x-1 ${stageInfo.progress > 50 ? 'text-purple-600' : ''}`}>
                  <div className={`w-2 h-2 rounded-full ${stageInfo.progress > 50 ? 'bg-purple-600' : 'bg-gray-300'}`}></div>
                  <span>Methods</span>
                </div>
                <div className={`flex items-center space-x-1 ${stageInfo.progress > 65 ? 'text-purple-600' : ''}`}>
                  <div className={`w-2 h-2 rounded-full ${stageInfo.progress > 65 ? 'bg-purple-600' : 'bg-gray-300'}`}></div>
                  <span>Results</span>
                </div>
                <div className={`flex items-center space-x-1 ${stageInfo.progress > 75 ? 'text-purple-600' : ''}`}>
                  <div className={`w-2 h-2 rounded-full ${stageInfo.progress > 75 ? 'bg-purple-600' : 'bg-gray-300'}`}></div>
                  <span>Discussion</span>
                </div>
                <div className={`flex items-center space-x-1 ${stageInfo.progress > 85 ? 'text-purple-600' : ''}`}>
                  <div className={`w-2 h-2 rounded-full ${stageInfo.progress > 85 ? 'bg-purple-600' : 'bg-gray-300'}`}></div>
                  <span>Conclusions</span>
                </div>
                <div className={`flex items-center space-x-1 ${stageInfo.progress > 95 ? 'text-green-600' : ''}`}>
                  <div className={`w-2 h-2 rounded-full ${stageInfo.progress > 95 ? 'bg-green-600' : 'bg-gray-300'}`}></div>
                  <span>PDF</span>
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






