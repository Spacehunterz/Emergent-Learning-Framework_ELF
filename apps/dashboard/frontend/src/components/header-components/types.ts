import { Activity, Brain, Clock, Search, Workflow, History, Lightbulb, FileSearch, ShieldCheck, Shield, TrendingUp, Network, LucideIcon } from 'lucide-react'

export interface CeoItem {
  filename: string
  title: string
  priority: string
  status: string
  date: string | null
  summary: string
  path: string
}

export type TabId = 'overview' | 'heuristics' | 'runs' | 'timeline' | 'query' | 'analytics' | 'graph' | 'sessions' | 'assumptions' | 'spikes' | 'invariants' | 'fraud'

export type TabGroup = 'knowledge' | 'research' | 'operations' | 'analysis'

export interface TabConfig {
  id: TabId
  label: string
  icon: LucideIcon
  group: TabGroup
}

export interface TabGroupConfig {
  label: string
  gradient: string
  accent: string
}

export const tabGroups: Record<TabGroup, TabGroupConfig> = {
  knowledge: {
    label: 'Knowledge',
    gradient: 'from-violet-500/10 via-purple-500/10 to-indigo-500/10',
    accent: 'violet'
  },
  research: {
    label: 'Research',
    gradient: 'from-cyan-500/10 via-sky-500/10 to-blue-500/10',
    accent: 'cyan'
  },
  operations: {
    label: 'Operations',
    gradient: 'from-emerald-500/10 via-green-500/10 to-teal-500/10',
    accent: 'emerald'
  },
  analysis: {
    label: 'Analysis',
    gradient: 'from-amber-500/10 via-yellow-500/10 to-orange-500/10',
    accent: 'amber'
  },
}

export const tabs: TabConfig[] = [
  // Knowledge group - understanding the system
  { id: 'overview', label: 'Overview', icon: Activity, group: 'knowledge' },
  { id: 'heuristics', label: 'Heuristics', icon: Brain, group: 'knowledge' },
  { id: 'assumptions', label: 'Assumptions', icon: Lightbulb, group: 'knowledge' },
  // Research group - investigation & exploration
  { id: 'spikes', label: 'Spikes', icon: FileSearch, group: 'research' },
  { id: 'invariants', label: 'Invariants', icon: ShieldCheck, group: 'research' },
  { id: 'graph', label: 'Graph', icon: Network, group: 'research' },
  // Operations group - execution & history
  { id: 'runs', label: 'Runs', icon: Workflow, group: 'operations' },
  { id: 'sessions', label: 'Sessions', icon: History, group: 'operations' },
  { id: 'timeline', label: 'Timeline', icon: Clock, group: 'operations' },
  // Analysis group - insights & queries
  { id: 'analytics', label: 'Analytics', icon: TrendingUp, group: 'analysis' },
  { id: 'query', label: 'Query', icon: Search, group: 'analysis' },
  { id: 'fraud', label: 'Fraud', icon: Shield, group: 'analysis' },
]

export const priorityColors: Record<string, string> = {
  Critical: 'bg-red-500/20 text-red-400 border-red-500/30',
  High: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  Medium: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  Low: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
}
