import React, { useState, useEffect, useRef } from 'react'
import { X, Send, Loader2, Copy, Check, Trash2, MessageCircle } from 'lucide-react'
import { Notebook, ChatMessage } from '../types'
import { chatAPI } from '../services/api'

interface ArticleChatPanelProps {
  isOpen: boolean
  onClose: () => void
  notebookId: string
  notebook: Notebook | null
}

const ArticleChatPanel: React.FC<ArticleChatPanelProps> = ({
  isOpen,
  onClose,
  notebookId,
  notebook
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Load conversation from localStorage on mount
  useEffect(() => {
    if (notebookId) {
      const key = `chat_history_${notebookId}`
      const saved = localStorage.getItem(key)
      if (saved) {
        try {
          const parsed = JSON.parse(saved)
          setMessages(parsed)
        } catch (e) {
          console.error('Failed to load chat history:', e)
        }
      }
    }
  }, [notebookId])

  // Save conversation to localStorage whenever messages change
  useEffect(() => {
    if (notebookId && messages.length > 0) {
      const key = `chat_history_${notebookId}`
      localStorage.setItem(key, JSON.stringify(messages))
    }
  }, [notebookId, messages])

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus()
    }
  }, [isOpen])

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading || !notebook) return

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date().toISOString()
    }

    // Add user message immediately (optimistic UI)
    setMessages(prev => [...prev, userMessage])
    setInputValue('')

    // Add loading message
    const loadingMessage: ChatMessage = {
      id: `loading-${Date.now()}`,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      loading: true
    }
    setMessages(prev => [...prev, loadingMessage])
    setIsLoading(true)

    try {
      // Send to backend
      const response = await chatAPI.sendMessage({
        notebook_id: notebookId,
        message: userMessage.content,
        conversation_history: messages.filter(m => !m.loading)
      })

      // Replace loading message with actual response
      setMessages(prev => prev.map(msg =>
        msg.id === loadingMessage.id
          ? {
              id: Date.now().toString(),
              role: 'assistant' as const,
              content: response.message,
              timestamp: response.timestamp
            }
          : msg
      ))
    } catch (error) {
      console.error('Failed to send message:', error)
      // Replace loading message with error
      setMessages(prev => prev.map(msg =>
        msg.id === loadingMessage.id
          ? {
              id: Date.now().toString(),
              role: 'assistant' as const,
              content: '❌ Sorry, I encountered an error. Please try again.',
              timestamp: new Date().toISOString()
            }
          : msg
      ))
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const clearConversation = () => {
    if (confirm('Clear all chat history? This cannot be undone.')) {
      setMessages([])
      if (notebookId) {
        localStorage.removeItem(`chat_history_${notebookId}`)
      }
    }
  }

  const copyMessage = async (content: string, id: string) => {
    try {
      await navigator.clipboard.writeText(content)
      setCopiedId(id)
      setTimeout(() => setCopiedId(null), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop overlay */}
      <div
        className="fixed inset-0 bg-black bg-opacity-30 z-50 transition-opacity duration-300"
        onClick={onClose}
      />

      {/* Chat panel */}
      <div className="fixed right-0 top-0 bottom-0 w-full sm:w-96 bg-white shadow-2xl z-50 flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="bg-blue-600 text-white p-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <MessageCircle className="h-5 w-5" />
            <div>
              <h2 className="font-semibold">Ask About This Article</h2>
              <p className="text-xs text-blue-100">Read-only assistant</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {messages.length > 0 && (
              <button
                onClick={clearConversation}
                className="p-1 hover:bg-blue-700 rounded transition-colors"
                title="Clear conversation"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1 hover:bg-blue-700 rounded transition-colors"
              title="Close chat"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center py-8">
              <MessageCircle className="h-12 w-12 text-gray-300 mx-auto mb-3" />
              <h3 className="text-lg font-medium text-gray-700 mb-2">
                Start a conversation
              </h3>
              <p className="text-sm text-gray-500 mb-4">
                Ask me anything about this article!
              </p>
              <div className="space-y-2 text-left max-w-sm mx-auto">
                <button
                  onClick={() => setInputValue('What is this article about?')}
                  className="w-full text-left px-3 py-2 text-sm bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  💡 What is this article about?
                </button>
                <button
                  onClick={() => setInputValue('What datasets are used?')}
                  className="w-full text-left px-3 py-2 text-sm bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  📊 What datasets are used?
                </button>
                <button
                  onClick={() => setInputValue('Summarize the findings')}
                  className="w-full text-left px-3 py-2 text-sm bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  ✨ Summarize the findings
                </button>
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-lg px-4 py-2 ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  {message.loading ? (
                    <div className="flex items-center space-x-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span className="text-sm text-gray-600">Thinking...</span>
                    </div>
                  ) : (
                    <>
                      <div className="whitespace-pre-wrap text-sm leading-relaxed">
                        {message.content}
                      </div>
                      {message.role === 'assistant' && (
                        <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-200">
                          <span className="text-xs text-gray-500">
                            {new Date(message.timestamp).toLocaleTimeString([], {
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </span>
                          <button
                            onClick={() => copyMessage(message.content, message.id)}
                            className="text-gray-500 hover:text-gray-700 transition-colors"
                            title="Copy message"
                          >
                            {copiedId === message.id ? (
                              <Check className="h-3 w-3 text-green-500" />
                            ) : (
                              <Copy className="h-3 w-3" />
                            )}
                          </button>
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div className="border-t border-gray-200 p-4 bg-gray-50">
          <div className="flex space-x-2">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your question... (Shift+Enter for new line)"
              className="flex-1 resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows={2}
              disabled={isLoading}
            />
            <button
              onClick={handleSend}
              disabled={!inputValue.trim() || isLoading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
              title="Send message (Enter)"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            This assistant has read-only access to your article
          </p>
        </div>
      </div>

      {/* Add slide-in animation to global CSS */}
      <style>{`
        @keyframes slide-in-right {
          from {
            transform: translateX(100%);
          }
          to {
            transform: translateX(0);
          }
        }
        .animate-slide-in-right {
          animation: slide-in-right 0.3s ease-out;
        }
      `}</style>
    </>
  )
}

export default ArticleChatPanel
