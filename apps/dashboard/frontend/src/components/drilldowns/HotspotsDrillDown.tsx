import { DrillDownProps } from './types'

export default function HotspotsDrillDown({ data }: DrillDownProps) {
  const hotspots = data || []
  const totalTrails = hotspots.reduce((sum: number, h: any) => sum + (h.trail_count || 0), 0)
  const totalStrength = hotspots.reduce((sum: number, h: any) => sum + (h.total_strength || 0), 0)

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-orange-500/10 rounded-lg p-3 text-center">
          <div className="text-xl font-bold text-orange-400">{hotspots.length}</div>
          <div className="text-xs text-slate-400">Locations</div>
        </div>
        <div className="bg-red-500/10 rounded-lg p-3 text-center">
          <div className="text-xl font-bold text-red-400">{totalTrails}</div>
          <div className="text-xs text-slate-400">Trails</div>
        </div>
        <div className="bg-purple-500/10 rounded-lg p-3 text-center">
          <div className="text-xl font-bold text-purple-400">{totalStrength.toFixed(1)}</div>
          <div className="text-xs text-slate-400">Strength</div>
        </div>
      </div>
      <div className="max-h-64 overflow-y-auto space-y-2">
        {hotspots.length > 0 ? hotspots.slice(0, 20).map((h: any, idx: number) => (
          <div key={idx} className="bg-slate-700/50 rounded-lg p-3">
            <div className="text-sm text-white font-mono truncate" title={h.location}>{h.location}</div>
            <div className="flex items-center gap-3 mt-2 text-xs text-slate-400 flex-wrap">
              <span>Trails: {h.trail_count}</span>
              <span>Strength: {(h.total_strength || 0).toFixed(1)}</span>
              <span>Agents: {h.agent_count}</span>
            </div>
            {h.scents && h.scents.length > 0 && (
              <div className="flex gap-1 mt-2 flex-wrap">
                {h.scents.slice(0, 4).map((scent: string, i: number) => (
                  <span key={i} className="text-xs bg-slate-600 px-2 py-0.5 rounded text-slate-300">{scent}</span>
                ))}
              </div>
            )}
          </div>
        )) : (
          <div className="text-center text-slate-400 py-4">
            <p>No hotspots detected</p>
            <p className="text-xs text-slate-500 mt-1">Trails are recorded when agents work in the codebase</p>
          </div>
        )}
      </div>
    </div>
  )
}
