import { Search, Filter } from 'lucide-react'
import { SpikeReportFiltersProps } from './types'

export default function SpikeReportFilters({
  searchQuery,
  domainFilter,
  tagFilter,
  domains,
  tags,
  onSearchChange,
  onDomainChange,
  onTagChange,
}: SpikeReportFiltersProps) {
  return (
    <div className="flex items-center space-x-4">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input
          type="text"
          placeholder="Search findings..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="bg-slate-700 text-sm text-white rounded-lg pl-9 pr-4 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500 w-64"
        />
      </div>

      <div className="flex items-center space-x-2">
        <Filter className="w-4 h-4 text-slate-400" />
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

      <select
        value={tagFilter}
        onChange={(e) => onTagChange(e.target.value)}
        className="bg-slate-700 text-sm text-white rounded-md px-3 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500"
      >
        <option value="all">All Tags</option>
        {tags.map(tag => (
          <option key={tag} value={tag}>{tag}</option>
        ))}
      </select>
    </div>
  )
}
