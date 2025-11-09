import React from 'react'
import { MessageCircle } from 'lucide-react'

interface ChatFloatingButtonProps {
  onClick: () => void
  hasNewFeatureBadge?: boolean
}

const ChatFloatingButton: React.FC<ChatFloatingButtonProps> = ({
  onClick,
  hasNewFeatureBadge = false
}) => {
  return (
    <button
      onClick={onClick}
      className="fixed bottom-20 right-6 z-50 w-14 h-14 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center group"
      title="Ask questions about this article (Cmd/Ctrl+K)"
      aria-label="Open chat assistant"
    >
      <MessageCircle className="h-6 w-6" />
      {hasNewFeatureBadge && (
        <div className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full animate-pulse" />
      )}

      {/* Tooltip on hover */}
      <span className="absolute bottom-full right-0 mb-2 px-3 py-2 bg-gray-900 text-white text-sm rounded-md opacity-0 group-hover:opacity-100 transition-opacity duration-200 whitespace-nowrap pointer-events-none">
        Ask about this article
        <span className="block text-xs text-gray-400 mt-1">Cmd/Ctrl+K</span>
      </span>
    </button>
  )
}

export default ChatFloatingButton
