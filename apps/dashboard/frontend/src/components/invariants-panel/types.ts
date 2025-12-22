import { Invariant } from '../../types'

export type ScopeFilter = 'all' | 'codebase' | 'module' | 'function' | 'runtime'
export type SeverityFilter = 'all' | 'error' | 'warning' | 'info'
export type StatusFilter = 'all' | 'active' | 'deprecated' | 'violated'

export interface InvariantsPanelProps {
  className?: string
}

export interface InvariantCardProps {
  invariant: Invariant
  isExpanded: boolean
  isLoading: boolean
  onToggle: () => void
  onValidate: (id: number) => void
  onViolate: (id: number) => void
}

export interface InvariantFiltersProps {
  scopeFilter: ScopeFilter
  severityFilter: SeverityFilter
  statusFilter: StatusFilter
  domainFilter: string
  domains: string[]
  onScopeChange: (scope: ScopeFilter) => void
  onSeverityChange: (severity: SeverityFilter) => void
  onStatusChange: (status: StatusFilter) => void
  onDomainChange: (domain: string) => void
}

export interface InvariantActionsProps {
  invariantId: number
  isLoading: boolean
  onValidate: () => void
  onViolate: () => void
}
