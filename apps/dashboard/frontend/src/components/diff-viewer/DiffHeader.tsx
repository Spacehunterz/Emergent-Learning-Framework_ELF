import { X } from 'lucide-react'
import { DiffHeaderProps } from './types'

export default function DiffHeader({
  runId,
  totalAdditions,
  totalDeletions,
  filesChanged,
  viewMode,
  onViewModeChange,
  onExpandAll,
  onCollapseAll,
  onClose,
}: DiffHeaderProps) {
  return (
    <div className="flex items-center justify-between p-4 border-b border-slate-700">
      <div>
        <h2 className="text-xl font-bold text-white">Changes in Run #{runId}</h2>
        <div className="flex items-center space-x-4 mt-1 text-sm">
          <span className="text-emerald-400">
            +{totalAdditions} {totalAdditions === 1 ? 'addition' : 'additions'}
          </span>
          <span className="text-red-400">
            -{totalDeletions} {totalDeletions === 1 ? 'deletion' : 'deletions'}
          </span>
          <span className="text-slate-400">
            {filesChanged} {filesChanged === 1 ? 'file' : 'files'} changed
          </span>
        </div>
      </div>
      <div className="flex items-center space-x-2">
        {/* View Mode Toggle */}
        <div className="flex items-center space-x-1 bg-slate-800 rounded-lg p-1">
          <button
            onClick={() => onViewModeChange('unified')}
            className={`px-3 py-1 text-sm rounded transition ${
              viewMode === 'unified'
                ? 'bg-sky-500 text-white'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Unified
          </button>
          <button
            onClick={() => onViewModeChange('split')}
            className={`px-3 py-1 text-sm rounded transition ${
              viewMode === 'split'
                ? 'bg-sky-500 text-white'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Split
          </button>
        </div>

        {/* Expand/Collapse */}
        <button
          onClick={onExpandAll}
          className="px-3 py-1 text-sm text-slate-400 hover:text-white transition"
        >
          Expand All
        </button>
        <button
          onClick={onCollapseAll}
          className="px-3 py-1 text-sm text-slate-400 hover:text-white transition"
        >
          Collapse All
        </button>

        {/* Close button */}
        <button
          onClick={onClose}
          className="p-2 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition"
        >
          <X className="w-5 h-5" />
        </button>
      </div>
    </div>
  )
}
