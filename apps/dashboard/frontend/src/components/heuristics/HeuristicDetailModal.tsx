import { useState } from 'react'
import { createPortal } from 'react-dom'
import { X, Star, TrendingDown, TrendingUp, Shield, Brain, Award, AlertTriangle, Zap } from 'lucide-react'
import { Heuristic } from '../../types'

interface HeuristicDetailModalProps {
  heuristic: Heuristic
  onClose: () => void
  onPromote: () => Promise<void>
  onDemote: () => Promise<void>
}

function getConfidenceColor(conf: number): string {
  if (conf >= 0.8) return '#10b981' // emerald
  if (conf >= 0.5) return '#f59e0b' // amber
  return '#ef4444' // red
}

function getLifecycleInfo(h: Heuristic) {
  const isGolden = Boolean(h.is_golden)
  if (isGolden) return { stage: 'Golden Rule', color: '#fbbf24', icon: Award, glow: 'shadow-amber-500/50' }
  if (h.confidence >= 0.9 && h.times_validated >= 10) return { stage: 'Promotion Ready', color: '#10b981', icon: TrendingUp, glow: 'shadow-emerald-500/50' }
  if (h.times_validated >= 5) return { stage: 'Validated', color: '#0ea5e9', icon: Shield, glow: 'shadow-sky-500/50' }
  if (h.times_violated > h.times_validated) return { stage: 'At Risk', color: '#ef4444', icon: AlertTriangle, glow: 'shadow-red-500/50' }
  return { stage: 'Learning', color: '#64748b', icon: Brain, glow: 'shadow-slate-500/50' }
}

