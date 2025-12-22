// Stats from API /api/stats endpoint
export interface Stats {
  total_runs: number
  total_executions: number
  total_trails: number
  total_heuristics: number
  golden_rules: number
  total_learnings: number
  failures: number
  successes: number
  successful_runs: number
  failed_runs: number
  avg_confidence: number
  total_validations: number
  total_violations: number
  metrics_last_hour: number
  runs_today: number
  // Query stats
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
  is_golden: boolean | number  // API may return 0/1 instead of true/false
  source_type: string
  created_at: string
  updated_at: string
}

// Hotspot from API /api/hotspots endpoint
export interface Hotspot {
  location: string
  trail_count: number
  total_strength: number
  scents: string[]
  agents: string[]
  agent_count: number
  last_activity: string
  first_activity: string
  related_heuristics: any[]
}

// Run interface for display (used by RunsPanel)
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

// ApiRun from API /api/runs endpoint
export interface ApiRun {
  id: number
  workflow_id: number | null
  workflow_name: string
  status: string
  phase: string
  total_nodes: number
  completed_nodes: number
  failed_nodes: number
  started_at: string
  completed_at: string | null
  created_at: string
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

// TimelineData from API /api/timeline endpoint
export interface TimelineData {
  runs: { date: string; runs: number }[]
  trails: { date: string; trails: number; strength: number }[]
  validations: { date: string; validations: number }[]
  failures: { date: string; failures: number }[]
}

// RawEvent from API /api/events endpoint (different field names than TimelineEvent)
export interface RawEvent {
  id?: number
  timestamp: string
  event_type?: string
  type?: string  // API uses 'type' instead of 'event_type'
  description?: string
  message?: string  // API uses 'message' instead of 'description'
  metadata?: Record<string, any>
  tags?: string  // API uses 'tags'
  context?: string
  file_path?: string
  line_number?: number
  domain?: string
}

// Anomaly interface for display (used by AnomalyPanel)
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

// ApiAnomaly from API /api/anomalies endpoint
export interface ApiAnomaly {
  type: string
  severity: string
  message: string
  data: Record<string, any>
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

export interface Session {
  session_id: string
  project: string
  project_path: string
  first_timestamp: string
  last_timestamp: string
  prompt_count: number
  first_prompt_preview: string
  git_branch: string
  is_agent: boolean
  file_path: string
  file_size: number
}

export interface SessionMessage {
  uuid: string
  type: 'user' | 'assistant'
  timestamp: string
  content: string
  is_command: boolean
  command_name?: string
  tool_use?: Array<{name: string, input: any}>
}

export interface SessionDetail extends Session {
  messages: SessionMessage[]
}

// Knowledge Systems Types

export interface Assumption {
  id: number;
  assumption: string;
  context: string;
  source: string | null;
  confidence: number;
  status: 'active' | 'verified' | 'challenged' | 'invalidated';
  domain: string | null;
  verified_count: number;
  challenged_count: number;
  last_verified_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SpikeReport {
  id: number;
  title: string;
  topic: string;
  question: string;
  findings: string;
  gotchas: string | null;
  resources: string | null;
  time_invested_minutes: number | null;
  domain: string | null;
  tags: string | null;
  usefulness_score: number;
  access_count: number;
  created_at: string;
  updated_at: string;
}

export interface Invariant {
  id: number;
  statement: string;
  rationale: string;
  domain: string | null;
  scope: 'codebase' | 'module' | 'function' | 'runtime';
  validation_type: 'manual' | 'automated' | 'test' | null;
  validation_code: string | null;
  severity: 'error' | 'warning' | 'info';
  status: 'active' | 'deprecated' | 'violated';
  violation_count: number;
  last_validated_at: string | null;
  last_violated_at: string | null;
  created_at: string;
  updated_at: string;
}

// Fraud Detection Types

export interface FraudReport {
  id: number;
  heuristic_id: number;
  fraud_score: number;
  classification: 'clean' | 'low_confidence' | 'suspicious' | 'fraud_likely' | 'fraud_confirmed';
  likelihood_ratio: number | null;
  signal_count: number;
  created_at: string;
  reviewed_at: string | null;
  reviewed_by: string | null;
  review_outcome: 'true_positive' | 'false_positive' | 'pending' | null;

  // Joined from heuristics table
  domain: string;
  rule: string;
  confidence: number;
  status?: string;
  times_validated?: number;
  times_violated?: number;
  times_contradicted?: number;

  // Signals (only in detailed view)
  signals?: AnomalySignal[];
}

export interface AnomalySignal {
  id: number;
  fraud_report_id: number;
  heuristic_id: number;
  detector_name: string;
  score: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  reason: string;
  evidence: Record<string, any>;
  created_at: string;
}
