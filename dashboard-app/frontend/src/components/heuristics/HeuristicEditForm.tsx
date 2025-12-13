import { Save, X } from 'lucide-react'
import { EditFormData } from './types'

interface HeuristicEditFormProps {
  editForm: EditFormData
  onEditFormChange: (form: EditFormData) => void
  onSave: () => void
  onCancel: () => void
}

export default function HeuristicEditForm({
  editForm,
  onEditFormChange,
  onSave,
  onCancel,
}: HeuristicEditFormProps) {
  return (
    <div className="space-y-3 pt-2 border-t border-slate-600 mt-2">
      <div>
        <label className="text-xs text-slate-400 block mb-1">Rule</label>
        <input
          type="text"
          value={editForm.rule}
          onChange={(e) => onEditFormChange({ ...editForm, rule: e.target.value })}
          className="w-full bg-slate-600 text-white rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
          onClick={(e) => e.stopPropagation()}
        />
      </div>
      <div>
        <label className="text-xs text-slate-400 block mb-1">Explanation</label>
        <textarea
          value={editForm.explanation}
          onChange={(e) => onEditFormChange({ ...editForm, explanation: e.target.value })}
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
          onChange={(e) => onEditFormChange({ ...editForm, domain: e.target.value })}
          className="w-full bg-slate-600 text-white rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
          onClick={(e) => e.stopPropagation()}
        />
      </div>
      <div className="flex items-center space-x-2">
        <button
          onClick={(e) => { e.stopPropagation(); onSave() }}
          className="flex items-center space-x-1 px-3 py-1.5 bg-emerald-500/20 text-emerald-400 rounded-lg text-sm hover:bg-emerald-500/30 transition"
        >
          <Save className="w-4 h-4" />
          <span>Save</span>
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onCancel() }}
          className="flex items-center space-x-1 px-3 py-1.5 bg-slate-600 text-slate-300 rounded-lg text-sm hover:bg-slate-500 transition"
        >
          <X className="w-4 h-4" />
          <span>Cancel</span>
        </button>
      </div>
    </div>
  )
}
