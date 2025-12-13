import { X, ArrowLeft, ChevronRight, Loader2, AlertCircle, RefreshCw } from 'lucide-react'
import { DrillDownView } from './types'
import RunsDrillDown from './RunsDrillDown'
import HeuristicsDrillDown from './HeuristicsDrillDown'
import GoldenRulesDrillDown from './GoldenRulesDrillDown'
import HotspotsDrillDown from './HotspotsDrillDown'
import QueriesDrillDown from './QueriesDrillDown'

interface StatCardData {
  label: string
  value: string | number
  icon: any
  color: string
  bgColor: string
  description: string
  drillDownType?: 'runs' | 'heuristics' | 'hotspots' | 'golden' | 'learnings' | 'queries'
  details?: { label: string; value: string | number }[]
}

interface DrillDownModalProps {
  card: StatCardData
  drillDownView: DrillDownView
  drillDownData: any
  loading: boolean
  error: string | null
  onClose: () => void
  onBack: () => void
  onLoadDrillDown: (type: DrillDownView) => void
}

export default function DrillDownModal({
  card,
  drillDownView,
  drillDownData,
  loading,
  error,
  onClose,
  onBack,
  onLoadDrillDown,
}: DrillDownModalProps) {
  const Icon = card.icon

  const renderDrillDownContent = () => {
    if (loading) {
      return (
        <div className="flex flex-col items-center justify-center py-8 gap-2">
          <Loader2 className="w-8 h-8 animate-spin" style={{ color: 'var(--theme-accent)' }} />
          <span className="text-sm text-slate-400">Loading data...</span>
        </div>
      )
    }

    if (error) {
      return (
        <div className="flex flex-col items-center justify-center py-8 gap-3">
          <AlertCircle className="w-8 h-8 text-red-400" />
          <span className="text-sm text-red-400 text-center">{error}</span>
          <button
            onClick={() => onLoadDrillDown(drillDownView)}
            className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
        </div>
      )
    }

    if (!drillDownData) return null

    switch (drillDownView) {
      case 'runs':
        return <RunsDrillDown data={drillDownData} cardLabel={card.label} />
      case 'heuristics':
        return <HeuristicsDrillDown data={drillDownData} />
      case 'golden':
        return <GoldenRulesDrillDown data={drillDownData} />
      case 'hotspots':
        return <HotspotsDrillDown data={drillDownData} />
      case 'queries':
        return <QueriesDrillDown data={drillDownData} />
      default:
        return null
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="glass-panel rounded-xl p-6 max-w-lg w-full shadow-2xl max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          {drillDownView !== 'main' ? (
            <button onClick={onBack} className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors">
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm">Back</span>
            </button>
          ) : (
            <div className="flex items-center gap-3">
              <div className={`p-3 rounded-lg ${card.bgColor}`}>
                <Icon className={`w-6 h-6 ${card.color}`} />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">{card.label}</h3>
                <div className={`text-3xl font-bold ${card.color}`}>{card.value}</div>
              </div>
            </div>
          )}
          <button onClick={onClose} className="p-2 text-slate-400 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {drillDownView === 'main' ? (
            <>
              <p className="text-slate-300 text-sm mb-4">{card.description}</p>

              {card.details && card.details.length > 0 && (
                <div className="border-t border-slate-700 pt-4 mb-4">
                  <h4 className="text-xs font-medium text-slate-400 mb-3">DETAILS</h4>
                  <div className="space-y-2">
                    {card.details.map((detail, idx) => (
                      <div key={idx} className="flex items-center justify-between">
                        <span className="text-sm text-slate-400">{detail.label}</span>
                        <span className="text-sm font-medium text-white">{detail.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {card.drillDownType && (
                <button
                  onClick={() => onLoadDrillDown(card.drillDownType as DrillDownView)}
                  className="w-full flex items-center justify-between p-3 bg-slate-700/50 hover:bg-slate-700 rounded-lg transition-colors group"
                >
                  <span className="text-sm text-slate-300 group-hover:text-white">
                    View all {card.label.toLowerCase()}
                  </span>
                  <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-white" />
                </button>
              )}
            </>
          ) : (
            renderDrillDownContent()
          )}
        </div>
      </div>
    </div>
  )
}
