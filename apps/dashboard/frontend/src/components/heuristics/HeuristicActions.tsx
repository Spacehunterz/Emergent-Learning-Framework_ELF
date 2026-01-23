import { Star, TrendingDown, Edit2, Trash2, X, Eye } from 'lucide-react'
import { Heuristic } from '../../types'

interface HeuristicActionsProps {
  heuristic: Heuristic
  isDeleting: boolean
  onPromote: () => void
  onDemote: () => void
  onStartEdit: () => void
  onStartDelete: () => void
  onConfirmDelete: () => void
  onCancelDelete: () => void
  onViewDetails?: () => void
}

export default function HeuristicActions({
  heuristic: h,
  isDeleting,
  onPromote,
  onDemote,
  onStartEdit,
  onStartDelete,
  onConfirmDelete,
  onCancelDelete,
  onViewDetails,
}: HeuristicActionsProps) {
  if (isDeleting) {
    return (
      <div className="flex items-center space-x-3 pt-2 border-t border-red-500/30 mt-2">
        <span className="text-sm text-red-400">Delete this heuristic?</span>
        <button
          onClick={(e) => { e.stopPropagation(); onConfirmDelete() }}
          className="flex items-center space-x-1 px-3 py-1.5 bg-red-500/20 text-red-400 rounded-lg text-sm hover:bg-red-500/30 transition"
        >
          <Trash2 className="w-4 h-4" />
          <span>Yes, Delete</span>
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onCancelDelete() }}
          className="flex items-center space-x-1 px-3 py-1.5 bg-slate-600 text-slate-300 rounded-lg text-sm hover:bg-slate-500 transition"
        >
          <X className="w-4 h-4" />
          <span>Cancel</span>
        </button>
      </div>
    )
  }

  return (
    <div className="flex items-center flex-wrap gap-2 pt-2">
      {onViewDetails && (
        <button
          onClick={(e) => { e.stopPropagation(); onViewDetails() }}
          className="flex items-center space-x-1 px-3 py-1.5 bg-purple-500/20 text-purple-400 rounded-lg text-sm hover:bg-purple-500/30 transition"
        >
          <Eye className="w-4 h-4" />
          <span>View Details</span>
        </button>
      )}
      {!h.is_golden && h.confidence >= 0.8 && (
        <button
          onClick={(e) => { e.stopPropagation(); onPromote() }}
          className="flex items-center space-x-1 px-3 py-1.5 bg-amber-500/20 text-amber-400 rounded-lg text-sm hover:bg-amber-500/30 transition"
        >
          <Star className="w-4 h-4" />
          <span>Promote to Golden</span>
        </button>
      )}
      {h.is_golden && (
        <button
          onClick={(e) => { e.stopPropagation(); onDemote() }}
          className="flex items-center space-x-1 px-3 py-1.5 bg-slate-600 text-slate-300 rounded-lg text-sm hover:bg-slate-500 transition"
        >
          <TrendingDown className="w-4 h-4" />
          <span>Demote from Golden</span>
        </button>
      )}
      <button
        onClick={(e) => { e.stopPropagation(); onStartEdit() }}
        className="flex items-center space-x-1 px-3 py-1.5 bg-sky-500/20 text-sky-400 rounded-lg text-sm hover:bg-sky-500/30 transition"
      >
        <Edit2 className="w-4 h-4" />
        <span>Edit</span>
      </button>
      <button
        onClick={(e) => { e.stopPropagation(); onStartDelete() }}
        className="flex items-center space-x-1 px-3 py-1.5 bg-red-500/20 text-red-400 rounded-lg text-sm hover:bg-red-500/30 transition"
      >
        <Trash2 className="w-4 h-4" />
        <span>Delete</span>
      </button>
    </div>
  )
}
