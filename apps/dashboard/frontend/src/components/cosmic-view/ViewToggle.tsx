import { Globe2, LayoutGrid } from 'lucide-react'
import { useCosmicStore } from '../../stores'

interface ViewToggleProps {
  className?: string
}

export function ViewToggle({ className = '' }: ViewToggleProps) {
  const viewMode = useCosmicStore((s) => s.viewMode)
  const setViewMode = useCosmicStore((s) => s.setViewMode)

  return (
    <div
      className={`inline-flex rounded-lg bg-slate-800/50 p-1 backdrop-blur-sm ${className}`}
    >
      <button
        onClick={() => setViewMode('grid')}
        className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-all ${
          viewMode === 'grid'
            ? 'bg-slate-700 text-white shadow-sm'
            : 'text-slate-400 hover:text-white'
        }`}
        title="Grid View"
      >
        <LayoutGrid className="h-4 w-4" />
        <span>Grid</span>
      </button>
      <button
        onClick={() => setViewMode('cosmic')}
        className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-all ${
          viewMode === 'cosmic'
            ? 'bg-slate-700 text-white shadow-sm'
            : 'text-slate-400 hover:text-white'
        }`}
        title="Cosmic View"
      >
        <Globe2 className="h-4 w-4" />
        <span>Cosmic</span>
      </button>
    </div>
  )
}

export default ViewToggle