export default function HeuristicDetailModal({
  heuristic: h,
  onClose,
  onPromote,
  onDemote,
}: HeuristicDetailModalProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [actionType, setActionType] = useState<'promote' | 'demote' | null>(null)

  const isGolden = Boolean(h.is_golden)
  const canPromote = !isGolden && h.confidence >= 0.8
  const lifecycle = getLifecycleInfo(h)
  const LifecycleIcon = lifecycle.icon
  const confidencePercent = Math.round(h.confidence * 100)

  const handlePromote = async () => {
    setIsLoading(true)
    setActionType('promote')
    try {
      await onPromote()
      onClose()
    } catch (err) {
      console.error('Failed to promote:', err)
    } finally {
      setIsLoading(false)
      setActionType(null)
    }
  }

  const handleDemote = async () => {
    setIsLoading(true)
    setActionType('demote')
    try {
      await onDemote()
      onClose()
    } catch (err) {
      console.error('Failed to demote:', err)
    } finally {
      setIsLoading(false)
      setActionType(null)
    }
  }

  return createPortal(
    <div
      className="fixed inset-0 flex items-center justify-center p-4 overflow-y-auto"
      style={{
        zIndex: 99999,
        background: 'radial-gradient(ellipse at center, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.95) 100%)',
        backdropFilter: 'blur(8px)',
      }}
      onClick={onClose}
    >
      {/* Holographic Modal Container */}
      <div
        className={`relative w-full max-w-lg overflow-hidden ${lifecycle.glow}`}
        style={{
          background: 'linear-gradient(135deg, rgba(15,23,42,0.98) 0%, rgba(30,41,59,0.95) 100%)',
          border: '1px solid rgba(100,116,139,0.3)',
          borderRadius: '16px',
          boxShadow: `
            0 0 40px rgba(0,0,0,0.5),
            inset 0 1px 0 rgba(255,255,255,0.05),
            0 0 60px ${lifecycle.color}20
          `,
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Scan line effect */}
        <div
          className="absolute inset-0 pointer-events-none opacity-[0.03]"
          style={{
            backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(255,255,255,0.1) 2px, rgba(255,255,255,0.1) 4px)',
          }}
        />

        {/* Top glow bar */}
        <div
          className="absolute top-0 left-0 right-0 h-[2px]"
          style={{
            background: `linear-gradient(90deg, transparent 0%, ${lifecycle.color} 50%, transparent 100%)`,
            boxShadow: `0 0 20px ${lifecycle.color}`,
          }}
        />

        {/* Header */}
        <div className="relative p-5 border-b border-slate-700/50">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              {/* Badges row */}
              <div className="flex items-center gap-2 mb-3">
                <span
                  className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded"
                  style={{
                    background: 'rgba(71,85,105,0.4)',
                    color: '#94a3b8',
                    border: '1px solid rgba(71,85,105,0.5)',
                  }}
                >
                  {h.domain}
                </span>
                <span
                  className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded"
                  style={{
                    background: `${lifecycle.color}15`,
                    color: lifecycle.color,
                    border: `1px solid ${lifecycle.color}40`,
                  }}
                >
                  <LifecycleIcon className="w-3 h-3" />
                  {lifecycle.stage}
                </span>
              </div>

              {/* Title with golden star */}
              <div className="flex items-start gap-2">
                {isGolden && (
                  <Star
                    className="w-5 h-5 flex-shrink-0 mt-0.5"
                    style={{ color: '#fbbf24', fill: '#fbbf24' }}
                  />
                )}
                <h2 className="text-base font-semibold text-white leading-snug">
                  {h.rule}
                </h2>
              </div>
            </div>

            {/* Close button */}
            <button
              onClick={onClose}
              className="p-2 text-slate-500 hover:text-white hover:bg-slate-700/50 rounded-lg transition-all duration-200"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="relative p-5 space-y-5">
          {/* Explanation */}
          {h.explanation && (
            <div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-2">
                Explanation
              </div>
              <p className="text-sm text-slate-300 leading-relaxed">
                {h.explanation}
              </p>
            </div>
          )}

          {/* Stats Grid */}
          <div className="grid grid-cols-2 gap-3">
            {/* Confidence */}
            <div
              className="p-3 rounded-lg"
              style={{
                background: 'rgba(30,41,59,0.6)',
                border: '1px solid rgba(71,85,105,0.3)',
              }}
            >
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                Confidence
              </div>
              <div
                className="text-2xl font-bold font-mono"
                style={{ color: getConfidenceColor(h.confidence) }}
              >
                {confidencePercent}%
              </div>
              {/* Mini progress bar */}
              <div className="mt-2 h-1 rounded-full bg-slate-700 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${confidencePercent}%`,
                    background: getConfidenceColor(h.confidence),
                    boxShadow: `0 0 8px ${getConfidenceColor(h.confidence)}`,
                  }}
                />
              </div>
            </div>

            {/* Validated */}
            <div
              className="p-3 rounded-lg"
              style={{
                background: 'rgba(30,41,59,0.6)',
                border: '1px solid rgba(71,85,105,0.3)',
              }}
            >
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                Validated
              </div>
              <div className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-emerald-400" />
                <span className="text-2xl font-bold font-mono text-emerald-400">
                  {h.times_validated}
                </span>
              </div>
            </div>

            {/* Violated */}
            <div
              className="p-3 rounded-lg"
              style={{
                background: 'rgba(30,41,59,0.6)',
                border: '1px solid rgba(71,85,105,0.3)',
              }}
            >
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                Violated
              </div>
              <div className="flex items-center gap-2">
                <TrendingDown className="w-5 h-5 text-red-400" />
                <span className="text-2xl font-bold font-mono text-red-400">
                  {h.times_violated}
                </span>
              </div>
            </div>

            {/* Created */}
            <div
              className="p-3 rounded-lg"
              style={{
                background: 'rgba(30,41,59,0.6)',
                border: '1px solid rgba(71,85,105,0.3)',
              }}
            >
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                Created
              </div>
              <div className="text-sm font-mono text-slate-300">
                {new Date(h.created_at).toLocaleDateString()}
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">
                {h.source_type}
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="pt-3 border-t border-slate-700/50">
            {isGolden ? (
              /* Demote Button */
              <button
                onClick={handleDemote}
                disabled={isLoading}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-medium text-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                style={{
                  background: 'rgba(71,85,105,0.3)',
                  border: '1px solid rgba(71,85,105,0.5)',
                  color: '#94a3b8',
                }}
                onMouseEnter={e => {
                  if (!isLoading) {
                    e.currentTarget.style.background = 'rgba(239,68,68,0.2)'
                    e.currentTarget.style.borderColor = 'rgba(239,68,68,0.5)'
                    e.currentTarget.style.color = '#f87171'
                  }
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = 'rgba(71,85,105,0.3)'
                  e.currentTarget.style.borderColor = 'rgba(71,85,105,0.5)'
                  e.currentTarget.style.color = '#94a3b8'
                }}
              >
                {isLoading && actionType === 'demote' ? (
                  <>
                    <Zap className="w-4 h-4 animate-pulse" />
                    Demoting...
                  </>
                ) : (
                  <>
                    <TrendingDown className="w-4 h-4" />
                    Demote from Golden Rule
                  </>
                )}
              </button>
            ) : canPromote ? (
              /* Promote Button */
              <button
                onClick={handlePromote}
                disabled={isLoading}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-medium text-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed group"
                style={{
                  background: 'linear-gradient(135deg, rgba(251,191,36,0.2) 0%, rgba(245,158,11,0.2) 100%)',
                  border: '1px solid rgba(251,191,36,0.4)',
                  color: '#fbbf24',
                  boxShadow: '0 0 20px rgba(251,191,36,0.1)',
                }}
                onMouseEnter={e => {
                  if (!isLoading) {
                    e.currentTarget.style.background = 'linear-gradient(135deg, rgba(251,191,36,0.3) 0%, rgba(245,158,11,0.3) 100%)'
                    e.currentTarget.style.boxShadow = '0 0 30px rgba(251,191,36,0.3)'
                  }
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = 'linear-gradient(135deg, rgba(251,191,36,0.2) 0%, rgba(245,158,11,0.2) 100%)'
                  e.currentTarget.style.boxShadow = '0 0 20px rgba(251,191,36,0.1)'
                }}
              >
                {isLoading && actionType === 'promote' ? (
                  <>
                    <Zap className="w-4 h-4 animate-pulse" />
                    Promoting...
                  </>
                ) : (
                  <>
                    <Star className="w-4 h-4" />
                    Promote to Golden Rule
                  </>
                )}
              </button>
            ) : (
              /* Cannot Promote - Low Confidence */
              <div
                className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg text-sm"
                style={{
                  background: 'rgba(30,41,59,0.4)',
                  border: '1px dashed rgba(71,85,105,0.5)',
                  color: '#64748b',
                }}
              >
                <AlertTriangle className="w-4 h-4" />
                Needs 80% confidence to promote
              </div>
            )}
          </div>
        </div>

        {/* Bottom glow bar */}
        <div
          className="absolute bottom-0 left-0 right-0 h-[1px]"
          style={{
            background: `linear-gradient(90deg, transparent 0%, ${lifecycle.color}40 50%, transparent 100%)`,
          }}
        />
      </div>
    </div>,
    document.body
  )
}
