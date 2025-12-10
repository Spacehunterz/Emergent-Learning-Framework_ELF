import { useState } from 'react'
import { Heuristic } from '../types'
import { Brain, Star, TrendingUp, TrendingDown, Shield, Filter, ChevronDown, ChevronUp, Award, AlertTriangle, Trash2, Edit2, X, Save } from 'lucide-react'

interface HeuristicPanelProps {
  heuristics: Heuristic[]
  onPromote: (id: number) => void
  onDemote: (id: number) => void
  onDelete: (id: number) => void
  onUpdate: (id: number, updates: { rule?: string; explanation?: string; domain?: string }) => void
  selectedDomain: string | null
  onDomainFilter: (domain: string | null) => void
}

type SortField = 'confidence' | 'validated' | 'created' | 'domain'
type SortDir = 'asc' | 'desc'

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
  const [editForm, setEditForm] = useState<{ rule: string; explanation: string; domain: string }>({ rule: '', explanation: '', domain: '' })
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

  const SortButton = ({ field, label }: { field: SortField; label: string }) => (
    <button
      onClick={() => toggleSort(field)}
      className={`flex items-center space-x-1 text-xs font-medium px-2 py-1 rounded
        ${sortField === field ? 'bg-sky-500/20 text-sky-400' : 'text-slate-400 hover:text-white'}`}
    >
      <span>{label}</span>
      {sortField === field && (
        sortDir === 'desc' ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />
      )}
    </button>
  )

  const getConfidenceColor = (conf: number) => {
    if (conf >= 0.8) return 'text-emerald-400'
    if (conf >= 0.5) return 'text-yellow-400'
    return 'text-red-400'
  }

  const getLifecycleStage = (h: Heuristic) => {
    if (h.is_golden) return { stage: 'Golden', color: 'text-amber-400', icon: Award }
    if (h.confidence >= 0.9 && h.times_validated >= 10) return { stage: 'Promotion Ready', color: 'text-emerald-400', icon: TrendingUp }
    if (h.times_validated >= 5) return { stage: 'Validated', color: 'text-sky-400', icon: Shield }
    if (h.times_violated > h.times_validated) return { stage: 'At Risk', color: 'text-red-400', icon: AlertTriangle }
    return { stage: 'Learning', color: 'text-slate-400', icon: Brain }
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
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Brain className="w-5 h-5 text-violet-400" />
          <h3 className="text-lg font-semibold text-white">Heuristics</h3>
          <span className="text-sm text-slate-400">({sorted.length} of {heuristics.length})</span>
        </div>

        <div className="flex items-center space-x-4">
          {/* Golden only toggle */}
          <button
            onClick={() => setShowGoldenOnly(!showGoldenOnly)}
            className={`flex items-center space-x-1 px-3 py-1.5 rounded-lg text-sm
              ${showGoldenOnly ? 'bg-amber-500/20 text-amber-400' : 'bg-slate-700 text-slate-400 hover:text-white'}`}
          >
            <Star className="w-4 h-4" />
            <span>Golden Only</span>
          </button>

          {/* Domain filter */}
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <select
              value={selectedDomain || ''}
              onChange={(e) => onDomainFilter(e.target.value || null)}
              className="bg-slate-700 text-sm text-white rounded-md px-3 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500"
            >
              <option value="">All Domains</option>
              {domains.map(domain => (
                <option key={domain} value={domain}>{domain}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Sort controls */}
      <div className="flex items-center space-x-2 mb-4">
        <span className="text-xs text-slate-500">Sort by:</span>
        <SortButton field="confidence" label="Confidence" />
        <SortButton field="validated" label="Validations" />
        <SortButton field="created" label="Created" />
        <SortButton field="domain" label="Domain" />
      </div>

      {/* Heuristics list */}
      <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2">
        {sorted.map(h => {
          const lifecycle = getLifecycleStage(h)
          const LifecycleIcon = lifecycle.icon
          const isExpanded = expandedId === h.id

          return (
            <div
              key={h.id}
              className={`bg-slate-700/50 rounded-lg border transition-all
                ${h.is_golden ? 'border-amber-500/30' : 'border-transparent'}
                ${isExpanded ? 'ring-2 ring-sky-500/50' : ''}`}
            >
              {/* Main row */}
              <div
                className="p-3 cursor-pointer"
                onClick={() => setExpandedId(isExpanded ? null : h.id)}
              >
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

                    {/* Lifecycle visualization */}
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

                    {/* Edit Form */}
                    {editingId === h.id ? (
                      <div className="space-y-3 pt-2 border-t border-slate-600 mt-2">
                        <div>
                          <label className="text-xs text-slate-400 block mb-1">Rule</label>
                          <input
                            type="text"
                            value={editForm.rule}
                            onChange={(e) => setEditForm({ ...editForm, rule: e.target.value })}
                            className="w-full bg-slate-600 text-white rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
                            onClick={(e) => e.stopPropagation()}
                          />
                        </div>
                        <div>
                          <label className="text-xs text-slate-400 block mb-1">Explanation</label>
                          <textarea
                            value={editForm.explanation}
                            onChange={(e) => setEditForm({ ...editForm, explanation: e.target.value })}
                            className="w-full bg-slate-600 text-white rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 resize-none"
                            rows={2}
                            onClick={(e) => e.stopPropagation()}
                          />
                        </div>
                        <div>
                          <label className="text-xs text-slate-400 block mb-1">Domain</label>
                          <input
                            type="text"
                            value={editForm.domain}
                            onChange={(e) => setEditForm({ ...editForm, domain: e.target.value })}
                            className="w-full bg-slate-600 text-white rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
                            onClick={(e) => e.stopPropagation()}
                          />
                        </div>
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={(e) => { e.stopPropagation(); saveEdit(h.id) }}
                            className="flex items-center space-x-1 px-3 py-1.5 bg-emerald-500/20 text-emerald-400 rounded-lg text-sm hover:bg-emerald-500/30 transition"
                          >
                            <Save className="w-4 h-4" />
                            <span>Save</span>
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); cancelEdit() }}
                            className="flex items-center space-x-1 px-3 py-1.5 bg-slate-600 text-slate-300 rounded-lg text-sm hover:bg-slate-500 transition"
                          >
                            <X className="w-4 h-4" />
                            <span>Cancel</span>
                          </button>
                        </div>
                      </div>
                    ) : deleteConfirmId === h.id ? (
                      /* Delete Confirmation */
                      <div className="flex items-center space-x-3 pt-2 border-t border-red-500/30 mt-2">
                        <span className="text-sm text-red-400">Delete this heuristic?</span>
                        <button
                          onClick={(e) => { e.stopPropagation(); confirmDelete(h.id) }}
                          className="flex items-center space-x-1 px-3 py-1.5 bg-red-500/20 text-red-400 rounded-lg text-sm hover:bg-red-500/30 transition"
                        >
                          <Trash2 className="w-4 h-4" />
                          <span>Yes, Delete</span>
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); setDeleteConfirmId(null) }}
                          className="flex items-center space-x-1 px-3 py-1.5 bg-slate-600 text-slate-300 rounded-lg text-sm hover:bg-slate-500 transition"
                        >
                          <X className="w-4 h-4" />
                          <span>Cancel</span>
                        </button>
                      </div>
                    ) : (
                      /* Actions */
                      <div className="flex items-center space-x-2 pt-2">
                        {!h.is_golden && h.confidence >= 0.8 && (
                          <button
                            onClick={(e) => { e.stopPropagation(); onPromote(h.id) }}
                            className="flex items-center space-x-1 px-3 py-1.5 bg-amber-500/20 text-amber-400 rounded-lg text-sm hover:bg-amber-500/30 transition"
                          >
                            <Star className="w-4 h-4" />
                            <span>Promote to Golden</span>
                          </button>
                        )}
                        {h.is_golden && (
                          <button
                            onClick={(e) => { e.stopPropagation(); onDemote(h.id) }}
                            className="flex items-center space-x-1 px-3 py-1.5 bg-slate-600 text-slate-300 rounded-lg text-sm hover:bg-slate-500 transition"
                          >
                            <TrendingDown className="w-4 h-4" />
                            <span>Demote from Golden</span>
                          </button>
                        )}
                        <button
                          onClick={(e) => { e.stopPropagation(); startEdit(h) }}
                          className="flex items-center space-x-1 px-3 py-1.5 bg-sky-500/20 text-sky-400 rounded-lg text-sm hover:bg-sky-500/30 transition"
                        >
                          <Edit2 className="w-4 h-4" />
                          <span>Edit</span>
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); setDeleteConfirmId(h.id) }}
                          className="flex items-center space-x-1 px-3 py-1.5 bg-red-500/20 text-red-400 rounded-lg text-sm hover:bg-red-500/30 transition"
                        >
                          <Trash2 className="w-4 h-4" />
                          <span>Delete</span>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
