import { X } from 'lucide-react'
import { GraphNode, getColorForDomain } from './types'

interface NodeInfoPanelProps {
  node: GraphNode
  isSelected: boolean
  onClose?: () => void
}

export default function NodeInfoPanel({ node, isSelected, onClose }: NodeInfoPanelProps) {
  return (
    <div className="absolute top-4 right-4 glass-panel p-4 max-w-sm">
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1 min-w-0 pr-2">
          <div className="flex items-center space-x-2 mb-1">
            {node.is_golden && (
              <span className="text-xs px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30 font-medium">
                GOLDEN
              </span>
            )}
            <span className="text-xs px-2 py-0.5 rounded" style={{
              backgroundColor: getColorForDomain(node.domain) + '20',
              color: getColorForDomain(node.domain),
              borderColor: getColorForDomain(node.domain) + '30',
              borderWidth: '1px'
            }}>
              {node.domain}
            </span>
          </div>
          <h4 className="text-sm font-medium text-white mb-2">
            {node.fullText}
          </h4>
          {node.explanation && (
            <p className="text-xs text-slate-400 mb-2">
              {node.explanation}
            </p>
          )}
          <div className="flex items-center space-x-3 text-xs text-slate-400">
            <div>
              <span className="text-emerald-400">{node.times_validated}</span> validated
            </div>
            <div>
              <span className="text-red-400">{node.times_violated}</span> violated
            </div>
            <div>
              <span className="text-purple-400">{(node.confidence * 100).toFixed(0)}%</span> confidence
            </div>
          </div>
        </div>
        {isSelected && onClose && (
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white hover:bg-slate-700 rounded transition-colors flex-shrink-0"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  )
}
