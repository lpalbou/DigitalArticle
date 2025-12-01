import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import Toast, { ToastType } from '../components/Toast'

interface ToasterContextValue {
  showToast: (message: string, type?: ToastType, duration?: number) => void
  success: (message: string, duration?: number) => void
  error: (message: string, duration?: number) => void
  warning: (message: string, duration?: number) => void
  info: (message: string, duration?: number) => void
}

const ToasterContext = createContext<ToasterContextValue | undefined>(undefined)

export const useToaster = (): ToasterContextValue => {
  const context = useContext(ToasterContext)
  if (!context) {
    throw new Error('useToaster must be used within a ToasterProvider')
  }
  return context
}

interface ToasterProviderProps {
  children: ReactNode
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

export default ToasterContext
