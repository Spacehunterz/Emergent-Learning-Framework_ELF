export interface Stats {
  total_runs: number
  successful_runs: number
  failed_runs: number
  success_rate: number
  total_heuristics: number
  golden_rules: number
  total_learnings: number
  hotspot_count: number
  avg_confidence: number
  total_validations: number
  runs_today: number
  active_domains: number
  queries_today: number
  total_queries: number
  avg_query_duration_ms: number
}

export interface Heuristic {
  id: number
  domain: string
  rule: string
  explanation: string | null
  confidence: number
  times_validated: number
  times_violated: number
  is_golden: boolean
  source_type: string
  created_at: string
  updated_at: string
}

export interface Hotspot {
  id: number
  file_path: string
  function_name: string | null
  hit_count: number
  last_hit: string
  strength: number
  domains: string[]
  severity: 'low' | 'medium' | 'high' | 'critical'
}

export interface TreemapNode {
  name: string
  value: number
  strength: number
  severity: string
  domains: string[]
  children?: TreemapNode[]
}

export interface Run {
  id: string
  agent_type: string
  description: string
  status: 'running' | 'success' | 'failure' | 'timeout'
  started_at: string
  completed_at: string | null
  duration_ms: number | null
  heuristics_used: number[]
  files_touched: string[]
  outcome_reason: string | null
}

export interface TimelineEvent {
  id: number
  timestamp: string
  event_type: 'task_start' | 'task_end' | 'heuristic_consulted' | 'heuristic_validated' | 'heuristic_violated' | 'failure_recorded' | 'golden_promoted'
  description: string
  metadata: Record<string, any>
  file_path?: string
  line_number?: number
  domain?: string
}

export interface Anomaly {
  id: string
  type: 'repeated_failure' | 'confidence_drop' | 'hotspot_surge' | 'validation_gap' | 'rule_conflict'
  severity: 'low' | 'medium' | 'high' | 'critical'
  title: string
  description: string
  timestamp: string
  related_ids: number[]
  suggested_action?: string
}

export interface Learning {
  id: number
  type: 'failure' | 'success' | 'observation' | 'experiment'
  filepath: string
  title: string
  summary: string
  domain: string
  severity: number
  created_at: string
}

export interface QueryResult {
  query: string
  interpretation: string
  results: any[]
  suggestions: string[]
}

export interface Workflow {
  id: string
  name: string
  description: string
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
  is_active: boolean
  created_at: string
}

export interface WorkflowNode {
  id: string
  type: 'trigger' | 'condition' | 'action' | 'notification'
  label: string
  config: Record<string, any>
  position: { x: number; y: number }
}

export interface WorkflowEdge {
  id: string
  source: string
  target: string
  label?: string
}

export interface Domain {
  name: string
  heuristic_count: number
  golden_count: number
  avg_confidence: number
  recent_activity: number
}
