import { Filter } from 'lucide-react'
import { AssumptionFiltersProps } from './types'

export default function AssumptionFilters({
  statusFilter,
  domainFilter,
  minConfidence,
  domains,
  onStatusChange,
  onDomainChange,
  onConfidenceChange,
}: AssumptionFiltersProps) {
  return (
    <div className="flex items-center space-x-4">
      <div className="flex items-center space-x-2">
        <Filter className="w-4 h-4 text-slate-400" />
        <select
          value={statusFilter}
          onChange={(e) => onStatusChange(e.target.value as any)}
          className="bg-slate-700 text-sm text-white rounded-md px-3 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500"
        >
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="verified">Verified</option>
          <option value="challenged">Challenged</option>
          <option value="invalidated">Invalidated</option>
        </select>
      </div>

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

      <div className="flex items-center space-x-2">
        <span className="text-xs text-slate-400">Min:</span>
        <input
          type="range"
          min="0"
          max="100"
          value={minConfidence}
          onChange={(e) => onConfidenceChange(Number(e.target.value))}
          className="w-24 accent-sky-500"
        />
        <span className="text-xs text-white w-8">{minConfidence}%</span>
      </div>
    </div>
  )
}
