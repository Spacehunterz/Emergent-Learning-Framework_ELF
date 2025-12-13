import { Brain, Star, Filter, ChevronDown, ChevronUp } from 'lucide-react'
import { SortField, SortDir } from './types'

interface HeuristicFiltersProps {
  totalCount: number
  filteredCount: number
  domains: string[]
  selectedDomain: string | null
  showGoldenOnly: boolean
  sortField: SortField
  sortDir: SortDir
  onDomainFilter: (domain: string | null) => void
  onToggleGoldenOnly: () => void
  onToggleSort: (field: SortField) => void
}

function SortButton({
  field,
  label,
  sortField,
  sortDir,
  onToggleSort,
}: {
  field: SortField
  label: string
  sortField: SortField
  sortDir: SortDir
  onToggleSort: (field: SortField) => void
}) {
  return (
    <button
      onClick={() => onToggleSort(field)}
      className={`flex items-center space-x-1 text-xs font-medium px-2 py-1 rounded
        ${sortField === field ? 'bg-sky-500/20 text-sky-400' : 'text-slate-400 hover:text-white'}`}
    >
      <span>{label}</span>
      {sortField === field && (
        sortDir === 'desc' ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />
      )}
    </button>
  )
}

export default function HeuristicFilters({
  totalCount,
  filteredCount,
  domains,
  selectedDomain,
  showGoldenOnly,
  sortField,
  sortDir,
  onDomainFilter,
  onToggleGoldenOnly,
  onToggleSort,
}: HeuristicFiltersProps) {
  return (
    <>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Brain className="w-5 h-5 text-violet-400" />
          <h3 className="text-lg font-semibold text-white">Heuristics</h3>
          <span className="text-sm text-slate-400">({filteredCount} of {totalCount})</span>
        </div>

        <div className="flex items-center space-x-4">
          {/* Golden only toggle */}
          <button
            onClick={onToggleGoldenOnly}
            className={`flex items-center space-x-1 px-3 py-1.5 rounded-lg text-sm
              ${showGoldenOnly ? 'bg-amber-500/20 text-amber-400' : 'bg-slate-700 text-slate-400 hover:text-white'}`}
          >
            <Star className="w-4 h-4" />
            <span>Golden Only</span>
          </button>

          {/* Domain filter */}
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <select
              value={selectedDomain || ''}
              onChange={(e) => onDomainFilter(e.target.value || null)}
              className="bg-slate-700 text-sm text-white rounded-md px-3 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500"
            >
              <option value="">All Domains</option>
              {domains.map(domain => (
                <option key={domain} value={domain}>{domain}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Sort controls */}
      <div className="flex items-center space-x-2 mb-4">
        <span className="text-xs text-slate-500">Sort by:</span>
        <SortButton field="confidence" label="Confidence" sortField={sortField} sortDir={sortDir} onToggleSort={onToggleSort} />
        <SortButton field="validated" label="Validations" sortField={sortField} sortDir={sortDir} onToggleSort={onToggleSort} />
        <SortButton field="created" label="Created" sortField={sortField} sortDir={sortDir} onToggleSort={onToggleSort} />
        <SortButton field="domain" label="Domain" sortField={sortField} sortDir={sortDir} onToggleSort={onToggleSort} />
      </div>
    </>
  )
}
