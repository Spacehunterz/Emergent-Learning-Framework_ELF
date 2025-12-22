export default function GraphLegend() {
  return (
    <div className="absolute bottom-4 left-4 glass-panel p-3 text-xs space-y-2">
      <div className="font-semibold text-white mb-2">Legend</div>
      <div className="flex items-center space-x-2">
        <div className="w-4 h-4 rounded-full bg-purple-500 border-2 border-amber-400"></div>
        <span className="text-slate-300">Golden Rule</span>
      </div>
      <div className="flex items-center space-x-2">
        <div className="w-3 h-3 rounded-full bg-blue-500"></div>
        <span className="text-slate-300">Regular Heuristic</span>
      </div>
      <div className="flex items-center space-x-2">
        <div className="w-8 h-0.5 bg-slate-500"></div>
        <span className="text-slate-300">Same Domain</span>
      </div>
      <div className="flex items-center space-x-2">
        <div className="w-8 h-0.5 bg-slate-600 opacity-50"></div>
        <span className="text-slate-300">Related Concepts</span>
      </div>
    </div>
  )
}
