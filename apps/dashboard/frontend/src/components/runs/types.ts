import { Run } from '../../types'
import { Clock, CheckCircle, XCircle } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export type StatusFilter = 'all' | 'success' | 'failure' | 'running'

export interface RunsPanelProps {
  runs: Run[]
  onRetry: (runId: string) => void
  onOpenInEditor: (path: string, line?: number) => void
}

export interface RunsFiltersProps {
  searchQuery: string
  onSearchChange: (query: string) => void
  statusFilter: StatusFilter
  onStatusFilterChange: (filter: StatusFilter) => void
  filteredCount: number
  totalCount: number
}

export interface RunCardProps {
  run: Run
  isExpanded: boolean
  onToggle: (runId: string) => void
  getStatusColor: (status: string) => string
  getStatusIcon: (status: string) => LucideIcon
  formatDuration: (ms: number | null) => string
}

export interface RunDetailProps {
  run: Run
  onOpenInEditor: (path: string, line?: number) => void
  onRetry: (runId: string) => void
  onViewChanges: (runId: string) => void
  loadingDiff: string | null
}

// Status configuration
export const statusColors: Record<string, string> = {
  running: 'text-sky-400 bg-sky-500/20',
  success: 'text-emerald-400 bg-emerald-500/20',
  failure: 'text-red-400 bg-red-500/20',
  failed: 'text-red-400 bg-red-500/20',
  timeout: 'text-orange-400 bg-orange-500/20',
  pending: 'text-slate-400 bg-slate-500/20',
  completed: 'text-emerald-400 bg-emerald-500/20',
}

export const statusIcons: Record<string, LucideIcon> = {
  running: Clock,
  success: CheckCircle,
  failure: XCircle,
  failed: XCircle,
  timeout: Clock,
  pending: Clock,
  completed: CheckCircle,
}
