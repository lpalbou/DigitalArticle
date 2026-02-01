import React, { useEffect, useMemo, useRef, useState } from 'react'
import { X, MessageSquare } from 'lucide-react'

interface GuidedRerunModalProps {
  isOpen: boolean
  isExecuting?: boolean
  maxLength?: number
  title?: string
  onClose: () => void
  onConfirm: (comment: string) => void
}

/**
 * GuidedRerunModal
 *
 * Collect a short "rerun comment" that is injected into LLM regeneration.
 * Goal: enable partial rewrites ("keep what you did, but change X") without rewriting the whole prompt.
 */
const GuidedRerunModal: React.FC<GuidedRerunModalProps> = ({
  isOpen,
  isExecuting = false,
  maxLength = 800,
  title = 'Guided rerun (keep context)',
  onClose,
  onConfirm
}) => {
  const [comment, setComment] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const remaining = useMemo(() => Math.max(0, maxLength - comment.length), [comment.length, maxLength])

  useEffect(() => {
    if (!isOpen) return
    setComment('')
    // Focus after open
    setTimeout(() => textareaRef.current?.focus(), 0)
  }, [isOpen])

  const handleConfirm = () => {
    const trimmed = comment.trim()
    if (!trimmed) return
    onConfirm(trimmed)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40"
        onClick={() => !isExecuting && onClose()}
      />

      {/* Modal */}
      <div className="relative w-full max-w-xl bg-white rounded-xl shadow-xl border border-gray-200 overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-blue-600" />
            <h3 className="text-sm font-semibold text-gray-800">{title}</h3>
          </div>
          <button
            onClick={onClose}
            disabled={isExecuting}
            className="p-1 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700 disabled:opacity-50"
            title="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="px-5 py-4 space-y-3">
          <p className="text-sm text-gray-600">
            Write a short delta request (e.g., “use a different method”, “change colors”, “add labels”, “use log scale”).
            This will <strong>regenerate</strong> the cell while <strong>invalidating all downstream cells</strong>.
          </p>

          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800">
            <strong>Reminder:</strong> Don’t put secrets here (API keys, tokens, credentials).
          </div>

          <textarea
            ref={textareaRef}
            value={comment}
            onChange={(e) => setComment(e.target.value.slice(0, maxLength))}
            placeholder="Example: Keep the same plot, but use a colorblind-friendly palette and add axis labels."
            className="w-full min-h-[120px] resize-y rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={isExecuting}
          />

          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>{remaining} characters remaining</span>
            <span className="text-gray-400">Max {maxLength}</span>
          </div>
        </div>

        <div className="px-5 py-4 border-t border-gray-200 bg-white flex items-center justify-end gap-2">
          <button
            onClick={onClose}
            disabled={isExecuting}
            className="px-3 py-2 text-sm rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={isExecuting || !comment.trim()}
            className="px-3 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Regenerate with comment
          </button>
        </div>
      </div>
    </div>
  )
}

export default GuidedRerunModal

