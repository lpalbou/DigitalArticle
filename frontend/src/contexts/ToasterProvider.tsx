import React, { useCallback, useState } from 'react'
import Toast, { ToastType } from '../components/Toast'
import ToasterContext from './ToasterContext'

interface ToasterProviderProps {
  children: React.ReactNode
}

export const ToasterProvider: React.FC<ToasterProviderProps> = ({ children }) => {
  const [toast, setToast] = useState<{ message: string; type: ToastType; duration?: number } | null>(null)

  const showToast = useCallback((message: string, type: ToastType = 'success', duration?: number) => {
    setToast({ message, type, duration })
  }, [])

  const success = useCallback((message: string, duration?: number) => {
    showToast(message, 'success', duration)
  }, [showToast])

  const error = useCallback((message: string, duration?: number) => {
    showToast(message, 'error', duration)
  }, [showToast])

  const warning = useCallback((message: string, duration?: number) => {
    showToast(message, 'warning', duration)
  }, [showToast])

  const info = useCallback((message: string, duration?: number) => {
    showToast(message, 'info', duration)
  }, [showToast])

  return (
    <ToasterContext.Provider value={{ showToast, success, error, warning, info }}>
      {children}
      {/* Global toast - uses existing Toast component */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          duration={toast.duration}
          onClose={() => setToast(null)}
        />
      )}
    </ToasterContext.Provider>
  )
}

