import { Filter } from 'lucide-react'
import { InvariantFiltersProps, ScopeFilter, SeverityFilter, StatusFilter } from './types'

export default function InvariantFilters({
  scopeFilter,
  severityFilter,
  statusFilter,
  domainFilter,
  domains,
  onScopeChange,
  onSeverityChange,
  onStatusChange,
  onDomainChange,
}: InvariantFiltersProps) {
  return (
    <div className="flex items-center space-x-3">
      {/* Severity filter */}
      <div className="flex items-center space-x-2">
        <Filter className="w-4 h-4 text-slate-400" />
        <select
          value={severityFilter}
          onChange={(e) => onSeverityChange(e.target.value as SeverityFilter)}
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
        onChange={(e) => onScopeChange(e.target.value as ScopeFilter)}
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
        onChange={(e) => onStatusChange(e.target.value as StatusFilter)}
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
        onChange={(e) => onDomainChange(e.target.value)}
        className="bg-slate-700 text-sm text-white rounded-md px-3 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500"
      >
        <option value="all">All Domains</option>
        {domains.map(domain => (
          <option key={domain} value={domain}>{domain}</option>
        ))}
      </select>
    </div>
  )
}
