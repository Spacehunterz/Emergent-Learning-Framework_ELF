import { ChevronDown, ChevronRight, Copy, Check } from 'lucide-react'
import { FileHeaderProps } from './types'

export default function FileHeader({
  path,
  additions,
  deletions,
  isExpanded,
  onToggle,
  onCopyPath,
  copiedPath,
}: FileHeaderProps) {
  return (
    <div
      className="flex items-center justify-between p-3 cursor-pointer hover:bg-slate-750 transition"
      onClick={onToggle}
    >
      <div className="flex items-center space-x-2">
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-slate-400" />
        ) : (
          <ChevronRight className="w-4 h-4 text-slate-400" />
        )}
        <span className="font-mono text-sm text-white">{path}</span>
      </div>
      <div className="flex items-center space-x-3">
        <span className="text-xs text-emerald-400">+{additions}</span>
        <span className="text-xs text-red-400">-{deletions}</span>
        <button
          onClick={(e) => {
            e.stopPropagation()
            onCopyPath(path)
          }}
          className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-white transition"
        >
          {copiedPath === path ? (
            <Check className="w-4 h-4 text-emerald-400" />
          ) : (
            <Copy className="w-4 h-4" />
          )}
        </button>
      </div>
    </div>
  )
}
