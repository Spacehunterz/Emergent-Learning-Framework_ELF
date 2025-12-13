import { Workflow, Search, Filter } from 'lucide-react'
import { RunsFiltersProps } from './types'

export default function RunsFilters({
  searchQuery,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  filteredCount,
  totalCount
}: RunsFiltersProps) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center space-x-2">
        <Workflow className="w-5 h-5 text-indigo-400" />
        <h3 className="text-lg font-semibold text-white">Agent Runs</h3>
        <span className="text-sm text-slate-400">({filteredCount} of {totalCount})</span>
      </div>

      <div className="flex items-center space-x-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search runs..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="bg-slate-700 text-sm text-white rounded-lg pl-9 pr-4 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500 w-64"
          />
        </div>

        {/* Status filter */}
        <div className="flex items-center space-x-2">
          <Filter className="w-4 h-4 text-slate-400" />
          <select
            value={statusFilter}
            onChange={(e) => onStatusFilterChange(e.target.value as any)}
            className="bg-slate-700 text-sm text-white rounded-md px-3 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500"
          >
            <option value="all">All Status</option>
            <option value="success">Success</option>
            <option value="failure">Failure</option>
            <option value="running">Running</option>
          </select>
        </div>
      </div>
    </div>
  )
}
