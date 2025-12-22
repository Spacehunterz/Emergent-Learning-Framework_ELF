import { CheckCircle, AlertTriangle, XCircle, Lightbulb } from 'lucide-react'
import { Assumption } from '../../types'

export function getStatusBadge(status: Assumption['status']) {
  switch (status) {
    case 'verified':
      return (
        <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 text-xs">
          <CheckCircle className="w-3 h-3" />
          <span>Verified</span>
        </span>
      )
    case 'challenged':
      return (
        <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 text-xs">
          <AlertTriangle className="w-3 h-3" />
          <span>Challenged</span>
        </span>
      )
    case 'invalidated':
      return (
        <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-red-500/20 text-red-400 text-xs">
          <XCircle className="w-3 h-3" />
          <span>Invalidated</span>
        </span>
      )
    default:
      return (
        <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-sky-500/20 text-sky-400 text-xs">
          <Lightbulb className="w-3 h-3" />
          <span>Active</span>
        </span>
      )
  }
}

export function getConfidenceColor(confidence: number) {
  if (confidence >= 0.8) return 'bg-emerald-500'
  if (confidence >= 0.5) return 'bg-amber-500'
  return 'bg-red-500'
}
