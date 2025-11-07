import React from 'react'
import { Loader2, Brain, Network, CheckCircle } from 'lucide-react'

interface SemanticExtractionModalProps {
  isVisible: boolean
  stage: 'analyzing' | 'extracting' | 'building_graph' | 'complete'
  graphType: 'analysis' | 'profile'
}

const SemanticExtractionModal: React.FC<SemanticExtractionModalProps> = ({
  isVisible,
  stage,
  graphType
}) => {
  if (!isVisible) return null

  const getStageInfo = () => {
    const graphLabel = graphType === 'analysis' ? 'Analysis Flow' : 'Profile'

    switch (stage) {
      case 'analyzing':
        return {
          icon: <Brain className="h-8 w-8 text-blue-500" />,
          title: 'Analyzing Notebook',
          description: `Reading cells and preparing context for ${graphLabel} extraction...`,
          progress: 10
        }
      case 'extracting':
        return {
          icon: <Brain className="h-8 w-8 text-purple-500 animate-pulse" />,
          title: 'Extracting Semantics with LLM',
          description: `AI is analyzing ${graphType === 'analysis' ? 'data assets, transformations, and outcomes' : 'skills, interests, and methodologies'}...`,
          progress: 50
        }
      case 'building_graph':
        return {
          icon: <Network className="h-8 w-8 text-purple-500" />,
          title: 'Building Knowledge Graph',
          description: 'Creating semantic relationships and provenance links...',
          progress: 85
        }
      case 'complete':
        return {
          icon: <CheckCircle className="h-8 w-8 text-green-500" />,
          title: 'Knowledge Graph Ready',
          description: `${graphLabel} knowledge graph has been generated successfully.`,
          progress: 100
        }
      default:
        return {
          icon: <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />,
          title: 'Processing',
          description: 'Preparing semantic extraction...',
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
              <div className="flex flex-wrap justify-center gap-4 text-xs text-gray-500">
                <div className={`flex items-center space-x-1 ${stageInfo.progress > 10 ? 'text-blue-600' : ''}`}>
                  <div className={`w-2 h-2 rounded-full ${stageInfo.progress > 10 ? 'bg-blue-600' : 'bg-gray-300'}`}></div>
                  <span>Analyze</span>
                </div>
                <div className={`flex items-center space-x-1 ${stageInfo.progress > 50 ? 'text-purple-600' : ''}`}>
                  <div className={`w-2 h-2 rounded-full ${stageInfo.progress > 50 ? 'bg-purple-600' : 'bg-gray-300'}`}></div>
                  <span>Extract</span>
                </div>
                <div className={`flex items-center space-x-1 ${stageInfo.progress > 85 ? 'text-purple-600' : ''}`}>
                  <div className={`w-2 h-2 rounded-full ${stageInfo.progress > 85 ? 'bg-purple-600' : 'bg-gray-300'}`}></div>
                  <span>Build Graph</span>
                </div>
                <div className={`flex items-center space-x-1 ${stageInfo.progress > 95 ? 'text-green-600' : ''}`}>
                  <div className={`w-2 h-2 rounded-full ${stageInfo.progress > 95 ? 'bg-green-600' : 'bg-gray-300'}`}></div>
                  <span>Complete</span>
                </div>
              </div>

              {/* Technical details for nerds */}
              {stage === 'extracting' && (
                <div className="mt-4 text-xs text-gray-400 text-center">
                  <p>Using LLM to extract structured semantic information...</p>
                  <p className="mt-1">This may take 30-60 seconds depending on notebook size</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SemanticExtractionModal
