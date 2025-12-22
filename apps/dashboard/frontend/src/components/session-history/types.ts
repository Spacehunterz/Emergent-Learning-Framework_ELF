import { Session, SessionDetail } from '../../types'

export type DateFilter = 'today' | '7days' | '30days' | 'all'

export interface SessionHistoryPanelProps {
  className?: string
}

export interface SessionFiltersProps {
  searchQuery: string
  onSearchChange: (query: string) => void
  projectFilter: string
  onProjectFilterChange: (project: string) => void
  dateFilter: DateFilter
  onDateFilterChange: (filter: DateFilter) => void
  projects: string[]
  filteredCount: number
  totalCount: number
}

export interface SessionCardProps {
  session: Session
  isExpanded: boolean
  isLoading: boolean
  onToggle: (sessionId: string) => void
  formatTimestamp: (timestamp: string) => string
}

export interface SessionDetailProps {
  session: Session
  sessionDetail: SessionDetail
  isLoading: boolean
  formatTimestamp: (timestamp: string) => string
}

export interface MessageItemProps {
  message: any
  formatTimestamp: (timestamp: string) => string
}
