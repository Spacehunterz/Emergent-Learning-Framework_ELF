import { Activity, Brain, Clock, Search, Workflow, History, Lightbulb, FileSearch, ShieldCheck, Shield, TrendingUp, Network } from 'lucide-react'

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

export const tabs = [
  { id: 'overview', label: 'Overview', icon: Activity },
  { id: 'heuristics', label: 'Heuristics', icon: Brain },
  { id: 'assumptions', label: 'Assumptions', icon: Lightbulb },
  { id: 'spikes', label: 'Spikes', icon: FileSearch },
  { id: 'invariants', label: 'Invariants', icon: ShieldCheck },
  { id: 'graph', label: 'Graph', icon: Network },
  { id: 'runs', label: 'Runs', icon: Workflow },
  { id: 'sessions', label: 'Sessions', icon: History },
  { id: 'timeline', label: 'Timeline', icon: Clock },
  { id: 'analytics', label: 'Analytics', icon: TrendingUp },
  { id: 'query', label: 'Query', icon: Search },
  { id: 'fraud', label: 'Fraud', icon: Shield },
] as const

export const priorityColors: Record<string, string> = {
  Critical: 'bg-red-500/20 text-red-400 border-red-500/30',
  High: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  Medium: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  Low: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
}
