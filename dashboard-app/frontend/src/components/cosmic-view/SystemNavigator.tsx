import { useState, useRef, useEffect } from 'react'
import { ChevronUp, ChevronDown, MapPin } from 'lucide-react'
import { useCosmicStore } from '../../stores'
import type { SolarSystem } from './types'

interface SystemNavigatorProps {
  systems: SolarSystem[]
  totalBodies: number
}

export function SystemNavigator({ systems, totalBodies }: SystemNavigatorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const setCameraTarget = useCosmicStore((s) => s.setCameraTarget)
  const focusedSystem = useCosmicStore((s) => s.focusedSystem)
  const focusSystem = useCosmicStore((s) => s.focusSystem)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSystemClick = (system: SolarSystem) => {
    setCameraTarget(system.position)
    focusSystem(system.id)
    setIsOpen(false)
  }

  const handleViewAll = () => {
    setCameraTarget([0, 0, 0])
    focusSystem(null)
    setIsOpen(false)
  }

  // Get severity color for system
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'blocker': return 'bg-red-500'
      case 'warning': return 'bg-orange-500'
      case 'discovery': return 'bg-green-500'
      default: return 'bg-slate-500'
    }
  }

  return (
    <div ref={dropdownRef} className="relative">
      {/* Main button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 bg-slate-900/80 backdrop-blur-sm rounded-lg text-sm text-slate-300 hover:bg-slate-800 transition-colors"
      >
        <MapPin className="w-4 h-4 text-amber-400" />
        <span className="font-medium">{systems.length} systems</span>
        <span className="text-slate-500">•</span>
        <span>{totalBodies} bodies</span>
        {isOpen ? (
          <ChevronDown className="w-4 h-4 text-slate-400" />
        ) : (
          <ChevronUp className="w-4 h-4 text-slate-400" />
        )}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute bottom-full left-0 mb-2 w-72 bg-slate-900/95 backdrop-blur-sm rounded-lg border border-slate-700 shadow-xl overflow-hidden">
          {/* Header */}
          <div className="px-3 py-2 border-b border-slate-700 flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Navigate to System</span>
            <button
              onClick={handleViewAll}
              className="text-xs text-amber-400 hover:text-amber-300"
            >
              View All
            </button>
          </div>

          {/* System list */}
          <div className="max-h-64 overflow-y-auto">
            {systems.map((system) => (
              <button
                key={system.id}
                onClick={() => handleSystemClick(system)}
                className={`w-full px-3 py-2 flex items-center gap-3 hover:bg-slate-800 transition-colors text-left ${
                  focusedSystem === system.id ? 'bg-slate-800' : ''
                }`}
              >
                {/* Severity indicator */}
                <div className={`w-2 h-2 rounded-full ${getSeverityColor(system.maxSeverity)}`} />

                {/* System info */}
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-white truncate">{system.name}</div>
                  <div className="text-xs text-slate-500 truncate">{system.directory}</div>
                </div>

                {/* Body count */}
                <div className="text-xs text-slate-400">
                  {system.bodyCount} {system.bodyCount === 1 ? 'body' : 'bodies'}
                </div>

                {/* Celestial icons */}
                <div className="flex items-center gap-1 text-xs">
                  {system.sun && <span title="Sun">☀️</span>}
                  {system.planets.length > 0 && <span title={`${system.planets.length} planets`}>🪐</span>}
                  {system.moons.length > 0 && <span title={`${system.moons.length} moons`}>🌙</span>}
                </div>
              </button>
            ))}
          </div>

          {/* Footer hint */}
          <div className="px-3 py-2 border-t border-slate-700 text-xs text-slate-500 text-center">
            Click a system to zoom to it
          </div>
        </div>
      )}
    </div>
  )
}

export default SystemNavigator
