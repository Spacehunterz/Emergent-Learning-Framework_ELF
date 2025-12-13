import { Brain, Target, AlertTriangle, Lightbulb } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export interface QueryResult {
  query: string
  heuristics: any[]
  learnings: any[]
  hotspots: any[]
  runs: any[]
  summary: string
}

export interface ExampleQuery {
  icon: LucideIcon
  text: string
  category: string
}

export const exampleQueries: ExampleQuery[] = [
  { icon: Brain, text: "What heuristics are most validated?", category: "Heuristics" },
  { icon: Target, text: "Show hotspots in authentication code", category: "Hotspots" },
  { icon: AlertTriangle, text: "What failures happened today?", category: "Failures" },
  { icon: Lightbulb, text: "Which rules should be promoted to golden?", category: "Insights" },
]

export interface QueryInputProps {
  query: string
  onQueryChange: (query: string) => void
  onSubmit: () => void
  isLoading: boolean
  inputRef: React.RefObject<HTMLInputElement>
}

export interface ExampleQueriesProps {
  onSelectQuery: (query: string) => void
}

export interface ResultItemProps {
  item: any
  index: number
}

export interface QueryResultsProps {
  result: QueryResult
}

export interface QueryHistoryProps {
  history: string[]
  onSelectQuery: (query: string) => void
}
