import { useState } from 'react'
import { ShieldCheck, Clock } from 'lucide-react'
import { InvariantsPanelProps, ScopeFilter, SeverityFilter, StatusFilter } from './types'
import { useInvariantsData } from './useInvariantsData'
import InvariantFilters from './InvariantFilters'
import InvariantCard from './InvariantCard'

export default function InvariantsPanel({ className = '' }: InvariantsPanelProps) {
  const [scopeFilter, setScopeFilter] = useState<ScopeFilter>('all')
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('all')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [domainFilter, setDomainFilter] = useState<string>('all')
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const {
    invariants,
    domains,
    loading,
    actionLoading,
    handleValidate,
    handleViolate,
  } = useInvariantsData(scopeFilter, severityFilter, statusFilter, domainFilter)

  return (
    <div className={`bg-slate-800 rounded-lg p-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <ShieldCheck className="w-5 h-5 text-emerald-400" />
          <h3 className="text-lg font-semibold text-white">Invariants</h3>
          <span className="text-sm text-slate-400">({invariants.length})</span>
        </div>

        <InvariantFilters
          scopeFilter={scopeFilter}
          severityFilter={severityFilter}
          statusFilter={statusFilter}
          domainFilter={domainFilter}
          domains={domains}
          onScopeChange={setScopeFilter}
          onSeverityChange={setSeverityFilter}
          onStatusChange={setStatusFilter}
          onDomainChange={setDomainFilter}
        />
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
          invariants.map(invariant => (
            <InvariantCard
              key={invariant.id}
              invariant={invariant}
              isExpanded={expandedId === invariant.id}
              isLoading={actionLoading === invariant.id}
              onToggle={() => setExpandedId(expandedId === invariant.id ? null : invariant.id)}
              onValidate={handleValidate}
              onViolate={handleViolate}
            />
          ))
        )}
      </div>
    </div>
  )
}
