export interface FileDiff {
  path: string
  changes: DiffChange[]
  additions: number
  deletions: number
}

export interface DiffChange {
  type: 'add' | 'remove' | 'context'
  lineNumber: number
  content: string
  oldLineNumber?: number
  newLineNumber?: number
}

export interface DiffViewerProps {
  runId: string
  diffs: FileDiff[]
  onClose: () => void
}

export interface DiffHeaderProps {
  runId: string
  totalAdditions: number
  totalDeletions: number
  filesChanged: number
  viewMode: 'split' | 'unified'
  onViewModeChange: (mode: 'split' | 'unified') => void
  onExpandAll: () => void
  onCollapseAll: () => void
  onClose: () => void
}

export interface FileHeaderProps {
  path: string
  additions: number
  deletions: number
  isExpanded: boolean
  onToggle: () => void
  onCopyPath: (path: string) => void
  copiedPath: string | null
}

export interface UnifiedDiffViewProps {
  changes: DiffChange[]
}

export interface SplitDiffViewProps {
  changes: DiffChange[]
}
