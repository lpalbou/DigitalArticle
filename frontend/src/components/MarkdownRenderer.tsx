import React, { useMemo, useRef, useEffect, useCallback } from 'react'
import { marked } from 'marked'
import hljs from 'highlight.js/lib/core'
// Import a dark theme that works well with our dark code blocks
import 'highlight.js/styles/github-dark.css'
// Import common languages for code highlighting
import python from 'highlight.js/lib/languages/python'
import javascript from 'highlight.js/lib/languages/javascript'
import typescript from 'highlight.js/lib/languages/typescript'
import bash from 'highlight.js/lib/languages/bash'
import json from 'highlight.js/lib/languages/json'
import sql from 'highlight.js/lib/languages/sql'
import r from 'highlight.js/lib/languages/r'
import yaml from 'highlight.js/lib/languages/yaml'
import xml from 'highlight.js/lib/languages/xml'
import css from 'highlight.js/lib/languages/css'

// Register languages
hljs.registerLanguage('python', python)
hljs.registerLanguage('py', python)
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('js', javascript)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('ts', typescript)
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('shell', bash)
hljs.registerLanguage('sh', bash)
hljs.registerLanguage('json', json)
hljs.registerLanguage('sql', sql)
hljs.registerLanguage('r', r)
hljs.registerLanguage('yaml', yaml)
hljs.registerLanguage('yml', yaml)
hljs.registerLanguage('xml', xml)
hljs.registerLanguage('html', xml)
hljs.registerLanguage('css', css)

// Configure marked globally once at module load time
// This avoids race conditions from calling setOptions on every render
marked.setOptions({
  breaks: true,        // Convert \n to <br>
  gfm: true            // GitHub Flavored Markdown
})

// Helper to escape HTML in code
function escapeHtml(text: string): string {
  if (!text || typeof text !== 'string') return ''
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

// Custom renderer for syntax highlighting
// Note: marked v16 passes a token object, not separate parameters
const renderer = new marked.Renderer()
renderer.code = function({ text, lang }: { text: string; lang?: string }) {
  const language = lang || ''
  const code = text || ''
  let highlighted: string
  
  if (language && hljs.getLanguage(language)) {
    try {
      highlighted = hljs.highlight(code, { language }).value
    } catch {
      highlighted = escapeHtml(code)
    }
  } else if (code) {
    // Auto-detect language
    try {
      highlighted = hljs.highlightAuto(code).value
    } catch {
      highlighted = escapeHtml(code)
    }
  } else {
    highlighted = ''
  }
  
  return `<pre><code class="hljs language-${language}">${highlighted}</code></pre>`
}

marked.use({ renderer })

// Copy icon SVG (matches lucide-react Copy icon)
const COPY_ICON_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>`
const CHECK_ICON_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`

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
 * Features:
 * - Uses the 'marked' library with consistent options
 * - Syntax highlighting with highlight.js
 * - Applies appropriate CSS classes based on the variant prop
 * - Adds copy buttons to code blocks
 */
const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  variant = 'default',
  className = ''
}) => {
  const containerRef = useRef<HTMLDivElement>(null)

  // Memoize the parsed HTML to avoid re-parsing on every render
  const parsedContent = useMemo(() => {
    if (!content) return ''
    return marked.parse(content) as string
  }, [content])

  // Copy code to clipboard
  const copyCode = useCallback(async (code: string, button: HTMLButtonElement) => {
    try {
      await navigator.clipboard.writeText(code)
      // Visual feedback
      button.innerHTML = CHECK_ICON_SVG
      button.classList.add('md-copy-success')
      setTimeout(() => {
        button.innerHTML = COPY_ICON_SVG
        button.classList.remove('md-copy-success')
      }, 2000)
    } catch (err) {
      console.error('Failed to copy code:', err)
      button.textContent = '✗'
      setTimeout(() => {
        button.innerHTML = COPY_ICON_SVG
      }, 2000)
    }
  }, [])

  // Add copy buttons to code blocks after render
  useEffect(() => {
    if (!containerRef.current) return

    // Find all pre > code blocks (fenced code blocks)
    const codeBlocks = containerRef.current.querySelectorAll('pre')
    
    codeBlocks.forEach((pre) => {
      // Skip if already has a copy button
      if (pre.querySelector('.md-code-copy-btn')) return
      
      // Create wrapper for positioning
      const wrapper = document.createElement('div')
      wrapper.className = 'md-code-block-wrapper'
      
      // Create copy button with icon
      const copyBtn = document.createElement('button')
      copyBtn.className = 'md-code-copy-btn'
      copyBtn.innerHTML = COPY_ICON_SVG
      copyBtn.title = 'Copy code'
      
      // Get the code content
      const codeElement = pre.querySelector('code')
      const codeText = codeElement?.textContent || pre.textContent || ''
      
      // Add click handler
      copyBtn.addEventListener('click', (e) => {
        e.preventDefault()
        e.stopPropagation()
        copyCode(codeText, copyBtn)
      })
      
      // Wrap the pre element
      pre.parentNode?.insertBefore(wrapper, pre)
      wrapper.appendChild(pre)
      wrapper.appendChild(copyBtn)
    })

    const container = containerRef.current
    if (!container) return

    // Cleanup function to remove event listeners
    return () => {
      const buttons = container.querySelectorAll('.md-code-copy-btn')
      buttons.forEach(btn => {
        btn.replaceWith(btn.cloneNode(true))
      })
    }
  }, [parsedContent, copyCode])

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
      ref={containerRef}
      className={`${variantClass} ${className}`.trim()}
      dangerouslySetInnerHTML={{ __html: parsedContent }}
    />
  )
}

export default MarkdownRenderer
