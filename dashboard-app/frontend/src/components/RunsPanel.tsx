import { useState } from 'react'
import { Run } from '../types'
import { Workflow, CheckCircle, XCircle, Clock, RefreshCw, ExternalLink, ChevronDown, Filter, Search, FileText } from 'lucide-react'
import { formatDistanceToNow, format } from 'date-fns'
import DiffViewer, { FileDiff } from './DiffViewer'

interface RunsPanelProps {
  runs: Run[]
  onRetry: (runId: string) => void
  onOpenInEditor: (path: string, line?: number) => void
}

type StatusFilter = 'all' | 'success' | 'failure' | 'running'

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

  const statusColors: Record<string, string> = {
    running: 'text-sky-400 bg-sky-500/20',
    success: 'text-emerald-400 bg-emerald-500/20',
    failure: 'text-red-400 bg-red-500/20',
    failed: 'text-red-400 bg-red-500/20',
    timeout: 'text-orange-400 bg-orange-500/20',
    pending: 'text-slate-400 bg-slate-500/20',
    completed: 'text-emerald-400 bg-emerald-500/20',
  }

  const statusIcons: Record<string, typeof Clock> = {
    running: Clock,
    success: CheckCircle,
    failure: XCircle,
    failed: XCircle,
    timeout: Clock,
    pending: Clock,
    completed: CheckCircle,
  }

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
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Workflow className="w-5 h-5 text-indigo-400" />
          <h3 className="text-lg font-semibold text-white">Agent Runs</h3>
          <span className="text-sm text-slate-400">({filteredRuns.length} of {runs.length})</span>
        </div>

        <div className="flex items-center space-x-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search runs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-slate-700 text-sm text-white rounded-lg pl-9 pr-4 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500 w-64"
            />
          </div>

          {/* Status filter */}
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
              className="bg-slate-700 text-sm text-white rounded-md px-3 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500"
            >
              <option value="all">All Status</option>
              <option value="success">Success</option>
              <option value="failure">Failure</option>
              <option value="running">Running</option>
            </select>
          </div>
        </div>
      </div>

      {/* Runs list */}
      <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2">
        {filteredRuns.map(run => {
          const isExpanded = expandedId === run.id
          const StatusIcon = getStatusIcon(run.status)

          return (
            <div
              key={run.id}
              className={`bg-slate-700/50 rounded-lg border transition-all
                ${run.status === 'failure' ? 'border-red-500/30' : 'border-transparent'}
                ${isExpanded ? 'ring-2 ring-sky-500/50' : ''}`}
            >
              {/* Main row */}
              <div
                className="p-3 cursor-pointer"
                onClick={() => setExpandedId(isExpanded ? null : run.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3 flex-1 min-w-0">
                    <div className={`p-2 rounded-lg ${getStatusColor(run.status)}`}>
                      <StatusIcon className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-0.5">
                        <span className="text-sm font-medium text-white truncate">{run.description}</span>
                        <span className="px-1.5 py-0.5 rounded bg-slate-600 text-xs text-slate-300 flex-shrink-0">
                          {run.agent_type}
                        </span>
                      </div>
                      <div className="text-xs text-slate-400">
                        {formatDistanceToNow(new Date(run.started_at), { addSuffix: true })}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-4 flex-shrink-0 ml-4">
                    <div className="text-right">
                      <div className="text-sm font-medium text-white">{formatDuration(run.duration_ms)}</div>
                      <div className="text-xs text-slate-400">{run.files_touched.length} files</div>
                    </div>
                    <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                  </div>
                </div>
              </div>

              {/* Expanded content */}
              {isExpanded && (
                <div className="px-3 pb-3 border-t border-slate-600">
                  <div className="pt-3 space-y-3">
                    {/* Timestamps */}
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-slate-400">Started:</span>
                        <span className="text-white ml-2">{format(new Date(run.started_at), 'MMM d, HH:mm:ss')}</span>
                      </div>
                      {run.completed_at && (
                        <div>
                          <span className="text-slate-400">Completed:</span>
                          <span className="text-white ml-2">{format(new Date(run.completed_at), 'MMM d, HH:mm:ss')}</span>
                        </div>
                      )}
                    </div>

                    {/* Outcome reason */}
                    {run.outcome_reason && (
                      <div>
                        <div className="text-xs text-slate-400 mb-1">Outcome</div>
                        <div className={`text-sm ${run.status === 'failure' ? 'text-red-400' : 'text-slate-300'}`}>
                          {run.outcome_reason}
                        </div>
                      </div>
                    )}

                    {/* Heuristics used */}
                    {run.heuristics_used.length > 0 && (
                      <div>
                        <div className="text-xs text-slate-400 mb-1">Heuristics Used ({run.heuristics_used.length})</div>
                        <div className="flex flex-wrap gap-1">
                          {run.heuristics_used.map(id => (
                            <span key={id} className="px-2 py-0.5 rounded bg-violet-500/20 text-violet-400 text-xs">
                              #{id}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Files touched */}
                    {run.files_touched.length > 0 && (
                      <div>
                        <div className="text-xs text-slate-400 mb-1">Files Touched ({run.files_touched.length})</div>
                        <div className="space-y-1 max-h-32 overflow-y-auto">
                          {run.files_touched.map((file, idx) => (
                            <div
                              key={idx}
                              className="flex items-center justify-between text-sm bg-slate-800/50 rounded px-2 py-1 group"
                            >
                              <span className="text-slate-300 truncate">{file}</span>
                              <button
                                onClick={(e) => { e.stopPropagation(); onOpenInEditor(file) }}
                                className="opacity-0 group-hover:opacity-100 text-sky-400 hover:text-sky-300 transition"
                              >
                                <ExternalLink className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Actions */}
                    <div className="flex items-center space-x-2 pt-2">
                      <button
                        onClick={(e) => { e.stopPropagation(); handleViewChanges(run.id) }}
                        disabled={loadingDiff === run.id}
                        className="flex items-center space-x-1 px-3 py-1.5 bg-violet-500/20 text-violet-400 rounded-lg text-sm hover:bg-violet-500/30 transition disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <FileText className="w-4 h-4" />
                        <span>{loadingDiff === run.id ? 'Loading...' : 'View Changes'}</span>
                      </button>
                      {run.status === 'failure' && (
                        <button
                          onClick={(e) => { e.stopPropagation(); onRetry(run.id) }}
                          className="flex items-center space-x-1 px-3 py-1.5 bg-sky-500/20 text-sky-400 rounded-lg text-sm hover:bg-sky-500/30 transition"
                        >
                          <RefreshCw className="w-4 h-4" />
                          <span>Retry</span>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
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
