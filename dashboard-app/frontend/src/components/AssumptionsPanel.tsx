import { useState, useEffect } from 'react'
import { Assumption } from '../types'
import { Lightbulb, Search, Filter, ChevronDown, CheckCircle, AlertTriangle, XCircle, Clock, ThumbsUp, HelpCircle } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { useAPI } from '../hooks/useAPI'

type StatusFilter = 'all' | 'active' | 'verified' | 'challenged' | 'invalidated'

interface AssumptionsPanelProps {
  className?: string
}

export default function AssumptionsPanel({ className = '' }: AssumptionsPanelProps) {
  const api = useAPI()

  const [assumptions, setAssumptions] = useState<Assumption[]>([])
  const [domains, setDomains] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [domainFilter, setDomainFilter] = useState<string>('all')
  const [minConfidence, setMinConfidence] = useState<number>(0)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [actionLoading, setActionLoading] = useState<number | null>(null)

  // Load assumptions
  useEffect(() => {
    loadAssumptions()
  }, [statusFilter, domainFilter, minConfidence])

  const loadAssumptions = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (statusFilter !== 'all') params.append('status', statusFilter)
      if (domainFilter !== 'all') params.append('domain', domainFilter)
      if (minConfidence > 0) params.append('min_confidence', (minConfidence / 100).toString())

      const data = await api.get(`/api/assumptions?${params.toString()}`)
      setAssumptions(data || [])

      // Extract unique domains
      const uniqueDomains = Array.from(new Set(data?.map((a: Assumption) => a.domain).filter(Boolean))) as string[]
      setDomains(uniqueDomains)
    } catch (err) {
      console.error('Failed to load assumptions:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleVerify = async (id: number) => {
    setActionLoading(id)
    try {
      await api.post(`/api/assumptions/${id}/verify`)
      // Update locally
      setAssumptions(prev => prev.map(a =>
        a.id === id
          ? { ...a, verified_count: a.verified_count + 1, status: 'verified' as const, last_verified_at: new Date().toISOString() }
          : a
      ))
    } catch (err) {
      console.error('Failed to verify assumption:', err)
    } finally {
      setActionLoading(null)
    }
  }

  const handleChallenge = async (id: number) => {
    setActionLoading(id)
    try {
      await api.post(`/api/assumptions/${id}/challenge`)
      // Update locally
      setAssumptions(prev => prev.map(a =>
        a.id === id
          ? { ...a, challenged_count: a.challenged_count + 1, status: 'challenged' as const }
          : a
      ))
    } catch (err) {
      console.error('Failed to challenge assumption:', err)
    } finally {
      setActionLoading(null)
    }
  }

  const getStatusBadge = (status: Assumption['status']) => {
    switch (status) {
      case 'verified':
        return (
          <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 text-xs">
            <CheckCircle className="w-3 h-3" />
            <span>Verified</span>
          </span>
        )
      case 'challenged':
        return (
          <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 text-xs">
            <AlertTriangle className="w-3 h-3" />
            <span>Challenged</span>
          </span>
        )
      case 'invalidated':
        return (
          <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-red-500/20 text-red-400 text-xs">
            <XCircle className="w-3 h-3" />
            <span>Invalidated</span>
          </span>
        )
      default:
        return (
          <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-sky-500/20 text-sky-400 text-xs">
            <Lightbulb className="w-3 h-3" />
            <span>Active</span>
          </span>
        )
    }
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-emerald-500'
    if (confidence >= 0.5) return 'bg-amber-500'
    return 'bg-red-500'
  }

  return (
    <div className={`bg-slate-800 rounded-lg p-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Lightbulb className="w-5 h-5 text-amber-400" />
          <h3 className="text-lg font-semibold text-white">Assumptions</h3>
          <span className="text-sm text-slate-400">({assumptions.length})</span>
        </div>

        <div className="flex items-center space-x-4">
          {/* Status filter */}
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
              className="bg-slate-700 text-sm text-white rounded-md px-3 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500"
            >
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="verified">Verified</option>
              <option value="challenged">Challenged</option>
              <option value="invalidated">Invalidated</option>
            </select>
          </div>

          {/* Domain filter */}
          <select
            value={domainFilter}
            onChange={(e) => setDomainFilter(e.target.value)}
            className="bg-slate-700 text-sm text-white rounded-md px-3 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500"
          >
            <option value="all">All Domains</option>
            {domains.map(domain => (
              <option key={domain} value={domain}>{domain}</option>
            ))}
          </select>

          {/* Min confidence slider */}
          <div className="flex items-center space-x-2">
            <span className="text-xs text-slate-400">Min:</span>
            <input
              type="range"
              min="0"
              max="100"
              value={minConfidence}
              onChange={(e) => setMinConfidence(Number(e.target.value))}
              className="w-24 accent-sky-500"
            />
            <span className="text-xs text-white w-8">{minConfidence}%</span>
          </div>
        </div>
      </div>

      {/* Assumptions list */}
      <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2">
        {loading ? (
          <div className="text-center text-slate-400 py-12">
            <Clock className="w-8 h-8 mx-auto mb-2 animate-spin" />
            Loading assumptions...
          </div>
        ) : assumptions.length === 0 ? (
          <div className="text-center text-slate-400 py-12">
            No assumptions found
          </div>
        ) : (
          assumptions.map(assumption => {
            const isExpanded = expandedId === assumption.id
            const isLoading = actionLoading === assumption.id

            return (
              <div
                key={assumption.id}
                className={`bg-slate-700/50 rounded-lg border border-transparent transition-all
                  ${isExpanded ? 'ring-2 ring-sky-500/50' : ''}`}
              >
                {/* Main row */}
                <div
                  className="p-3 cursor-pointer hover:bg-slate-700/70 transition-colors"
                  onClick={() => setExpandedId(isExpanded ? null : assumption.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-1">
                        {getStatusBadge(assumption.status)}
                        {assumption.domain && (
                          <span className="px-2 py-0.5 rounded bg-slate-600 text-xs text-slate-300">
                            {assumption.domain}
                          </span>
                        )}
                      </div>
                      <div className="text-sm font-medium text-white">
                        {assumption.assumption}
                      </div>
                      {assumption.source && (
                        <div className="text-xs text-slate-400 mt-1">
                          Source: {assumption.source}
                        </div>
                      )}
                    </div>

                    <div className="flex items-center space-x-4 flex-shrink-0 ml-4">
                      {/* Confidence bar */}
                      <div className="w-24">
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span className="text-slate-400">Confidence</span>
                          <span className="text-white font-medium">{Math.round(assumption.confidence * 100)}%</span>
                        </div>
                        <div className="h-2 bg-slate-600 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${getConfidenceColor(assumption.confidence)} transition-all`}
                            style={{ width: `${assumption.confidence * 100}%` }}
                          />
                        </div>
                      </div>

                      {/* Verification stats */}
                      <div className="flex items-center space-x-3 text-xs">
                        <div className="flex items-center space-x-1 text-emerald-400">
                          <ThumbsUp className="w-3 h-3" />
                          <span>{assumption.verified_count}</span>
                        </div>
                        <div className="flex items-center space-x-1 text-amber-400">
                          <HelpCircle className="w-3 h-3" />
                          <span>{assumption.challenged_count}</span>
                        </div>
                      </div>

                      <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                    </div>
                  </div>
                </div>

                {/* Expanded content */}
                {isExpanded && (
                  <div className="px-3 pb-3 border-t border-slate-600">
                    <div className="pt-3 space-y-3">
                      {/* Context */}
                      <div>
                        <div className="text-xs text-slate-400 mb-1">Context</div>
                        <div className="text-sm text-slate-300 bg-slate-800/50 rounded p-2">
                          {assumption.context}
                        </div>
                      </div>

                      {/* Metadata */}
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-slate-400">Created:</span>
                          <span className="text-white ml-2">
                            {formatDistanceToNow(new Date(assumption.created_at), { addSuffix: true })}
                          </span>
                        </div>
                        {assumption.last_verified_at && (
                          <div>
                            <span className="text-slate-400">Last Verified:</span>
                            <span className="text-white ml-2">
                              {formatDistanceToNow(new Date(assumption.last_verified_at), { addSuffix: true })}
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="flex items-center space-x-2 pt-2">
                        <button
                          onClick={(e) => { e.stopPropagation(); handleVerify(assumption.id) }}
                          disabled={isLoading}
                          className="flex items-center space-x-1 px-3 py-1.5 bg-emerald-500/20 text-emerald-400 rounded-lg text-sm hover:bg-emerald-500/30 transition disabled:opacity-50"
                        >
                          <CheckCircle className="w-4 h-4" />
                          <span>Verify</span>
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleChallenge(assumption.id) }}
                          disabled={isLoading}
                          className="flex items-center space-x-1 px-3 py-1.5 bg-amber-500/20 text-amber-400 rounded-lg text-sm hover:bg-amber-500/30 transition disabled:opacity-50"
                        >
                          <AlertTriangle className="w-4 h-4" />
                          <span>Challenge</span>
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
