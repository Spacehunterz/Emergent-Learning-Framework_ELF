import { ZoomIn, ZoomOut, Maximize2, Filter } from 'lucide-react'
import { GraphData } from './types'

interface GraphControlsProps {
  graphData: GraphData
  showGoldenOnly: boolean
  filterDomain: string | null
  onShowGoldenToggle: () => void
  onDomainFilter: (domain: string | null) => void
  onZoomIn: () => void
  onZoomOut: () => void
  onResetZoom: () => void
}

export default function GraphControls({
  graphData,
  showGoldenOnly,
  filterDomain,
  onShowGoldenToggle,
  onDomainFilter,
  onZoomIn,
  onZoomOut,
  onResetZoom,
}: GraphControlsProps) {
  const domains = Array.from(new Set(graphData.nodes.map(n => n.domain)))

  return (
    <div className="glass-panel p-4">
      <div className="flex items-center justify-between flex-wrap gap-4">
        {/* Stats */}
        <div className="flex items-center space-x-6 text-sm">
          <div>
            <span className="text-slate-400">Nodes:</span>
            <span className="ml-2 font-semibold" style={{ color: 'var(--theme-accent)' }}>
              {graphData.stats.total_nodes}
            </span>
          </div>
          <div>
            <span className="text-slate-400">Edges:</span>
            <span className="ml-2 font-semibold text-blue-400">
              {graphData.stats.total_edges}
            </span>
          </div>
          <div>
            <span className="text-slate-400">Golden:</span>
            <span className="ml-2 font-semibold text-amber-400">
              {graphData.stats.golden_rules}
            </span>
          </div>
          <div>
            <span className="text-slate-400">Domains:</span>
            <span className="ml-2 font-semibold text-emerald-400">
              {graphData.stats.domains}
            </span>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center space-x-2">
          <button
            onClick={onShowGoldenToggle}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              showGoldenOnly
                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                : 'bg-white/5 text-slate-400 hover:text-white hover:bg-white/10'
            }`}
          >
            Golden Only
          </button>

          <div className="relative">
            <select
              value={filterDomain || ''}
              onChange={(e) => onDomainFilter(e.target.value || null)}
              className="px-3 py-1.5 rounded-lg text-sm font-medium bg-white/5 text-slate-300 border border-white/10 hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-purple-500/50 appearance-none pr-8"
            >
              <option value="">All Domains</option>
              {domains.map(domain => (
                <option key={domain} value={domain}>{domain}</option>
              ))}
            </select>
            <Filter className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          </div>
        </div>

        {/* Zoom controls */}
        <div className="flex items-center space-x-2">
          <button
            onClick={onZoomIn}
            className="p-2 rounded-lg bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 transition-all"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={onZoomOut}
            className="p-2 rounded-lg bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 transition-all"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={onResetZoom}
            className="p-2 rounded-lg bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 transition-all"
            title="Reset View"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
