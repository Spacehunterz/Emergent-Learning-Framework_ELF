import { useState, useRef, useEffect } from 'react'
import { Filter, X } from 'lucide-react'
import { useCosmicStore } from '../../stores'
import type { Severity } from '../../stores'

interface CosmicFiltersProps {
  selectedDomain: string | null
  onDomainFilter: (domain: string | null) => void
  domains: string[]
}

export function CosmicFilters({
  selectedDomain,
  onDomainFilter,
  domains,
}: CosmicFiltersProps) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const severityFilter = useCosmicStore((s) => s.severityFilter)
  const toggleSeverity = useCosmicStore((s) => s.toggleSeverity)
  const resetFilters = useCosmicStore((s) => s.resetFilters)
  const autoRotate = useCosmicStore((s) => s.autoRotate)
  const setAutoRotate = useCosmicStore((s) => s.setAutoRotate)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const severityOptions: { value: Severity; label: string; color: string }[] = [
    { value: 'blocker', label: 'Blockers (Suns)', color: 'bg-red-500' },
    { value: 'warning', label: 'Warnings (Planets)', color: 'bg-orange-500' },
    { value: 'discovery', label: 'Discoveries (Moons)', color: 'bg-green-500' },
  ]

  const hasActiveFilters =
    severityFilter.length < 3 || selectedDomain !== null

  const handleReset = () => {
    resetFilters()
    onDomainFilter(null)
  }

  return (
    <div ref={dropdownRef} className="relative">
      {/* Filter button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
          hasActiveFilters
            ? 'border-amber-500/50 bg-amber-500/20 text-amber-300'
            : 'border-slate-700 bg-slate-900/90 text-slate-300 hover:bg-slate-800'
        } backdrop-blur-sm`}
      >
        <Filter className="h-3 w-3" />
        <span>Filters</span>
        {hasActiveFilters && (
          <span className="ml-1 rounded-full bg-amber-500 px-1.5 text-[10px] text-black">
            {3 - severityFilter.length + (selectedDomain ? 1 : 0)}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute right-0 top-full z-50 mt-2 w-56 rounded-lg border border-slate-700 bg-slate-900/95 p-3 shadow-xl backdrop-blur-sm">
          {/* Severity filters */}
          <div className="mb-3">
            <div className="mb-2 text-xs font-medium text-slate-400">
              Show Body Types
            </div>
            <div className="space-y-1.5">
              {severityOptions.map((option) => (
                <label
                  key={option.value}
                  className="flex cursor-pointer items-center gap-2 rounded px-2 py-1 hover:bg-slate-800"
                >
                  <input
                    type="checkbox"
                    checked={severityFilter.includes(option.value)}
                    onChange={() => toggleSeverity(option.value)}
                    className="rounded border-slate-600 bg-slate-800 text-amber-500 focus:ring-amber-500/50"
                  />
                  <div className={`h-2 w-2 rounded-full ${option.color}`} />
                  <span className="text-xs text-slate-300">{option.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Directory filter */}
          {domains.length > 0 && (
            <div className="mb-3">
              <div className="mb-2 text-xs font-medium text-slate-400">
                Focus Directory
              </div>
              <select
                value={selectedDomain || ''}
                onChange={(e) => onDomainFilter(e.target.value || null)}
                className="w-full rounded border border-slate-700 bg-slate-800 px-2 py-1.5 text-xs text-slate-300 focus:border-amber-500 focus:outline-none"
              >
                <option value="">All directories</option>
                {domains.slice(0, 20).map((domain) => (
                  <option key={domain} value={domain}>
                    {domain.split('/').pop() || domain}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Auto-rotate toggle */}
          <div className="mb-3">
            <label className="flex cursor-pointer items-center justify-between rounded px-2 py-1 hover:bg-slate-800">
              <span className="text-xs text-slate-300">Auto-rotate camera</span>
              <input
                type="checkbox"
                checked={autoRotate}
                onChange={(e) => setAutoRotate(e.target.checked)}
                className="rounded border-slate-600 bg-slate-800 text-amber-500 focus:ring-amber-500/50"
              />
            </label>
          </div>

          {/* Reset button */}
          {hasActiveFilters && (
            <button
              onClick={handleReset}
              className="flex w-full items-center justify-center gap-1 rounded bg-slate-800 py-1.5 text-xs text-slate-400 hover:bg-slate-700 hover:text-slate-300"
            >
              <X className="h-3 w-3" />
              Reset filters
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export default CosmicFilters
