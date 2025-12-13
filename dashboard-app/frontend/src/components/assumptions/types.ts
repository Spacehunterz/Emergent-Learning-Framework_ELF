import { Assumption } from '../../types'

export type StatusFilter = 'all' | 'active' | 'verified' | 'challenged' | 'invalidated'

export interface AssumptionsPanelProps {
  className?: string
}

export interface AssumptionFiltersProps {
  statusFilter: StatusFilter
  domainFilter: string
  minConfidence: number
  domains: string[]
  onStatusChange: (status: StatusFilter) => void
  onDomainChange: (domain: string) => void
  onConfidenceChange: (confidence: number) => void
}

export interface AssumptionCardProps {
  assumption: Assumption
  isExpanded: boolean
  isLoading: boolean
  onToggle: () => void
  onVerify: (id: number) => void
  onChallenge: (id: number) => void
}
