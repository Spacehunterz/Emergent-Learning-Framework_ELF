import { CheckCircle, XCircle } from 'lucide-react'
import { InvariantActionsProps } from './types'

export default function InvariantActions({
  isLoading,
  onValidate,
  onViolate,
}: Omit<InvariantActionsProps, 'invariantId'>) {
  return (
    <div className="flex items-center space-x-2 pt-2">
      <button
        onClick={(e) => { e.stopPropagation(); onValidate() }}
        disabled={isLoading}
        className="flex items-center space-x-1 px-3 py-1.5 bg-emerald-500/20 text-emerald-400 rounded-lg text-sm hover:bg-emerald-500/30 transition disabled:opacity-50"
      >
        <CheckCircle className="w-4 h-4" />
        <span>Validate</span>
      </button>
      <button
        onClick={(e) => { e.stopPropagation(); onViolate() }}
        disabled={isLoading}
        className="flex items-center space-x-1 px-3 py-1.5 bg-red-500/20 text-red-400 rounded-lg text-sm hover:bg-red-500/30 transition disabled:opacity-50"
      >
        <XCircle className="w-4 h-4" />
        <span>Record Violation</span>
      </button>
    </div>
  )
}
