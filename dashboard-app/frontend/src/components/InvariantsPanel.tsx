import { useState, useEffect } from 'react'
import { Invariant } from '../types'
import { ShieldCheck, Filter, ChevronDown, Clock, AlertTriangle, AlertOctagon, Info, CheckCircle, XCircle, Archive, Code } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { useAPI } from '../hooks/useAPI'

type ScopeFilter = 'all' | 'codebase' | 'module' | 'function' | 'runtime'
type SeverityFilter = 'all' | 'error' | 'warning' | 'info'
type StatusFilter = 'all' | 'active' | 'deprecated' | 'violated'

interface InvariantsPanelProps {
  className?: string
}

export default function InvariantsPanel({ className = '' }: InvariantsPanelProps) {
  const api = useAPI()

  const [invariants, setInvariants] = useState<Invariant[]>([])
  const [domains, setDomains] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [scopeFilter, setScopeFilter] = useState<ScopeFilter>('all')
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('all')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [domainFilter, setDomainFilter] = useState<string>('all')
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [actionLoading, setActionLoading] = useState<number | null>(null)

  // Load invariants
  useEffect(() => {
    loadInvariants()
  }, [scopeFilter, severityFilter, statusFilter, domainFilter])

  const loadInvariants = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (scopeFilter !== 'all') params.append('scope', scopeFilter)
      if (severityFilter !== 'all') params.append('severity', severityFilter)
      if (statusFilter !== 'all') params.append('status', statusFilter)
      if (domainFilter !== 'all') params.append('domain', domainFilter)

      const data = await api.get(`/api/invariants?${params.toString()}`)
      setInvariants(data || [])

      // Extract unique domains
      const uniqueDomains = Array.from(new Set(data?.map((i: Invariant) => i.domain).filter(Boolean))) as string[]
      setDomains(uniqueDomains)
    } catch (err) {
      console.error('Failed to load invariants:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleValidate = async (id: number) => {
    setActionLoading(id)
    try {
      await api.post(`/api/invariants/${id}/validate`)
      // Update locally
      setInvariants(prev => prev.map(i =>
        i.id === id
          ? { ...i, status: 'active' as const, last_validated_at: new Date().toISOString() }
          : i
      ))
    } catch (err) {
      console.error('Failed to validate invariant:', err)
    } finally {
      setActionLoading(null)
    }
  }

  const handleViolate = async (id: number) => {
    setActionLoading(id)
    try {
      await api.post(`/api/invariants/${id}/violate`)
      // Update locally
      setInvariants(prev => prev.map(i =>
        i.id === id
          ? { ...i, status: 'violated' as const, violation_count: i.violation_count + 1, last_violated_at: new Date().toISOString() }
          : i
      ))
    } catch (err) {
      console.error('Failed to record violation:', err)
    } finally {
      setActionLoading(null)
    }
  }

  const getSeverityBadge = (severity: Invariant['severity']) => {
    switch (severity) {
      case 'error':
        return (
          <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-red-500/20 text-red-400 text-xs">
            <AlertOctagon className="w-3 h-3" />
            <span>Error</span>
          </span>
        )
      case 'warning':
        return (
          <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 text-xs">
            <AlertTriangle className="w-3 h-3" />
            <span>Warning</span>
          </span>
        )
      default:
        return (
          <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-sky-500/20 text-sky-400 text-xs">
            <Info className="w-3 h-3" />
            <span>Info</span>
          </span>
        )
    }
  }

  const getStatusBadge = (status: Invariant['status']) => {
    switch (status) {
      case 'violated':
        return (
          <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-red-500/20 text-red-400 text-xs">
            <XCircle className="w-3 h-3" />
            <span>Violated</span>
          </span>
        )
      case 'deprecated':
        return (
          <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-slate-500/20 text-slate-400 text-xs">
            <Archive className="w-3 h-3" />
            <span>Deprecated</span>
          </span>
        )
      default:
        return (
          <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 text-xs">
            <CheckCircle className="w-3 h-3" />
            <span>Active</span>
          </span>
        )
    }
  }

  const getScopeBadge = (scope: Invariant['scope']) => {
    const colors: Record<string, string> = {
      codebase: 'bg-violet-500/20 text-violet-400',
      module: 'bg-sky-500/20 text-sky-400',
      function: 'bg-emerald-500/20 text-emerald-400',
      runtime: 'bg-amber-500/20 text-amber-400',
    }

    return (
      <span className={`px-2 py-0.5 rounded text-xs ${colors[scope] || 'bg-slate-500/20 text-slate-400'}`}>
        {scope}
      </span>
    )
  }

  return (
    <div className={`bg-slate-800 rounded-lg p-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <ShieldCheck className="w-5 h-5 text-emerald-400" />
          <h3 className="text-lg font-semibold text-white">Invariants</h3>
          <span className="text-sm text-slate-400">({invariants.length})</span>
        </div>

        <div className="flex items-center space-x-3">
          {/* Severity filter */}
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value as SeverityFilter)}
              className="bg-slate-700 text-sm text-white rounded-md px-3 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500"
            >
              <option value="all">All Severity</option>
              <option value="error">Error</option>
              <option value="warning">Warning</option>
              <option value="info">Info</option>
            </select>
          </div>

          {/* Scope filter */}
          <select
            value={scopeFilter}
            onChange={(e) => setScopeFilter(e.target.value as ScopeFilter)}
            className="bg-slate-700 text-sm text-white rounded-md px-3 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500"
          >
            <option value="all">All Scopes</option>
            <option value="codebase">Codebase</option>
            <option value="module">Module</option>
            <option value="function">Function</option>
            <option value="runtime">Runtime</option>
          </select>

          {/* Status filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
            className="bg-slate-700 text-sm text-white rounded-md px-3 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="violated">Violated</option>
            <option value="deprecated">Deprecated</option>
          </select>

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
        </div>
      </div>

      {/* Invariants list */}
      <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2">
        {loading ? (
          <div className="text-center text-slate-400 py-12">
            <Clock className="w-8 h-8 mx-auto mb-2 animate-spin" />
            Loading invariants...
          </div>
        ) : invariants.length === 0 ? (
          <div className="text-center text-slate-400 py-12">
            No invariants found
          </div>
        ) : (
          invariants.map(invariant => {
            const isExpanded = expandedId === invariant.id
            const isLoading = actionLoading === invariant.id

            return (
              <div
                key={invariant.id}
                className={`bg-slate-700/50 rounded-lg border transition-all
                  ${invariant.status === 'violated' ? 'border-red-500/30' : 'border-transparent'}
                  ${isExpanded ? 'ring-2 ring-emerald-500/50' : ''}`}
              >
                {/* Main row */}
                <div
                  className="p-3 cursor-pointer hover:bg-slate-700/70 transition-colors"
                  onClick={() => setExpandedId(isExpanded ? null : invariant.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-2 flex-wrap gap-1">
                        {getSeverityBadge(invariant.severity)}
                        {getStatusBadge(invariant.status)}
                        {getScopeBadge(invariant.scope)}
                        {invariant.domain && (
                          <span className="px-2 py-0.5 rounded bg-slate-600 text-xs text-slate-300">
                            {invariant.domain}
                          </span>
                        )}
                      </div>
                      <div className="text-sm font-medium text-white">
                        {invariant.statement}
                      </div>
                    </div>

                    <div className="flex items-center space-x-4 flex-shrink-0 ml-4">
                      {/* Violation count */}
                      {invariant.violation_count > 0 && (
                        <div className="flex items-center space-x-1 px-2 py-1 bg-red-500/20 rounded text-red-400 text-xs">
                          <XCircle className="w-3 h-3" />
                          <span>{invariant.violation_count} violations</span>
                        </div>
                      )}

                      {/* Validation type */}
                      {invariant.validation_type && (
                        <span className="text-xs text-slate-400">
                          {invariant.validation_type}
                        </span>
                      )}

                      <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                    </div>
                  </div>
                </div>

                {/* Expanded content */}
                {isExpanded && (
                  <div className="px-3 pb-3 border-t border-slate-600">
                    <div className="pt-3 space-y-3">
                      {/* Rationale */}
                      <div>
                        <div className="text-xs text-slate-400 mb-1">Rationale</div>
                        <div className="text-sm text-slate-300 bg-slate-800/50 rounded p-2">
                          {invariant.rationale}
                        </div>
                      </div>

                      {/* Validation code */}
                      {invariant.validation_code && (
                        <div>
                          <div className="flex items-center space-x-2 text-xs text-slate-400 mb-1">
                            <Code className="w-3 h-3" />
                            <span>Validation Code</span>
                          </div>
                          <pre className="text-xs text-slate-300 bg-slate-900 rounded p-2 overflow-x-auto">
                            {invariant.validation_code}
                          </pre>
                        </div>
                      )}

                      {/* Metadata */}
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-slate-400">Created:</span>
                          <span className="text-white ml-2">
                            {formatDistanceToNow(new Date(invariant.created_at), { addSuffix: true })}
                          </span>
                        </div>
                        {invariant.last_validated_at && (
                          <div>
                            <span className="text-slate-400">Last Validated:</span>
                            <span className="text-white ml-2">
                              {formatDistanceToNow(new Date(invariant.last_validated_at), { addSuffix: true })}
                            </span>
                          </div>
                        )}
                        {invariant.last_violated_at && (
                          <div>
                            <span className="text-slate-400">Last Violated:</span>
                            <span className="text-red-400 ml-2">
                              {formatDistanceToNow(new Date(invariant.last_violated_at), { addSuffix: true })}
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="flex items-center space-x-2 pt-2">
                        <button
                          onClick={(e) => { e.stopPropagation(); handleValidate(invariant.id) }}
                          disabled={isLoading}
                          className="flex items-center space-x-1 px-3 py-1.5 bg-emerald-500/20 text-emerald-400 rounded-lg text-sm hover:bg-emerald-500/30 transition disabled:opacity-50"
                        >
                          <CheckCircle className="w-4 h-4" />
                          <span>Validate</span>
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleViolate(invariant.id) }}
                          disabled={isLoading}
                          className="flex items-center space-x-1 px-3 py-1.5 bg-red-500/20 text-red-400 rounded-lg text-sm hover:bg-red-500/30 transition disabled:opacity-50"
                        >
                          <XCircle className="w-4 h-4" />
                          <span>Record Violation</span>
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
