import { createContext, useContext } from 'react'
import { ToastType } from '../components/Toast'

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

export default ToasterContext
