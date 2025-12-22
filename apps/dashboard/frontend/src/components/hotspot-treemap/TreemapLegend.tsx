export default function TreemapLegend() {
  return (
    <div className="flex items-center space-x-4 mb-4 text-xs">
      <div className="flex items-center space-x-1">
        <div className="w-3 h-3 rounded bg-emerald-500" />
        <span className="text-slate-400">Low</span>
      </div>
      <div className="flex items-center space-x-1">
        <div className="w-3 h-3 rounded bg-yellow-500" />
        <span className="text-slate-400">Medium</span>
      </div>
      <div className="flex items-center space-x-1">
        <div className="w-3 h-3 rounded bg-orange-500" />
        <span className="text-slate-400">High</span>
      </div>
      <div className="flex items-center space-x-1">
        <div className="w-3 h-3 rounded bg-red-500" />
        <span className="text-slate-400">Critical</span>
      </div>
    </div>
  )
}
