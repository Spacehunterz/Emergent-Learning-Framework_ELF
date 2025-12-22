import { Heuristic } from '../../types'

export type SortField = 'confidence' | 'validated' | 'created' | 'domain'
export type SortDir = 'asc' | 'desc'

export interface EditFormData {
  rule: string
  explanation: string
  domain: string
}

export interface HeuristicCardProps {
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

export interface LifecycleInfo {
  stage: string
  color: string
  icon: any
}
