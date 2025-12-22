export interface LearningVelocityData {
  heuristics_by_day: Array<{ date: string; count: number }>
  learnings_by_day: Array<{ date: string; total: number; failures: number; successes: number }>
  promotions_by_day: Array<{ date: string; count: number }>
  confidence_by_day: Array<{ date: string; avg_confidence: number }>
  heuristics_by_week: Array<{ week: string; heuristics_count: number }>
  success_trend: Array<{ date: string; total: number; success_ratio: number }>
  current_streak: number
  heuristics_trend: number
  failure_to_learning_rate?: number
  confidence_improvement?: number
  promotion_rate?: number
  totals: {
    heuristics: number
    learnings: number
    promotions: number
    failures?: number
    heuristics_from_failures?: number
  }
}

export interface LearningVelocityProps {
  days?: number
}

export interface TimeframeControlsProps {
  timeframe: number
  onTimeframeChange: (days: number) => void
}

export interface MetricCardsProps {
  data: LearningVelocityData
  timeframe: number
}

export interface VelocityChartsProps {
  data: LearningVelocityData
}
