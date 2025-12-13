import { useState } from 'react'
import { Clock } from 'lucide-react'
import DiffViewer, { FileDiff } from './DiffViewer'
import { RunsFilters, RunCard, RunDetail, statusColors, statusIcons } from './runs'
import type { RunsPanelProps, StatusFilter } from './runs/types'

export default function RunsPanel({ runs, onRetry, onOpenInEditor }: RunsPanelProps) {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [diffViewerOpen, setDiffViewerOpen] = useState(false)
  const [selectedRunDiffs, setSelectedRunDiffs] = useState<{ runId: string; diffs: FileDiff[] } | null>(null)
  const [loadingDiff, setLoadingDiff] = useState<string | null>(null)

  // Filter runs
  const filteredRuns = runs.filter(run => {
    if (statusFilter !== 'all' && run.status !== statusFilter) return false
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      return (
        run.description.toLowerCase().includes(query) ||
        run.agent_type.toLowerCase().includes(query) ||
        run.files_touched.some(f => f.toLowerCase().includes(query))
      )
    }
    return true
  })

  // Default fallbacks for unknown statuses
  const getStatusColor = (status: string) => statusColors[status] || 'text-slate-400 bg-slate-500/20'
  const getStatusIcon = (status: string) => statusIcons[status] || Clock

  const formatDuration = (ms: number | null) => {
    if (ms === null) return '-'
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${(ms / 60000).toFixed(1)}m`
  }

  const handleViewChanges = async (runId: string) => {
    setLoadingDiff(runId)
    try {
      // Fetch diffs from backend
      const response = await fetch(`http://localhost:8888/api/runs/${runId}/diff`)
      if (!response.ok) {
        throw new Error('Failed to fetch diffs')
      }
      const data = await response.json()
      setSelectedRunDiffs({ runId, diffs: data.diffs })
      setDiffViewerOpen(true)
    } catch (err) {
      console.error('Failed to load diffs:', err)
    } finally {
      setLoadingDiff(null)
    }
  }

  return (
    <>
      {/* Diff Viewer Modal */}
      {diffViewerOpen && selectedRunDiffs && (
        <DiffViewer
          runId={selectedRunDiffs.runId}
          diffs={selectedRunDiffs.diffs}
          onClose={() => {
            setDiffViewerOpen(false)
            setSelectedRunDiffs(null)
          }}
        />
      )}
      <div className="bg-slate-800 rounded-lg p-4">
        <RunsFilters
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          statusFilter={statusFilter}
          onStatusFilterChange={setStatusFilter}
          filteredCount={filteredRuns.length}
          totalCount={runs.length}
        />

        {/* Runs list */}
        <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2">
          {filteredRuns.map(run => {
            const isExpanded = expandedId === run.id

            return (
              <div
                key={run.id}
                className={`bg-slate-700/50 rounded-lg border transition-all
                  ${run.status === 'failure' ? 'border-red-500/30' : 'border-transparent'}
                  ${isExpanded ? 'ring-2 ring-sky-500/50' : ''}`}
              >
                <RunCard
                  run={run}
                  isExpanded={isExpanded}
                  onToggle={(id) => setExpandedId(isExpanded ? null : id)}
                  getStatusColor={getStatusColor}
                  getStatusIcon={getStatusIcon}
                  formatDuration={formatDuration}
                />

                {isExpanded && (
                  <RunDetail
                    run={run}
                    onOpenInEditor={onOpenInEditor}
                    onRetry={onRetry}
                    onViewChanges={handleViewChanges}
                    loadingDiff={loadingDiff}
                  />
                )}
              </div>
            )
          })}

          {filteredRuns.length === 0 && (
            <div className="text-center text-slate-400 py-12">
              No runs found
            </div>
          )}
        </div>
      </div>
    </>
  )
}
