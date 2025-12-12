import React, { useMemo } from 'react'
import { marked } from 'marked'

/**
 * Variant types for markdown rendering:
 * - 'default': Full markdown styling for methodology sections
 * - 'compact': Reduced spacing for chat messages and review panels
 * - 'inverted': White text on dark backgrounds (e.g., user chat bubbles)
 */
export type MarkdownVariant = 'default' | 'compact' | 'inverted'

interface MarkdownRendererProps {
  content: string
  variant?: MarkdownVariant
  className?: string
}

/**
 * MarkdownRenderer - Unified markdown rendering component
 * 
 * Provides consistent markdown rendering across the application:
 * - Article chat panel
 * - Reviewer chat panel
 * - Methodology sections
 * - Review modal content
 * 
 * Uses the 'marked' library with consistent options and applies
 * appropriate CSS classes based on the variant prop.
 */
const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  variant = 'default',
  className = ''
}) => {
  // Memoize the parsed HTML to avoid re-parsing on every render
  const parsedContent = useMemo(() => {
    if (!content) return ''
    
    // Configure marked options for consistent rendering
    // Note: headerIds was removed in marked v8, we use the default behavior
    marked.setOptions({
      breaks: true,        // Convert \n to <br>
      gfm: true            // GitHub Flavored Markdown
    })
    
    return marked.parse(content) as string
  }, [content])

  // Determine CSS class based on variant
  const variantClass = useMemo(() => {
    switch (variant) {
      case 'compact':
        return 'md-content md-compact'
      case 'inverted':
        return 'md-content md-compact md-inverted'
      default:
        return 'md-content'
    }
  }, [variant])

  if (!content) {
    return null
  }

  return (
    <div
      className={`${variantClass} ${className}`.trim()}
      dangerouslySetInnerHTML={{ __html: parsedContent }}
    />
  )
}

export default MarkdownRenderer
