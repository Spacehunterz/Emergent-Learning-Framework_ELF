import { Star, TrendingUp, TrendingDown, ChevronDown, Brain, Shield, Award, AlertTriangle } from 'lucide-react'
import { Heuristic } from '../../types'
import { EditFormData, LifecycleInfo } from './types'
import LifecycleProgress from './LifecycleProgress'
import HeuristicEditForm from './HeuristicEditForm'
import HeuristicActions from './HeuristicActions'

interface HeuristicCardProps {
  heuristic: Heuristic
  isExpanded: boolean
  isEditing: boolean
  isDeleting: boolean
  editForm: EditFormData
  onToggleExpand: () => void
  onStartEdit: () => void
  onCancelEdit: () => void
  onSaveEdit: () => void
  onEditFormChange: (form: EditFormData) => void
  onPromote: () => void
  onDemote: () => void
  onStartDelete: () => void
  onConfirmDelete: () => void
  onCancelDelete: () => void
}

function getConfidenceColor(conf: number): string {
  if (conf >= 0.8) return 'text-emerald-400'
  if (conf >= 0.5) return 'text-yellow-400'
  return 'text-red-400'
}

function getLifecycleStage(h: Heuristic): LifecycleInfo {
  if (h.is_golden) return { stage: 'Golden', color: 'text-amber-400', icon: Award }
  if (h.confidence >= 0.9 && h.times_validated >= 10) return { stage: 'Promotion Ready', color: 'text-emerald-400', icon: TrendingUp }
  if (h.times_validated >= 5) return { stage: 'Validated', color: 'text-sky-400', icon: Shield }
  if (h.times_violated > h.times_validated) return { stage: 'At Risk', color: 'text-red-400', icon: AlertTriangle }
  return { stage: 'Learning', color: 'text-slate-400', icon: Brain }
}

export default function HeuristicCard({
  heuristic: h,
  isExpanded,
  isEditing,
  isDeleting,
  editForm,
  onToggleExpand,
  onStartEdit,
  onCancelEdit,
  onSaveEdit,
  onEditFormChange,
  onPromote,
  onDemote,
  onStartDelete,
  onConfirmDelete,
  onCancelDelete,
}: HeuristicCardProps) {
  const lifecycle = getLifecycleStage(h)
  const LifecycleIcon = lifecycle.icon

  return (
    <div
      className={`bg-slate-700/50 rounded-lg border transition-all
        ${h.is_golden ? 'border-amber-500/30' : 'border-transparent'}
        ${isExpanded ? 'ring-2 ring-sky-500/50' : ''}`}
    >
      {/* Main row */}
      <div className="p-3 cursor-pointer" onClick={onToggleExpand}>
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2 mb-1">
              {h.is_golden && <Star className="w-4 h-4 text-amber-400 flex-shrink-0" />}
              <span className="text-sm font-medium text-white truncate">{h.rule}</span>
            </div>
            <div className="flex items-center space-x-3 text-xs">
              <span className="px-2 py-0.5 rounded bg-slate-600 text-slate-300">{h.domain}</span>
              <span className={`flex items-center ${lifecycle.color}`}>
                <LifecycleIcon className="w-3 h-3 mr-1" />
                {lifecycle.stage}
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-4 flex-shrink-0 ml-4">
            {/* Confidence gauge */}
            <div className="text-center">
              <div className={`text-lg font-bold ${getConfidenceColor(h.confidence)}`}>
                {(h.confidence * 100).toFixed(0)}%
              </div>
              <div className="text-xs text-slate-500">confidence</div>
            </div>

            {/* Validation stats */}
            <div className="flex items-center space-x-2">
              <div className="text-center">
                <div className="flex items-center text-emerald-400">
                  <TrendingUp className="w-3 h-3 mr-1" />
                  <span className="font-medium">{h.times_validated}</span>
                </div>
                <div className="text-xs text-slate-500">validated</div>
              </div>
              <div className="text-center">
                <div className="flex items-center text-red-400">
                  <TrendingDown className="w-3 h-3 mr-1" />
                  <span className="font-medium">{h.times_violated}</span>
                </div>
                <div className="text-xs text-slate-500">violated</div>
              </div>
            </div>

            <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
          </div>
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="px-3 pb-3 border-t border-slate-600">
          <div className="pt-3 space-y-3">
            {h.explanation && (
              <div>
                <div className="text-xs text-slate-400 mb-1">Explanation</div>
                <div className="text-sm text-slate-300">{h.explanation}</div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-slate-400">Source:</span>
                <span className="text-white ml-2">{h.source_type}</span>
              </div>
              <div>
                <span className="text-slate-400">Created:</span>
                <span className="text-white ml-2">{new Date(h.created_at).toLocaleDateString()}</span>
              </div>
            </div>

            <LifecycleProgress heuristic={h} />

            {isEditing ? (
              <HeuristicEditForm
                editForm={editForm}
                onEditFormChange={onEditFormChange}
                onSave={onSaveEdit}
                onCancel={onCancelEdit}
              />
            ) : (
              <HeuristicActions
                heuristic={h}
                isDeleting={isDeleting}
                onPromote={onPromote}
                onDemote={onDemote}
                onStartEdit={onStartEdit}
                onStartDelete={onStartDelete}
                onConfirmDelete={onConfirmDelete}
                onCancelDelete={onCancelDelete}
              />
            )}
          </div>
        </div>
      )}
    </div>
  )
}
