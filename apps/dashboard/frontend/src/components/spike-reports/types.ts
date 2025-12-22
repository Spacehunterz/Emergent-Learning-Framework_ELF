import { SpikeReport } from '../../types'

export interface SpikeReportsPanelProps {
  className?: string
}

export interface SpikeReportFiltersProps {
  searchQuery: string
  domainFilter: string
  tagFilter: string
  domains: string[]
  tags: string[]
  onSearchChange: (query: string) => void
  onDomainChange: (domain: string) => void
  onTagChange: (tag: string) => void
}

export interface ReportCardProps {
  report: SpikeReport
  isExpanded: boolean
  isRating: boolean
  onToggle: () => void
  onRate: (id: number, score: number) => void
}

export interface StarRatingProps {
  score: number
  onChange?: (score: number) => void
  loading?: boolean
}
