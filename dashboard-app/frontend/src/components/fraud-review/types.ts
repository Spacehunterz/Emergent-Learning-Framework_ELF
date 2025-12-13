import { FraudReport, AnomalySignal } from '../../types'

export interface FraudReviewPanelProps {
  className?: string
}

export interface ReportCardProps {
  report: FraudReport
  isExpanded: boolean
  isLoading: boolean
  selectedReport: FraudReport | null
  onToggle: () => void
  onReview: (id: number, outcome: 'true_positive' | 'false_positive') => void
}

export interface SignalListProps {
  signals: AnomalySignal[]
  performanceStats: {
    validated: number
    violated: number
    contradicted: number
  }
}

export type ReviewOutcome = 'true_positive' | 'false_positive'
