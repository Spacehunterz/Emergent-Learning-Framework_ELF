import { Filter } from 'lucide-react'

interface TreemapFiltersProps {
  selectedDomain: string | null
  domains: string[]
  onDomainFilter: (domain: string | null) => void
}

export default function TreemapFilters({ selectedDomain, domains, onDomainFilter }: TreemapFiltersProps) {
  return (
    <div className="flex items-center space-x-2">
      <Filter className="w-4 h-4 text-slate-400" />
      <select
        value={selectedDomain || ''}
        onChange={(e) => onDomainFilter(e.target.value || null)}
        className="bg-slate-700 text-sm text-white rounded-md px-3 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500"
      >
        <option value="">All Scents</option>
        {domains.map((domain, idx) => (
          <option key={`${domain}-${idx}`} value={domain}>{domain}</option>
        ))}
      </select>
    </div>
  )
}
