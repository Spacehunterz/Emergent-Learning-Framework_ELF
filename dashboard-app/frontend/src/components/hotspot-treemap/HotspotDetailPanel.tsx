import { X } from 'lucide-react'
import type { ApiHotspot } from './types'

interface HotspotDetailPanelProps {
  hotspot: ApiHotspot | null
  onClose: () => void
}

export default function HotspotDetailPanel({ hotspot, onClose }: HotspotDetailPanelProps) {
  if (!hotspot) return null

  return (
    <div className="mt-4">
      <div className="bg-slate-900 border border-slate-700 rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-white font-medium">{hotspot.location}</h4>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-slate-400">Trail Count:</span>
            <span className="text-white ml-2">{hotspot.trail_count}</span>
          </div>
          <div>
            <span className="text-slate-400">Total Strength:</span>
            <span className="text-white ml-2">{hotspot.total_strength?.toFixed(2)}</span>
          </div>
          <div>
            <span className="text-slate-400">Agents:</span>
            <span className="text-white ml-2">{hotspot.agents?.join(', ') || 'none'}</span>
          </div>
          <div>
            <span className="text-slate-400">Scents:</span>
            <span className="text-white ml-2">{hotspot.scents?.join(', ') || 'none'}</span>
          </div>
          <div>
            <span className="text-slate-400">First Activity:</span>
            <span className="text-white ml-2">{new Date(hotspot.first_activity).toLocaleString()}</span>
          </div>
          <div>
            <span className="text-slate-400">Last Activity:</span>
            <span className="text-white ml-2">{new Date(hotspot.last_activity).toLocaleString()}</span>
          </div>
        </div>
        {hotspot.related_heuristics?.length > 0 && (
          <div className="mt-3 pt-3 border-t border-slate-700">
            <span className="text-slate-400 text-sm">Related Heuristics:</span>
            <div className="mt-1 space-y-1">
              {hotspot.related_heuristics.map((h, i) => (
                <div key={i} className="text-xs text-slate-300 bg-slate-800 rounded px-2 py-1">
                  {typeof h === 'object' ? (h.rule || JSON.stringify(h)) : String(h)}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
