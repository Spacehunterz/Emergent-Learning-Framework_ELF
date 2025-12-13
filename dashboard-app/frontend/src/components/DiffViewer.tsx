import { useState } from 'react'
import {
  DiffHeader,
  FileHeader,
  UnifiedDiffView,
  SplitDiffView,
  DiffViewerProps,
} from './diff-viewer'

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
        <DiffHeader
          runId={runId}
          totalAdditions={totalAdditions}
          totalDeletions={totalDeletions}
          filesChanged={diffs.length}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
          onExpandAll={expandAll}
          onCollapseAll={collapseAll}
          onClose={onClose}
        />

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {diffs.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              No changes detected in this run
            </div>
          ) : (
            diffs.map((diff) => (
              <div key={diff.path} className="bg-slate-800 rounded-lg border border-slate-700">
                <FileHeader
                  path={diff.path}
                  additions={diff.additions}
                  deletions={diff.deletions}
                  isExpanded={expandedFiles.has(diff.path)}
                  onToggle={() => toggleFile(diff.path)}
                  onCopyPath={copyPath}
                  copiedPath={copiedPath}
                />

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

export type { FileDiff, DiffChange } from './diff-viewer'
