import React from 'react'
import Editor from '@monaco-editor/react'

interface CodeDisplayProps {
  code: string
  language?: string
  readOnly?: boolean
  height?: string
  theme?: string
}

const CodeDisplay: React.FC<CodeDisplayProps> = ({
  code,
  language = 'python',
  readOnly = true,
  height = '200px',
  theme = 'vs-dark'
}) => {
  // Calculate height based on content if height is 'auto'
  const calculatedHeight = height === 'auto' 
    ? `${Math.max(100, Math.min(400, (code.split('\n').length * 20) + 40))}px`
    : height

  return (
    <div className="rounded-md overflow-hidden">
      <Editor
        height={calculatedHeight}
        language={language}
        value={code}
        theme={theme}
        options={{
          readOnly,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          fontSize: 13,
          lineNumbers: 'on',
          glyphMargin: false,
          folding: false,
          lineDecorationsWidth: 0,
          lineNumbersMinChars: 3,
          renderLineHighlight: 'none',
          scrollbar: {
            vertical: 'auto',
            horizontal: 'auto',
            verticalScrollbarSize: 8,
            horizontalScrollbarSize: 8
          },
          wordWrap: 'on',
          automaticLayout: true
        }}
        loading={
          <div className="flex items-center justify-center h-full bg-gray-900 text-gray-300">
            <div className="animate-spin h-4 w-4 border-2 border-gray-300 border-t-transparent rounded-full mr-2" />
            Loading editor...
          </div>
        }
      />
    </div>
  )
}

export default CodeDisplay
