import { useState } from 'react'
import { Heuristic } from '../types'
import { HeuristicCard, HeuristicFilters, SortField, SortDir, EditFormData } from './heuristics'

interface HeuristicPanelProps {
  heuristics: Heuristic[]
  onPromote: (id: number) => void
  onDemote: (id: number) => void
  onDelete: (id: number) => void
  onUpdate: (id: number, updates: { rule?: string; explanation?: string; domain?: string }) => void
  selectedDomain: string | null
  onDomainFilter: (domain: string | null) => void
}

export default function HeuristicPanel({
  heuristics,
  onPromote,
  onDemote,
  onDelete,
  onUpdate,
  selectedDomain,
  onDomainFilter
}: HeuristicPanelProps) {
  const [sortField, setSortField] = useState<SortField>('confidence')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [showGoldenOnly, setShowGoldenOnly] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editForm, setEditForm] = useState<EditFormData>({ rule: '', explanation: '', domain: '' })
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null)

  const domains = Array.from(new Set(heuristics.map(h => h.domain)))

  // Filter and sort
  let filtered = heuristics
  if (selectedDomain) {
    filtered = filtered.filter(h => h.domain === selectedDomain)
  }
  if (showGoldenOnly) {
    filtered = filtered.filter(h => h.is_golden)
  }

  const sorted = [...filtered].sort((a, b) => {
    let cmp = 0
    switch (sortField) {
      case 'confidence':
        cmp = a.confidence - b.confidence
        break
      case 'validated':
        cmp = a.times_validated - b.times_validated
        break
      case 'created':
        cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        break
      case 'domain':
        cmp = a.domain.localeCompare(b.domain)
        break
    }
    return sortDir === 'desc' ? -cmp : cmp
  })

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDir('desc')
    }
  }

  const startEdit = (h: Heuristic) => {
    setEditingId(h.id)
    setEditForm({ rule: h.rule, explanation: h.explanation || '', domain: h.domain })
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditForm({ rule: '', explanation: '', domain: '' })
  }

  const saveEdit = (id: number) => {
    onUpdate(id, editForm)
    setEditingId(null)
    setEditForm({ rule: '', explanation: '', domain: '' })
  }

  const confirmDelete = (id: number) => {
    onDelete(id)
    setDeleteConfirmId(null)
  }

  return (
    <div className="bg-slate-800 rounded-lg p-4">
      <HeuristicFilters
        totalCount={heuristics.length}
        filteredCount={sorted.length}
        domains={domains}
        selectedDomain={selectedDomain}
        showGoldenOnly={showGoldenOnly}
        sortField={sortField}
        sortDir={sortDir}
        onDomainFilter={onDomainFilter}
        onToggleGoldenOnly={() => setShowGoldenOnly(!showGoldenOnly)}
        onToggleSort={toggleSort}
      />

      {/* Heuristics list */}
      <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2">
        {sorted.map(h => (
          <HeuristicCard
            key={h.id}
            heuristic={h}
            isExpanded={expandedId === h.id}
            isEditing={editingId === h.id}
            isDeleting={deleteConfirmId === h.id}
            editForm={editForm}
            onToggleExpand={() => setExpandedId(expandedId === h.id ? null : h.id)}
            onStartEdit={() => startEdit(h)}
            onCancelEdit={cancelEdit}
            onSaveEdit={() => saveEdit(h.id)}
            onEditFormChange={setEditForm}
            onPromote={() => onPromote(h.id)}
            onDemote={() => onDemote(h.id)}
            onStartDelete={() => setDeleteConfirmId(h.id)}
            onConfirmDelete={() => confirmDelete(h.id)}
            onCancelDelete={() => setDeleteConfirmId(null)}
          />
        ))}
      </div>
    </div>
  )
}
