import { DrillDownProps } from './types'

export default function RunsDrillDown({ data, cardLabel }: DrillDownProps) {
  let runs = data || []

  if (cardLabel === 'Successful') {
    runs = runs.filter((r: any) => r.status === 'completed' || r.status === 'success')
  } else if (cardLabel === 'Failed') {
    runs = runs.filter((r: any) => r.status === 'failed' || r.status === 'error' || r.status === 'cancelled')
  } else if (cardLabel === 'Today') {
    const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000)
    runs = runs.filter((r: any) => new Date(r.created_at + 'Z') > oneDayAgo)
  }

  const statusCounts = {
    completed: data.filter((r: any) => r.status === 'completed' || r.status === 'success').length,
    failed: data.filter((r: any) => r.status === 'failed' || r.status === 'error' || r.status === 'cancelled').length,
    running: data.filter((r: any) => r.status === 'running' || r.status === 'in_progress' || r.status === 'pending').length,
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-emerald-500/10 rounded-lg p-3 text-center">
          <div className="text-xl font-bold text-emerald-400">{statusCounts.completed}</div>
          <div className="text-xs text-slate-400">Completed</div>
        </div>
        <div className="bg-red-500/10 rounded-lg p-3 text-center">
          <div className="text-xl font-bold text-red-400">{statusCounts.failed}</div>
          <div className="text-xs text-slate-400">Failed</div>
        </div>
        <div className="bg-sky-500/10 rounded-lg p-3 text-center">
          <div className="text-xl font-bold text-sky-400">{statusCounts.running}</div>
          <div className="text-xs text-slate-400">Running</div>
        </div>
      </div>
      <div className="text-xs text-slate-500 text-center">
        Showing {runs.length} of {data.length} runs
      </div>
      <div className="max-h-64 overflow-y-auto space-y-2">
        {runs.slice(0, 30).map((run: any, idx: number) => (
          <div key={run.id || idx} className="bg-slate-700/50 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-white font-medium">{run.workflow_name || 'Unknown Workflow'}</span>
              <span className={
                run.status === 'completed' || run.status === 'success' ? 'text-xs px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400' :
                run.status === 'failed' || run.status === 'error' || run.status === 'cancelled' ? 'text-xs px-2 py-0.5 rounded bg-red-500/20 text-red-400' :
                'text-xs px-2 py-0.5 rounded bg-sky-500/20 text-sky-400'
              }>
                {run.status}
              </span>
            </div>
            <div className="flex items-center justify-between mt-2">
              <span className="text-xs text-slate-400">
                {run.started_at || run.created_at ? new Date((run.started_at || run.created_at) + 'Z').toLocaleString() : 'No date'}
              </span>
              {run.phase && <span className="text-xs text-slate-500">{run.phase}</span>}
            </div>
            {(run.total_nodes > 0 || run.completed_nodes > 0) && (
              <div className="mt-2 text-xs text-slate-500">
                Nodes: {run.completed_nodes || 0}/{run.total_nodes || 0} completed
                {run.failed_nodes > 0 && <span className="text-red-400 ml-2">({run.failed_nodes} failed)</span>}
              </div>
            )}
          </div>
        ))}
        {runs.length === 0 && (
          <div className="text-center text-slate-400 py-4">No runs found matching criteria</div>
        )}
      </div>
    </div>
  )
}
