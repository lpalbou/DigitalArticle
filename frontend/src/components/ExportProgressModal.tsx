import React from 'react'
import { Loader2, FileText, Download, Brain, CheckCircle, AlertCircle } from 'lucide-react'

interface ExportProgressModalProps {
  isVisible: boolean
  operationType: 'pdf' | 'semantic-analysis' | 'semantic-profile'
  progress: number  // 0-100
  stage: string
  message: string
  isCached?: boolean
}

const ExportProgressModal: React.FC<ExportProgressModalProps> = ({
  isVisible,
  operationType,
  progress,
  stage,
  message,
  isCached
}) => {
  if (!isVisible) return null

  const getStageInfo = () => {
    // Handle cache hit - instant result
    if (stage === 'cached') {
      return {
        icon: <CheckCircle className="h-8 w-8 text-green-500" />,
        title: 'Using Cached Results',
        description: message || 'Found recent extraction - returning instantly',
      }
    }

    // Handle error
    if (stage === 'error') {
      return {
        icon: <AlertCircle className="h-8 w-8 text-red-500" />,
        title: 'Export Failed',
        description: message || 'An error occurred during export.',
      }
    }

    // Handle complete
    if (stage === 'complete') {
      return {
        icon: <CheckCircle className="h-8 w-8 text-green-500" />,
        title: operationType === 'pdf' ? 'PDF Ready' : 'Graph Ready',
        description: message || 'Export completed successfully.',
      }
    }

    // PDF-specific stages
    if (operationType === 'pdf') {
      if (stage === 'regenerating_abstract') {
        return {
          icon: <FileText className="h-8 w-8 text-blue-500 animate-pulse" />,
          title: 'Regenerating Abstract',
          description: message || 'Updating abstract with latest analysis...',
        }
      }
      if (stage.startsWith('writing_')) {
        return {
          icon: <FileText className="h-8 w-8 text-purple-500 animate-pulse" />,
          title: 'Generating Article',
          description: message || 'AI is writing scientific article sections...',
        }
      }
      if (stage === 'creating_pdf') {
        return {
          icon: <Download className="h-8 w-8 text-purple-500" />,
          title: 'Creating PDF',
          description: message || 'Formatting and generating PDF document...',
        }
      }
    }

    // Semantic extraction stages
    if (operationType.startsWith('semantic-')) {
      if (stage === 'extracting') {
        return {
          icon: <Brain className="h-8 w-8 text-purple-500 animate-pulse" />,
          title: operationType === 'semantic-analysis' ? 'Analyzing Article' : 'Extracting Profile',
          description: message || 'Extracting semantic knowledge...',
        }
      }
      if (stage === 'building_graph') {
        return {
          icon: <Brain className="h-8 w-8 text-purple-500" />,
          title: 'Building Knowledge Graph',
          description: message || 'Creating semantic relationships...',
        }
      }
    }

    // Default loading state
    return {
      icon: <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />,
      title: 'Loading',
      description: message || 'Loading notebook...',
    }
  }

  const stageInfo = getStageInfo()

  // Determine stage indicators based on operation type
  const getStageIndicators = () => {
    // If cached, show simplified progress (no fake intermediate steps)
    if (isCached || stage === 'cached') {
      return [
        { label: 'Cached', threshold: 100 },
      ]
    }

    if (operationType === 'pdf') {
      return [
        { label: 'Load', threshold: 5 },
        { label: 'Abstract', threshold: 15 },
        { label: 'Write', threshold: 30 },
        { label: 'Create PDF', threshold: 95 },
        { label: 'Complete', threshold: 100 },
      ]
    } else if (operationType === 'semantic-analysis') {
      return [
        { label: 'Load', threshold: 5 },
        { label: 'Extract', threshold: 20 },
        { label: 'Graph', threshold: 90 },
        { label: 'Complete', threshold: 100 },
      ]
    } else {
      // semantic-profile (faster, no LLM)
      return [
        { label: 'Load', threshold: 5 },
        { label: 'Extract', threshold: 50 },
        { label: 'Complete', threshold: 100 },
      ]
    }
  }

  const indicators = getStageIndicators()

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
                {stage === 'complete' || stage === 'cached' ? stageInfo.icon :
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
                      className={`h-2 rounded-full transition-all duration-500 ease-out ${
                        stage === 'cached' ? 'bg-green-600' : 'bg-blue-600'
                      }`}
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
                {indicators.map((indicator, index) => (
                  <div
                    key={index}
                    className={`flex items-center space-x-1 ${
                      progress >= indicator.threshold ? 'text-blue-600' : ''
                    }`}
                  >
                    <div
                      className={`w-2 h-2 rounded-full ${
                        progress >= indicator.threshold ? 'bg-blue-600' : 'bg-gray-300'
                      }`}
                    ></div>
                    <span>{indicator.label}</span>
                  </div>
                ))}
              </div>

              {/* Cache indicator */}
              {stage === 'cached' && (
                <div className="mt-4 text-xs text-green-600 text-center">
                  <p>✓ Using previously extracted results</p>
                  <p className="mt-1">Cache automatically updates when cells execute</p>
                </div>
              )}

              {/* Time estimate for LLM operations */}
              {stage === 'extracting' && operationType === 'semantic-analysis' && (
                <div className="mt-4 text-xs text-gray-400 text-center">
                  <p>LLM-based extraction in progress</p>
                  <p className="mt-1">This may take a few minutes depending on notebook size</p>
                </div>
              )}

              {/* Error message */}
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

export default ExportProgressModal
