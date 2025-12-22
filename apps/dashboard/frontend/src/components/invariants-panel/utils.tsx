import { AlertOctagon, AlertTriangle, Info, CheckCircle, XCircle, Archive } from 'lucide-react'
import { Invariant } from '../../types'

export function getSeverityBadge(severity: Invariant['severity']) {
  switch (severity) {
    case 'error':
      return (
        <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-red-500/20 text-red-400 text-xs">
          <AlertOctagon className="w-3 h-3" />
          <span>Error</span>
        </span>
      )
    case 'warning':
      return (
        <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 text-xs">
          <AlertTriangle className="w-3 h-3" />
          <span>Warning</span>
        </span>
      )
    default:
      return (
        <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-sky-500/20 text-sky-400 text-xs">
          <Info className="w-3 h-3" />
          <span>Info</span>
        </span>
      )
  }
}

export function getStatusBadge(status: Invariant['status']) {
  switch (status) {
    case 'violated':
      return (
        <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-red-500/20 text-red-400 text-xs">
          <XCircle className="w-3 h-3" />
          <span>Violated</span>
        </span>
      )
    case 'deprecated':
      return (
        <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-slate-500/20 text-slate-400 text-xs">
          <Archive className="w-3 h-3" />
          <span>Deprecated</span>
        </span>
      )
    default:
      return (
        <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 text-xs">
          <CheckCircle className="w-3 h-3" />
          <span>Active</span>
        </span>
      )
  }
}

export function getScopeBadge(scope: Invariant['scope']) {
  const colors: Record<string, string> = {
    codebase: 'bg-violet-500/20 text-violet-400',
    module: 'bg-sky-500/20 text-sky-400',
    function: 'bg-emerald-500/20 text-emerald-400',
    runtime: 'bg-amber-500/20 text-amber-400',
  }

  return (
    <span className={`px-2 py-0.5 rounded text-xs ${colors[scope] || 'bg-slate-500/20 text-slate-400'}`}>
      {scope}
    </span>
  )
}
