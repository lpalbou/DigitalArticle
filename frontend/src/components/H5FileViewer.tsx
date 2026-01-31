import React, { useState, useMemo } from 'react'
import { ChevronDown, ChevronRight, FileText, Folder } from 'lucide-react'

interface H5FileViewerProps {
  fileInfo: {
    name: string
    preview: any
    is_h5_file?: boolean
  }
}

interface TreeNode {
  name: string
  type: 'dataset' | 'group' | 'folder'
  children?: TreeNode[]
  data?: any
  expanded?: boolean
}

const H5FileViewer: React.FC<H5FileViewerProps> = ({ fileInfo }) => {
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set())
  const [selectedNode, setSelectedNode] = useState<string | null>(null)

  // Parse H5 structure into tree format
  const treeData = useMemo(() => {
    if (!fileInfo.preview || fileInfo.preview.error) {
      return null
    }

    const preview = fileInfo.preview

    // Handle AnnData files
    if (preview.file_type === 'anndata') {
      return {
        name: fileInfo.name,
        type: 'folder' as const,
        children: [
          {
            name: 'Observations (cells)',
            type: 'group' as const,
            data: {
              count: preview.n_obs,
              columns: preview.obs_keys,
              preview: preview.obs_preview
            }
          },
          {
            name: 'Variables (genes)',
            type: 'group' as const,
            data: {
              count: preview.n_vars,
              columns: preview.var_keys,
              preview: preview.var_preview
            }
          },
          {
            name: 'Expression Matrix',
            type: 'dataset' as const,
            data: {
              shape: [preview.n_obs, preview.n_vars],
              preview: preview.expression_preview
            }
          },
          ...(preview.obsm_keys?.map((key: string) => ({
            name: `Embedding: ${key}`,
            type: 'dataset' as const,
            data: preview[`embedding_${key}`]
          })) || []),
          ...(preview.layers?.map((layer: string) => ({
            name: `Layer: ${layer}`,
            type: 'dataset' as const,
            data: { name: layer }
          })) || [])
        ]
      }
    }

    // Handle standard HDF5 files
    if (preview.file_type === 'hdf5' && preview.structure) {
      const buildTree = (structure: any, path = ''): TreeNode[] => {
        return Object.entries(structure).map(([name, info]: [string, any]) => {
          const fullPath = path ? `${path}/${name}` : name
          
          if (info.type === 'group') {
            return {
              name,
              type: 'group',
              children: info.children ? buildTree(info.children, fullPath) : [],
              data: info
            }
          } else {
            return {
              name,
              type: 'dataset',
              data: {
                ...info,
                preview: preview.preview_data?.[fullPath]
              }
            }
          }
        })
      }

      return {
        name: fileInfo.name,
        type: 'folder' as const,
        children: buildTree(preview.structure)
      }
    }

    return null
  }, [fileInfo])

  const toggleNode = (nodePath: string) => {
    const newExpanded = new Set(expandedNodes)
    if (newExpanded.has(nodePath)) {
      newExpanded.delete(nodePath)
    } else {
      newExpanded.add(nodePath)
    }
    setExpandedNodes(newExpanded)
  }

  const renderTreeNode = (node: TreeNode, path = '', depth = 0) => {
    const nodePath = path ? `${path}/${node.name}` : node.name
    const isExpanded = expandedNodes.has(nodePath)
    const isSelected = selectedNode === nodePath
    const hasChildren = node.children && node.children.length > 0

    return (
      <div key={nodePath} className="select-none">
        <div
          className={`flex items-center py-1 px-2 cursor-pointer hover:bg-gray-100 rounded ${
            isSelected ? 'bg-blue-100 border-l-2 border-blue-500' : ''
          }`}
          style={{ paddingLeft: `${depth * 16 + 8}px` }}
          onClick={() => {
            if (hasChildren) {
              toggleNode(nodePath)
            }
            setSelectedNode(nodePath)
          }}
        >
          {hasChildren ? (
            isExpanded ? (
              <ChevronDown className="w-4 h-4 mr-1 text-gray-500" />
            ) : (
              <ChevronRight className="w-4 h-4 mr-1 text-gray-500" />
            )
          ) : (
            <div className="w-4 h-4 mr-1" />
          )}
          
          {node.type === 'folder' ? (
            <Folder className="w-4 h-4 mr-2 text-blue-500" />
          ) : node.type === 'group' ? (
            <Folder className="w-4 h-4 mr-2 text-green-500" />
          ) : (
            <FileText className="w-4 h-4 mr-2 text-gray-500" />
          )}
          
          <span className="text-sm font-medium">{node.name}</span>
          
          {node.data && (
            <div className="ml-2 flex items-center space-x-2 text-xs">
              {node.data.shape && (
                <span className="px-1.5 py-0.5 bg-blue-100 text-blue-800 rounded">
                  {node.data.shape.join(' × ')}
                </span>
              )}
              {node.data.count && (
                <span className="px-1.5 py-0.5 bg-green-100 text-green-800 rounded">
                  {node.data.count.toLocaleString()} items
                </span>
              )}
              {node.data.dtype && (
                <span className="px-1.5 py-0.5 bg-gray-100 text-gray-700 rounded font-mono text-xs">
                  {node.data.dtype}
                </span>
              )}
              {node.data.size && (
                <span className="text-gray-500">
                  {node.data.size.toLocaleString()} elements
                </span>
              )}
            </div>
          )}
        </div>
        
        {hasChildren && isExpanded && (
          <div>
            {node.children!.map(child => renderTreeNode(child, nodePath, depth + 1))}
          </div>
        )}
      </div>
    )
  }

  const renderDataPreview = () => {
    if (!selectedNode || !treeData) return null

    const findNodeByPath = (node: TreeNode, targetPath: string, currentPath = ''): TreeNode | null => {
      const nodePath = currentPath ? `${currentPath}/${node.name}` : node.name
      
      if (nodePath === targetPath) {
        return node
      }
      
      if (node.children) {
        for (const child of node.children) {
          const found = findNodeByPath(child, targetPath, nodePath)
          if (found) return found
        }
      }
      
      return null
    }

    const selectedNodeData = findNodeByPath(treeData, selectedNode)
    if (!selectedNodeData?.data) return null

    const data = selectedNodeData.data

    return (
      <div className="mt-4 p-4 bg-gray-50 rounded-lg">
        <div className="flex items-center justify-between mb-4">
          <h4 className="font-semibold text-lg">{selectedNodeData.name}</h4>
          <span className="text-xs text-gray-500 bg-white px-2 py-1 rounded">
            {selectedNodeData.type}
          </span>
        </div>
        
        {/* Basic info cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
          {data.shape && (
            <div className="bg-white p-3 rounded-lg border">
              <div className="text-xs text-gray-500 uppercase tracking-wide">Shape</div>
              <div className="text-sm font-mono font-medium">[{data.shape.join(' × ')}]</div>
            </div>
          )}
          {data.dtype && (
            <div className="bg-white p-3 rounded-lg border">
              <div className="text-xs text-gray-500 uppercase tracking-wide">Data Type</div>
              <div className="text-sm font-mono font-medium">{data.dtype}</div>
            </div>
          )}
          {data.count && (
            <div className="bg-white p-3 rounded-lg border">
              <div className="text-xs text-gray-500 uppercase tracking-wide">Count</div>
              <div className="text-sm font-medium">{data.count.toLocaleString()}</div>
            </div>
          )}
          {data.size && (
            <div className="bg-white p-3 rounded-lg border">
              <div className="text-xs text-gray-500 uppercase tracking-wide">Elements</div>
              <div className="text-sm font-medium">{data.size.toLocaleString()}</div>
            </div>
          )}
          {data.compression && (
            <div className="bg-white p-3 rounded-lg border">
              <div className="text-xs text-gray-500 uppercase tracking-wide">Compression</div>
              <div className="text-sm font-medium">{data.compression}</div>
            </div>
          )}
          {data.chunks && (
            <div className="bg-white p-3 rounded-lg border">
              <div className="text-xs text-gray-500 uppercase tracking-wide">Chunks</div>
              <div className="text-sm font-mono font-medium">[{data.chunks.join(' × ')}]</div>
            </div>
          )}
        </div>

        {/* Columns for observations/variables */}
        {data.columns && (
          <div className="mb-4">
            <span className="font-medium text-gray-700">Columns:</span>
            <div className="mt-2 flex flex-wrap gap-1">
              {data.columns.slice(0, 10).map((col: string, idx: number) => (
                <span key={idx} className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                  {col}
                </span>
              ))}
              {data.columns.length > 10 && (
                <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded">
                  +{data.columns.length - 10} more
                </span>
              )}
            </div>
          </div>
        )}

        {/* Sample data preview */}
        {data.preview?.sample_data && (
          <div className="mb-4">
            <h5 className="font-medium text-gray-700 mb-2">Sample Data</h5>
            <div className="bg-white rounded-lg border overflow-hidden">
              <div className="overflow-x-auto max-h-64">
                <table className="min-w-full text-xs">
                  <tbody>
                    {Array.isArray(data.preview.sample_data) ? (
                      // Handle 2D array data
                      data.preview.sample_data.slice(0, 10).map((row: any, rowIdx: number) => (
                        <tr key={rowIdx} className={`${rowIdx % 2 === 0 ? 'bg-gray-50' : 'bg-white'} hover:bg-blue-50`}>
                          <td className="px-3 py-2 text-gray-500 font-medium border-r">
                            {rowIdx}
                          </td>
                          {Array.isArray(row) ? (
                            row.slice(0, 10).map((cell, cellIdx) => (
                              <td key={cellIdx} className="px-3 py-2 border-r border-gray-100 font-mono">
                                {typeof cell === 'number' ? 
                                  (cell % 1 === 0 ? cell.toLocaleString() : cell.toFixed(3)) : 
                                  String(cell).length > 20 ? String(cell).substring(0, 20) + '...' : String(cell)
                                }
                              </td>
                            ))
                          ) : (
                            <td className="px-3 py-2 font-mono">
                              {typeof row === 'number' ? 
                                (row % 1 === 0 ? row.toLocaleString() : (row as number).toFixed(3)) : 
                                String(row).length > 50 ? String(row).substring(0, 50) + '...' : String(row)
                              }
                            </td>
                          )}
                          {Array.isArray(row) && row.length > 10 && (
                            <td className="px-3 py-2 text-gray-400 italic">
                              ... +{row.length - 10} more columns
                            </td>
                          )}
                        </tr>
                      ))
                    ) : (
                      // Handle object data (like obs_preview)
                      Object.entries(data.preview.sample_data).slice(0, 10).map(([key, value], idx) => (
                        <tr key={key} className={`${idx % 2 === 0 ? 'bg-gray-50' : 'bg-white'} hover:bg-blue-50`}>
                          <td className="px-3 py-2 font-medium text-blue-700 border-r">{key}</td>
                          <td className="px-3 py-2 font-mono">
                            {String(value).length > 100 ? String(value).substring(0, 100) + '...' : String(value)}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
              {Array.isArray(data.preview.sample_data) && data.preview.sample_data.length > 10 && (
                <div className="px-3 py-2 bg-gray-100 text-xs text-gray-600 border-t">
                  Showing first 10 of {data.preview.sample_data.length} rows
                </div>
              )}
            </div>
          </div>
        )}

        {/* Attributes */}
        {data.attributes && Object.keys(data.attributes).length > 0 && (
          <div>
            <h5 className="font-medium text-gray-700 mb-2">Attributes</h5>
            <div className="bg-white rounded-lg border overflow-hidden">
              <div className="divide-y divide-gray-100">
                {Object.entries(data.attributes).slice(0, 10).map(([key, value], idx) => (
                  <div key={key} className={`px-3 py-2 ${idx % 2 === 0 ? 'bg-gray-50' : 'bg-white'}`}>
                    <div className="flex items-start justify-between">
                      <span className="font-medium text-blue-700 text-sm">{key}</span>
                      <span className="ml-3 text-xs font-mono text-gray-600 max-w-md truncate">
                        {typeof value === 'object' ? 
                          JSON.stringify(value).length > 100 ? 
                            JSON.stringify(value).substring(0, 100) + '...' : 
                            JSON.stringify(value) : 
                          String(value).length > 100 ? 
                            String(value).substring(0, 100) + '...' : 
                            String(value)
                        }
                      </span>
                    </div>
                  </div>
                ))}
              </div>
              {Object.keys(data.attributes).length > 10 && (
                <div className="px-3 py-2 bg-gray-100 text-xs text-gray-600 border-t">
                  Showing first 10 of {Object.keys(data.attributes).length} attributes
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    )
  }

  if (!fileInfo.is_h5_file || !fileInfo.preview) {
    return (
      <div className="p-4 text-center text-gray-500">
        <FileText className="w-12 h-12 mx-auto mb-2 text-gray-400" />
        <p>This file is not an H5 file or preview is not available.</p>
      </div>
    )
  }

  if (fileInfo.preview.error) {
    return (
      <div className="p-4 text-center text-red-500">
        <FileText className="w-12 h-12 mx-auto mb-2 text-red-400" />
        <p>Error loading H5 file:</p>
        <p className="text-sm mt-1">{fileInfo.preview.error}</p>
      </div>
    )
  }

  if (!treeData) {
    return (
      <div className="p-4 text-center text-gray-500">
        <FileText className="w-12 h-12 mx-auto mb-2 text-gray-400" />
        <p>Unable to parse H5 file structure.</p>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* File info header */}
      <div className="p-4 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-lg text-gray-900">{fileInfo.name}</h3>
            <div className="flex items-center space-x-4 text-sm text-gray-600 mt-2">
              {fileInfo.preview.file_type === 'anndata' && (
                <>
                  <span className="flex items-center">
                    <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                    AnnData Format
                  </span>
                  <span>{fileInfo.preview.n_obs?.toLocaleString()} cells</span>
                  <span>{fileInfo.preview.n_vars?.toLocaleString()} genes</span>
                </>
              )}
              {fileInfo.preview.file_type === 'hdf5' && (
                <>
                  <span className="flex items-center">
                    <span className="w-2 h-2 bg-blue-500 rounded-full mr-2"></span>
                    HDF5 Format
                  </span>
                  <span>{fileInfo.preview.datasets?.length || 0} datasets</span>
                  <span>{fileInfo.preview.groups?.length || 0} groups</span>
                </>
              )}
              <span className="text-gray-500">
                {(fileInfo.preview.file_size / 1024 / 1024).toFixed(1)} MB
              </span>
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs text-gray-500 uppercase tracking-wide">File Type</div>
            <div className="text-sm font-medium text-indigo-700">
              {fileInfo.name.split('.').pop()?.toUpperCase()}
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 flex">
        {/* Tree view */}
        <div className="w-1/2 border-r border-gray-200 overflow-y-auto">
          <div className="p-2">
            {renderTreeNode(treeData)}
          </div>
        </div>

        {/* Data preview */}
        <div className="w-1/2 overflow-y-auto">
          {selectedNode ? (
            renderDataPreview()
          ) : (
            <div className="p-4 text-center text-gray-500">
              <p>Select an item from the tree to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default H5FileViewer
