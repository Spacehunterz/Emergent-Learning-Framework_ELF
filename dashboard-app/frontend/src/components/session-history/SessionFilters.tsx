import { Search, Filter, History } from 'lucide-react'
import { SessionFiltersProps } from './types'

export default function SessionFilters({
  searchQuery,
  onSearchChange,
  projectFilter,
  onProjectFilterChange,
  dateFilter,
  onDateFilterChange,
  projects,
  filteredCount,
  totalCount
}: SessionFiltersProps) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center space-x-2">
        <History className="w-5 h-5 text-sky-400" />
        <h3 className="text-lg font-semibold text-white">Sessions</h3>
        <span className="text-sm text-slate-400">({filteredCount} of {totalCount})</span>
      </div>

      <div className="flex items-center space-x-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search sessions..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="bg-slate-700 text-sm text-white rounded-lg pl-9 pr-4 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500 w-64"
          />
        </div>

        {/* Project filter */}
        <div className="flex items-center space-x-2">
          <Filter className="w-4 h-4 text-slate-400" />
          <select
            value={projectFilter}
            onChange={(e) => onProjectFilterChange(e.target.value)}
            className="bg-slate-700 text-sm text-white rounded-md px-3 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500"
          >
            <option value="all">All Projects</option>
            {projects.map(project => (
              <option key={project} value={project}>{project}</option>
            ))}
          </select>
        </div>

        {/* Date range filter */}
        <select
          value={dateFilter}
          onChange={(e) => onDateFilterChange(e.target.value as any)}
          className="bg-slate-700 text-sm text-white rounded-md px-3 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500"
        >
          <option value="today">Today</option>
          <option value="7days">Last 7 days</option>
          <option value="30days">Last 30 days</option>
          <option value="all">All time</option>
        </select>
      </div>
    </div>
  )
}
