import React from 'react'
import { Loader2, Brain, FileCheck, CheckCircle, AlertCircle } from 'lucide-react'

interface ReviewProgressModalProps {
  isVisible: boolean
  progress: number  // 0-100
  stage: 'preparing' | 'building_context' | 'reviewing' | 'parsing' | 'complete' | 'error'
  message: string
  tokens?: number
}

const ReviewProgressModal: React.FC<ReviewProgressModalProps> = ({
  isVisible,
  progress,
  stage,
  message,
  tokens
}) => {
  if (!isVisible) return null

  const getStageInfo = () => {
    switch (stage) {
      case 'preparing':
        return {
          icon: <Brain className="h-8 w-8 text-blue-500" />,
          title: 'Preparing Review',
          description: message || 'Loading notebook content...',
        }
      case 'building_context':
        return {
          icon: <Brain className="h-8 w-8 text-blue-500" />,
          title: 'Building Context',
          description: message || 'Analyzing cells and preparing context...',
        }
      case 'reviewing':
        return {
          icon: <Brain className="h-8 w-8 text-purple-500 animate-pulse" />,
          title: 'AI Review in Progress',
          description: message || 'Evaluating methodology, results, and conclusions...',
        }
      case 'parsing':
        return {
          icon: <FileCheck className="h-8 w-8 text-purple-500" />,
          title: 'Processing Results',
          description: message || 'Parsing review findings and recommendations...',
        }
      case 'complete':
        return {
          icon: <CheckCircle className="h-8 w-8 text-green-500" />,
          title: 'Review Complete',
          description: message || 'Article review has been generated successfully.',
        }
      case 'error':
        return {
          icon: <AlertCircle className="h-8 w-8 text-red-500" />,
          title: 'Review Failed',
          description: message || 'An error occurred during review.',
        }
      default:
        return {
          icon: <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />,
          title: 'Processing',
          description: message || 'Preparing review...',
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
                {stage === 'complete' ? stageInfo.icon :
                 stage === 'error' ? stageInfo.icon :
                 <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />}
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
              {stage !== 'error' && (
                <>
                  <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-500 ease-out"
                      style={{ width: `${progress}%` }}
                    ></div>
                  </div>

                  {/* Progress percentage */}
                  <div className="text-sm text-gray-600 mb-4">
                    {progress}% Complete
                  </div>
                </>
              )}

              {/* Stage indicators */}
              <div className="flex flex-wrap justify-center gap-4 text-xs text-gray-500">
                <div className={`flex items-center space-x-1 ${progress > 5 ? 'text-blue-600' : ''}`}>
                  <div className={`w-2 h-2 rounded-full ${progress > 5 ? 'bg-blue-600' : 'bg-gray-300'}`}></div>
                  <span>Prepare</span>
                </div>
                <div className={`flex items-center space-x-1 ${progress > 15 ? 'text-blue-600' : ''}`}>
                  <div className={`w-2 h-2 rounded-full ${progress > 15 ? 'bg-blue-600' : 'bg-gray-300'}`}></div>
                  <span>Context</span>
                </div>
                <div className={`flex items-center space-x-1 ${progress > 30 ? 'text-purple-600' : ''}`}>
                  <div className={`w-2 h-2 rounded-full ${progress > 30 ? 'bg-purple-600' : 'bg-gray-300'}`}></div>
                  <span>Review</span>
                </div>
                <div className={`flex items-center space-x-1 ${progress > 90 ? 'text-purple-600' : ''}`}>
                  <div className={`w-2 h-2 rounded-full ${progress > 90 ? 'bg-purple-600' : 'bg-gray-300'}`}></div>
                  <span>Parse</span>
                </div>
                <div className={`flex items-center space-x-1 ${progress >= 100 ? 'text-green-600' : ''}`}>
                  <div className={`w-2 h-2 rounded-full ${progress >= 100 ? 'bg-green-600' : 'bg-gray-300'}`}></div>
                  <span>Complete</span>
                </div>
              </div>

              {/* Token counter during reviewing stage */}
              {stage === 'reviewing' && tokens !== undefined && tokens > 0 && (
                <div className="mt-4 text-xs text-gray-400 text-center">
                  <p>Processing: {tokens} tokens generated</p>
                  <p className="mt-1">This may take 30-60 seconds depending on article size</p>
                </div>
              )}

              {/* Error message for error stage */}
              {stage === 'error' && (
                <div className="mt-4 text-xs text-red-500 text-center">
                  <p>Please check the console for more details</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ReviewProgressModal
