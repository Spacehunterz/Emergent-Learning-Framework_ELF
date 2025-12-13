import { Heuristic } from '../../types'

interface LifecycleProgressProps {
  heuristic: Heuristic
}

export default function LifecycleProgress({ heuristic: h }: LifecycleProgressProps) {
  return (
    <div className="mt-3">
      <div className="text-xs text-slate-400 mb-2">Lifecycle Progress</div>
      <div className="flex items-center space-x-1">
        <div className={`h-2 flex-1 rounded-l ${h.times_validated > 0 ? 'bg-sky-500' : 'bg-slate-600'}`} />
        <div className={`h-2 flex-1 ${h.times_validated >= 5 ? 'bg-sky-500' : 'bg-slate-600'}`} />
        <div className={`h-2 flex-1 ${h.confidence >= 0.9 && h.times_validated >= 10 ? 'bg-emerald-500' : 'bg-slate-600'}`} />
        <div className={`h-2 flex-1 rounded-r ${h.is_golden ? 'bg-amber-500' : 'bg-slate-600'}`} />
      </div>
      <div className="flex justify-between text-xs text-slate-500 mt-1">
        <span>Learning</span>
        <span>Validated</span>
        <span>Ready</span>
        <span>Golden</span>
      </div>
    </div>
  )
}
