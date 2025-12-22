export type DrillDownView = 'main' | 'runs' | 'heuristics' | 'golden' | 'hotspots' | 'learnings' | 'queries'

export interface DrillDownProps {
  data: any[]
  cardLabel?: string
}
