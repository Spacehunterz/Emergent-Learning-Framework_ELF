import { useState } from 'react'
import { X, ChevronDown, ChevronRight, Copy, Check } from 'lucide-react'

export interface FileDiff {
  path: string
  changes: DiffChange[]
  additions: number
  deletions: number
}

export interface DiffChange {
  type: 'add' | 'remove' | 'context'
  lineNumber: number
  content: string
  oldLineNumber?: number
  newLineNumber?: number
}

interface DiffViewerProps {
  runId: string
  diffs: FileDiff[]
  onClose: () => void
}

export default function DiffViewer({ runId, diffs, onClose }: DiffViewerProps) {
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set(diffs.map(d => d.path)))
  const [viewMode, setViewMode] = useState<'split' | 'unified'>('unified')
  const [copiedPath, setCopiedPath] = useState<string | null>(null)

  const toggleFile = (path: string) => {
    setExpandedFiles(prev => {
      const next = new Set(prev)
      if (next.has(path)) {
        next.delete(path)
      } else {
        next.add(path)
      }
      return next
    })
  }

  const copyPath = (path: string) => {
    navigator.clipboard.writeText(path)
    setCopiedPath(path)
    setTimeout(() => setCopiedPath(null), 2000)
  }

  const expandAll = () => {
    setExpandedFiles(new Set(diffs.map(d => d.path)))
  }

  const collapseAll = () => {
    setExpandedFiles(new Set())
  }

  const totalAdditions = diffs.reduce((sum, d) => sum + d.additions, 0)
  const totalDeletions = diffs.reduce((sum, d) => sum + d.deletions, 0)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-slate-900 rounded-lg shadow-2xl w-full max-w-6xl max-h-[90vh] flex flex-col border border-slate-700">
        {/* Header */}
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
                {diffs.length} {diffs.length === 1 ? 'file' : 'files'} changed
              </span>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {/* View Mode Toggle */}
            <div className="flex items-center space-x-1 bg-slate-800 rounded-lg p-1">
              <button
                onClick={() => setViewMode('unified')}
                className={`px-3 py-1 text-sm rounded transition ${
                  viewMode === 'unified'
                    ? 'bg-sky-500 text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Unified
              </button>
              <button
                onClick={() => setViewMode('split')}
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
              onClick={expandAll}
              className="px-3 py-1 text-sm text-slate-400 hover:text-white transition"
            >
              Expand All
            </button>
            <button
              onClick={collapseAll}
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

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {diffs.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              No changes detected in this run
            </div>
          ) : (
            diffs.map((diff) => (
              <div key={diff.path} className="bg-slate-800 rounded-lg border border-slate-700">
                {/* File Header */}
                <div
                  className="flex items-center justify-between p-3 cursor-pointer hover:bg-slate-750 transition"
                  onClick={() => toggleFile(diff.path)}
                >
                  <div className="flex items-center space-x-2">
                    {expandedFiles.has(diff.path) ? (
                      <ChevronDown className="w-4 h-4 text-slate-400" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-slate-400" />
                    )}
                    <span className="font-mono text-sm text-white">{diff.path}</span>
                  </div>
                  <div className="flex items-center space-x-3">
                    <span className="text-xs text-emerald-400">+{diff.additions}</span>
                    <span className="text-xs text-red-400">-{diff.deletions}</span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        copyPath(diff.path)
                      }}
                      className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-white transition"
                    >
                      {copiedPath === diff.path ? (
                        <Check className="w-4 h-4 text-emerald-400" />
                      ) : (
                        <Copy className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Diff Content */}
                {expandedFiles.has(diff.path) && (
                  <div className="border-t border-slate-700">
                    {viewMode === 'unified' ? (
                      <UnifiedDiffView changes={diff.changes} />
                    ) : (
                      <SplitDiffView changes={diff.changes} />
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

// Unified Diff View (like GitHub)
function UnifiedDiffView({ changes }: { changes: DiffChange[] }) {
  return (
    <div className="font-mono text-xs">
      {changes.map((change, idx) => {
        const bgColor =
          change.type === 'add'
            ? 'bg-emerald-500/10 border-l-2 border-emerald-500'
            : change.type === 'remove'
            ? 'bg-red-500/10 border-l-2 border-red-500'
            : 'bg-slate-800/50'

        const textColor =
          change.type === 'add'
            ? 'text-emerald-300'
            : change.type === 'remove'
            ? 'text-red-300'
            : 'text-slate-400'

        const linePrefix = change.type === 'add' ? '+' : change.type === 'remove' ? '-' : ' '

        return (
          <div key={idx} className={`flex ${bgColor}`}>
            <div className="flex-shrink-0 w-20 px-2 py-1 text-slate-500 text-right select-none border-r border-slate-700/50">
              {change.type === 'remove' && change.oldLineNumber && (
                <span>{change.oldLineNumber}</span>
              )}
              {change.type === 'add' && change.newLineNumber && (
                <span className="ml-2">{change.newLineNumber}</span>
              )}
              {change.type === 'context' && (
                <>
                  <span>{change.oldLineNumber}</span>
                  <span className="ml-2">{change.newLineNumber}</span>
                </>
              )}
            </div>
            <div className={`flex-1 px-2 py-1 whitespace-pre overflow-x-auto ${textColor}`}>
              <span className="select-none mr-2">{linePrefix}</span>
              {change.content}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// Split Diff View (side-by-side)
function SplitDiffView({ changes }: { changes: DiffChange[] }) {
  // Group changes into pairs for side-by-side display
  const pairs: Array<{ left: DiffChange | null; right: DiffChange | null }> = []
  let i = 0

  while (i < changes.length) {
    const change = changes[i]

    if (change.type === 'context') {
      pairs.push({ left: change, right: change })
      i++
    } else if (change.type === 'remove') {
      // Look for a matching add
      const nextAdd = changes[i + 1]?.type === 'add' ? changes[i + 1] : null
      pairs.push({ left: change, right: nextAdd })
      i += nextAdd ? 2 : 1
    } else if (change.type === 'add') {
      pairs.push({ left: null, right: change })
      i++
    }
  }

  return (
    <div className="grid grid-cols-2 font-mono text-xs">
      {pairs.map((pair, idx) => (
        <div key={idx} className="contents">
          {/* Left side (removals) */}
          <div
            className={`border-r border-slate-700 ${
              pair.left?.type === 'remove'
                ? 'bg-red-500/10 border-l-2 border-l-red-500'
                : pair.left?.type === 'context'
                ? 'bg-slate-800/50'
                : 'bg-slate-900'
            }`}
          >
            {pair.left && (
              <div className="flex">
                <div className="flex-shrink-0 w-12 px-2 py-1 text-slate-500 text-right select-none border-r border-slate-700/50">
                  {pair.left.oldLineNumber}
                </div>
                <div
                  className={`flex-1 px-2 py-1 whitespace-pre overflow-x-auto ${
                    pair.left.type === 'remove' ? 'text-red-300' : 'text-slate-400'
                  }`}
                >
                  {pair.left.type === 'remove' && <span className="select-none mr-2">-</span>}
                  {pair.left.content}
                </div>
              </div>
            )}
          </div>

          {/* Right side (additions) */}
          <div
            className={
              pair.right?.type === 'add'
                ? 'bg-emerald-500/10 border-l-2 border-emerald-500'
                : pair.right?.type === 'context'
                ? 'bg-slate-800/50'
                : 'bg-slate-900'
            }
          >
            {pair.right && (
              <div className="flex">
                <div className="flex-shrink-0 w-12 px-2 py-1 text-slate-500 text-right select-none border-r border-slate-700/50">
                  {pair.right.newLineNumber}
                </div>
                <div
                  className={`flex-1 px-2 py-1 whitespace-pre overflow-x-auto ${
                    pair.right.type === 'add' ? 'text-emerald-300' : 'text-slate-400'
                  }`}
                >
                  {pair.right.type === 'add' && <span className="select-none mr-2">+</span>}
                  {pair.right.content}
                </div>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
