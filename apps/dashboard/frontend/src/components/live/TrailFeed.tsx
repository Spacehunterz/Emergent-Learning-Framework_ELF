import React, { useRef, useEffect, useState } from 'react'
import { Copy, Check, ArrowDown, ArrowUp } from 'lucide-react'

export interface Trail {
  id: number
  location: string
  scent: string
  strength: number
  agent_id?: string
  message?: string
  created_at: string
}

interface TrailFeedProps {
  trails: Trail[]
  autoScroll: boolean
  onAutoScrollChange: (enabled: boolean) => void
}

const SCENT_CONFIG: Record<string, { color: string; bgColor: string; emoji: string; label: string }> = {
  discovery: {
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-500/10',
    emoji: '\uD83D\uDFE2',
    label: 'Discovery',
  },
  warning: {
    color: 'text-amber-400',
    bgColor: 'bg-amber-500/10',
    emoji: '\uD83D\uDFE1',
    label: 'Warning',
  },
  blocker: {
    color: 'text-red-400',
    bgColor: 'bg-red-500/10',
    emoji: '\uD83D\uDD34',
    label: 'Blocker',
  },
  hot: {
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/10',
    emoji: '\uD83D\uDFE0',
    label: 'Hot',
  },
  info: {
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/10',
    emoji: '\uD83D\uDD35',
    label: 'Info',
  },
}

function TrailCard({ trail }: { trail: Trail }) {
  const [copied, setCopied] = useState(false)
  const config = SCENT_CONFIG[trail.scent] || SCENT_CONFIG.info

  const handleCopyPath = async (e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await navigator.clipboard.writeText(trail.location)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy path:', err)
    }
  }

  // Calculate opacity based on strength (0-1)
  const opacity = Math.max(0.3, Math.min(1, trail.strength))

  // Format timestamp
  const timestamp = new Date(trail.created_at)
  const timeStr = timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })

  return (
    <div
      className={`p-3 rounded-lg border border-slate-700/50 ${config.bgColor} transition-opacity`}
      style={{ opacity }}
    >
      <div className="flex items-start gap-2">
        <span className="text-lg flex-shrink-0">{config.emoji}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs font-semibold ${config.color}`}>
              {config.label}
            </span>
            <span className="text-[10px] text-slate-500">{timeStr}</span>
            {trail.agent_id && (
              <span className="text-[10px] text-slate-600 px-1.5 py-0.5 bg-slate-800 rounded">
                {trail.agent_id.slice(0, 8)}
              </span>
            )}
          </div>

          {trail.message && (
            <div className="text-sm text-slate-300 mb-2">
              {trail.message}
            </div>
          )}

          <div className="flex items-center gap-2">
            <div
              className="flex-1 text-xs text-slate-500 font-mono truncate cursor-pointer hover:text-slate-400"
              onClick={handleCopyPath}
              title={trail.location}
            >
              {trail.location}
            </div>
            <button
              onClick={handleCopyPath}
              className="flex-shrink-0 p-1 text-slate-500 hover:text-slate-300 transition-colors"
              title="Copy path"
            >
              {copied ? (
                <Check className="w-3 h-3 text-emerald-400" />
              ) : (
                <Copy className="w-3 h-3" />
              )}
            </button>
          </div>

          {/* Strength indicator */}
          <div className="mt-2 flex items-center gap-2">
            <div className="flex-1 h-1 bg-slate-800 rounded-full overflow-hidden">
              <div
                className={`h-full ${config.bgColor.replace('/10', '/50')} transition-all`}
                style={{ width: `${trail.strength * 100}%` }}
              />
            </div>
            <span className="text-[10px] text-slate-600">
              {Math.round(trail.strength * 100)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

export function TrailFeed({ trails, autoScroll, onAutoScrollChange }: TrailFeedProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [isAtBottom, setIsAtBottom] = useState(true)

  // Auto-scroll to top when new trails arrive (newest at top)
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = 0
    }
  }, [trails.length, autoScroll])

  const handleScroll = () => {
    if (containerRef.current) {
      const { scrollTop } = containerRef.current
      setIsAtBottom(scrollTop < 10)
    }
  }

  const scrollToTop = () => {
    if (containerRef.current) {
      containerRef.current.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  // Sort trails by created_at descending (newest first)
  const sortedTrails = [...trails].sort((a, b) =>
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-slate-700/50">
        <span className="text-xs font-bold tracking-wider text-slate-400">
          PHEROMONE TRAILS
        </span>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-slate-600">
            {trails.length} trails
          </span>
          <button
            onClick={() => onAutoScrollChange(!autoScroll)}
            className={`p-1 rounded transition-colors ${
              autoScroll ? 'bg-violet-500/20 text-violet-400' : 'text-slate-500 hover:text-slate-400'
            }`}
            title={autoScroll ? 'Auto-scroll on' : 'Auto-scroll off'}
          >
            <ArrowUp className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Trail List */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-2 space-y-2"
      >
        {sortedTrails.length === 0 ? (
          <div className="text-center text-slate-600 text-sm py-8">
            No trails yet. Agents will leave trails as they work.
          </div>
        ) : (
          sortedTrails.map(trail => (
            <TrailCard key={trail.id} trail={trail} />
          ))
        )}
      </div>

      {/* Scroll to top button */}
      {!isAtBottom && (
        <button
          onClick={scrollToTop}
          className="absolute bottom-4 right-4 p-2 bg-slate-800 border border-slate-700 rounded-full shadow-lg hover:bg-slate-700 transition-colors"
        >
          <ArrowUp className="w-4 h-4 text-slate-400" />
        </button>
      )}
    </div>
  )
}
