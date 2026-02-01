import React from 'react'
import { AlertTriangle, X } from 'lucide-react'

interface DeleteCellConfirmModalProps {
  isOpen: boolean
  isDeleting?: boolean
  onClose: () => void
  onConfirm: () => void
}

/**
 * Confirmation modal for destructive cell deletion.
 *
 * Notes:
 * - Deleting a cell invalidates downstream cells and removes persisted provenance for that cell.
 * - This is intentionally explicit to preserve user trust.
 */
const DeleteCellConfirmModal: React.FC<DeleteCellConfirmModalProps> = ({
  isOpen,
  isDeleting = false,
  onClose,
  onConfirm
}) => {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40"
        onClick={() => !isDeleting && onClose()}
      />

      <div className="relative w-full max-w-md bg-white rounded-xl shadow-xl border border-gray-200 overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-600" />
            <h3 className="text-sm font-semibold text-gray-800">Delete cell</h3>
          </div>
          <button
            onClick={onClose}
            disabled={isDeleting}
            className="p-1 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700 disabled:opacity-50"
            title="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="px-5 py-4 space-y-2">
          <p className="text-sm text-gray-700">
            This will permanently delete the cell.
          </p>
          <p className="text-xs text-gray-500">
            Downstream cells will be invalidated and may need to be re-executed.
          </p>
        </div>

        <div className="px-5 py-4 border-t border-gray-200 bg-white flex items-center justify-end gap-2">
          <button
            onClick={onClose}
            disabled={isDeleting}
            className="px-3 py-2 text-sm rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isDeleting}
            className="px-3 py-2 text-sm rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isDeleting ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default DeleteCellConfirmModal

