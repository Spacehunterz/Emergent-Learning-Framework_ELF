import { useState, useRef, useEffect } from 'react'
import {
  Bell, ChevronDown, Inbox, AlertTriangle, Star, X,
  TrendingDown, Repeat, Target, AlertCircle, Zap, FileText
} from 'lucide-react'
import { CeoItem, priorityColors } from './types'

// API anomaly format
interface ApiAnomaly {
  type: string
  severity: string
  message: string
  data: Record<string, any>
}

interface GoldenRule {
  id: string
  rule: string
  explanation?: string
  domain?: string
  times_validated?: number
  confidence?: number
}

interface NotificationCenterProps {
  // CEO Inbox props
  ceoItems: CeoItem[]
  onCeoItemClick: (item: CeoItem) => void
  // Alerts props
  anomalies: ApiAnomaly[]
  goldenRules: GoldenRule[]
  onDismissAnomaly: (index: number) => void
}

type TabType = 'alerts' | 'ceo'

const anomalyConfig: Record<string, { icon: any; color: string; bg: string; border: string }> = {
  repeated_failure: { icon: Repeat, color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/30' },
  confidence_drop: { icon: TrendingDown, color: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/30' },
  new_hotspot: { icon: Target, color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30' },
  hotspot_surge: { icon: Target, color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30' },
  heuristic_violations: { icon: AlertCircle, color: 'text-violet-400', bg: 'bg-violet-500/10', border: 'border-violet-500/30' },
  stale_run: { icon: Zap, color: 'text-pink-400', bg: 'bg-pink-500/10', border: 'border-pink-500/30' },
}

const severityColors: Record<string, string> = {
  info: 'text-slate-400',
  warning: 'text-amber-400',
  error: 'text-red-400',
  low: 'text-slate-400',
  medium: 'text-amber-400',
  high: 'text-orange-400',
  critical: 'text-red-400',
}

export default function NotificationCenter({
  ceoItems,
  onCeoItemClick,
  anomalies,
  goldenRules,
  onDismissAnomaly,
}: NotificationCenterProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<TabType>('alerts')
  const [alertSubTab, setAlertSubTab] = useState<'anomalies' | 'rules'>('anomalies')
  const buttonRef = useRef<HTMLButtonElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const pendingCeoItems = ceoItems.filter(item => item.status === 'Pending')
  const anomalyCount = anomalies?.length || 0
  const rulesCount = goldenRules?.length || 0
  const alertsCount = anomalyCount + rulesCount
  const ceoCount = pendingCeoItems.length
  const totalCount = alertsCount + ceoCount

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        buttonRef.current?.contains(event.target as Node) ||
        dropdownRef.current?.contains(event.target as Node)
      ) {
        return
      }
      setIsOpen(false)
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsOpen(!isOpen)
  }

  return (
    <div className="relative">
      {/* Toggle Button */}
      <button
        ref={buttonRef}
        onClick={handleToggle}
        className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
          totalCount > 0
            ? 'bg-amber-500/20 text-amber-400 hover:bg-amber-500/30'
            : 'bg-white/5 text-white/60 hover:text-white hover:bg-white/10'
        }`}
      >
        <Bell className="w-4 h-4" />
        <span>Notifications</span>
        {totalCount > 0 && (
          <span className="bg-amber-500 text-black text-xs font-bold px-1.5 py-0.5 rounded-full">
            {totalCount}
          </span>
        )}
        <ChevronDown className={`w-3 h-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <div
          ref={dropdownRef}
          className="absolute right-0 top-full mt-2 w-[380px] rounded-xl shadow-2xl overflow-hidden z-[9999] glass-panel border border-white/10 translate-x-4"
          style={{ backgroundColor: 'rgba(15, 23, 42, 0.95)' }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="p-3 border-b border-white/10 bg-black/20 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Bell className="w-4 h-4 text-violet-400" />
              Notifications
            </h3>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1 text-slate-400 hover:text-white rounded transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Main Tab Buttons - Alerts | CEO Inbox */}
          <div className="flex border-b border-white/10">
            <button
              type="button"
              onClick={() => setActiveTab('alerts')}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition-colors cursor-pointer ${
                activeTab === 'alerts'
                  ? 'text-amber-400 bg-amber-500/10 border-b-2 border-amber-400'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <AlertTriangle className="w-4 h-4" />
              <span>Alerts</span>
              {alertsCount > 0 && (
                <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                  activeTab === 'alerts'
                    ? 'bg-amber-500/30 text-amber-300'
                    : 'bg-slate-600 text-slate-300'
                }`}>
                  {alertsCount}
                </span>
              )}
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('ceo')}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition-colors cursor-pointer ${
                activeTab === 'ceo'
                  ? 'text-violet-400 bg-violet-500/10 border-b-2 border-violet-400'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <Inbox className="w-4 h-4" />
              <span>CEO Inbox</span>
              {ceoCount > 0 && (
                <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                  activeTab === 'ceo'
                    ? 'bg-violet-500/30 text-violet-300'
                    : 'bg-slate-600 text-slate-300'
                }`}>
                  {ceoCount}
                </span>
              )}
            </button>
          </div>

          {/* Content Area */}
          <div className="max-h-[400px] overflow-y-auto custom-scrollbar">
            {activeTab === 'alerts' && (
              <AlertsContent
                anomalies={anomalies}
                goldenRules={goldenRules}
                onDismissAnomaly={onDismissAnomaly}
                activeSubTab={alertSubTab}
                setActiveSubTab={setAlertSubTab}
              />
            )}
            {activeTab === 'ceo' && (
              <CeoContent
                items={ceoItems}
                onItemClick={onCeoItemClick}
              />
            )}
          </div>

          {/* Footer */}
          <div className="p-2 border-t border-white/10 bg-black/20">
            <p className="text-[10px] text-slate-500 text-center uppercase tracking-widest">
              {activeTab === 'alerts'
                ? `${anomalyCount} anomalies · ${rulesCount} rules`
                : `${ceoCount} pending · ${ceoItems.length} total`
              }
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

// Alerts Content with sub-tabs
function AlertsContent({
  anomalies,
  goldenRules,
  onDismissAnomaly,
  activeSubTab,
  setActiveSubTab,
}: {
  anomalies: ApiAnomaly[]
  goldenRules: GoldenRule[]
  onDismissAnomaly: (index: number) => void
  activeSubTab: 'anomalies' | 'rules'
  setActiveSubTab: (tab: 'anomalies' | 'rules') => void
}) {
  const anomalyCount = anomalies?.length || 0
  const rulesCount = goldenRules?.length || 0

  return (
    <div>
      {/* Sub-tabs */}
      <div className="flex border-b border-white/5 bg-black/10">
        <button
          type="button"
          onClick={() => setActiveSubTab('anomalies')}
          className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 text-xs font-medium transition-colors cursor-pointer ${
            activeSubTab === 'anomalies'
              ? 'text-amber-400 border-b border-amber-400/50'
              : 'text-slate-500 hover:text-white'
          }`}
        >
          <AlertTriangle className="w-3 h-3" />
          <span>Anomalies</span>
          {anomalyCount > 0 && (
            <span className="text-[10px] px-1 rounded bg-amber-500/20 text-amber-300">
              {anomalyCount}
            </span>
          )}
        </button>
        <button
          type="button"
          onClick={() => setActiveSubTab('rules')}
          className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 text-xs font-medium transition-colors cursor-pointer ${
            activeSubTab === 'rules'
              ? 'text-amber-400 border-b border-amber-400/50'
              : 'text-slate-500 hover:text-white'
          }`}
        >
          <Star className="w-3 h-3" />
          <span>Golden Rules</span>
          {rulesCount > 0 && (
            <span className="text-[10px] px-1 rounded bg-amber-500/20 text-amber-300">
              {rulesCount}
            </span>
          )}
        </button>
      </div>

      {/* Sub-tab Content */}
      <div className="p-3">
        {activeSubTab === 'anomalies' && (
          <AnomaliesContent anomalies={anomalies} onDismiss={onDismissAnomaly} />
        )}
        {activeSubTab === 'rules' && (
          <GoldenRulesContent rules={goldenRules} />
        )}
      </div>
    </div>
  )
}

function AnomaliesContent({
  anomalies,
  onDismiss
}: {
  anomalies: ApiAnomaly[]
  onDismiss: (index: number) => void
}) {
  if (!anomalies || anomalies.length === 0) {
    return (
      <div className="text-center text-slate-400 py-6 text-sm">
        <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-slate-500" />
        <p>No anomalies detected</p>
        <p className="text-xs text-slate-500 mt-1">System is running normally</p>
      </div>
    )
  }

  return (
    <div className="space-y-2 max-h-[280px] overflow-y-auto pr-1">
      {anomalies.map((anomaly, index) => {
        const config = anomalyConfig[anomaly.type] || {
          icon: AlertCircle,
          color: 'text-slate-400',
          bg: 'bg-slate-500/10',
          border: 'border-slate-500/30'
        }
        const Icon = config.icon

        return (
          <div
            key={`anomaly-${index}-${anomaly.type}`}
            className={`${config.bg} border ${config.border} rounded-lg p-2.5 relative`}
          >
            <button
              onClick={() => onDismiss(index)}
              className="absolute top-2 right-2 p-1 text-slate-400 hover:text-white transition"
            >
              <X className="w-3 h-3" />
            </button>

            <div className="flex items-start space-x-2 pr-5">
              <div className={`p-1 rounded ${config.bg}`}>
                <Icon className={`w-3.5 h-3.5 ${config.color}`} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2 mb-0.5">
                  <span className="text-xs font-medium text-white">
                    {anomaly.type.replace(/_/g, ' ')}
                  </span>
                  <span className={`text-xs ${severityColors[anomaly.severity] || 'text-slate-400'}`}>
                    {anomaly.severity}
                  </span>
                </div>
                <p className="text-xs text-slate-300 line-clamp-2">{anomaly.message}</p>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function GoldenRulesContent({ rules }: { rules: GoldenRule[] }) {
  if (!rules || rules.length === 0) {
    return (
      <div className="text-center text-slate-400 py-6 text-sm">
        <Star className="w-8 h-8 mx-auto mb-2 text-slate-500" />
        <p>No golden rules yet</p>
        <p className="text-xs text-slate-500 mt-1">Promote high-confidence heuristics</p>
      </div>
    )
  }

  return (
    <div className="space-y-2 max-h-[280px] overflow-y-auto pr-1">
      {rules.map((rule, idx) => (
        <div
          key={rule.id || idx}
          className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-2.5"
        >
          <div className="flex items-start gap-2">
            <Star className="w-3.5 h-3.5 text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-xs text-white font-medium line-clamp-2">{rule.rule}</p>
              <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                <span className="text-xs bg-amber-500/20 px-1.5 py-0.5 rounded text-amber-300">
                  {rule.domain || 'general'}
                </span>
                {rule.times_validated !== undefined && rule.times_validated > 0 && (
                  <span className="text-xs text-slate-500">
                    {rule.times_validated}x
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

// CEO Inbox Content
function CeoContent({
  items,
  onItemClick,
}: {
  items: CeoItem[]
  onItemClick: (item: CeoItem) => void
}) {
  if (items.length === 0) {
    return (
      <div className="p-8 text-center text-slate-400 text-sm">
        <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center mx-auto mb-3">
          <Inbox className="w-6 h-6 opacity-50" />
        </div>
        No items in inbox
      </div>
    )
  }

  return (
    <div>
      {items.map((item) => (
        <button
          key={item.filename}
          onClick={() => onItemClick(item)}
          className="w-full text-left p-3 border-b border-white/5 hover:bg-white/5 transition-colors cursor-pointer group"
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-[10px] px-1.5 py-0.5 rounded border uppercase tracking-wider ${priorityColors[item.priority] || priorityColors.Medium}`}>
                  {item.priority}
                </span>
                <span className={`text-[10px] uppercase tracking-wider ${item.status === 'Pending' ? 'text-amber-400' : 'text-emerald-400'}`}>
                  {item.status}
                </span>
              </div>
              <h4 className="text-sm font-medium text-white truncate group-hover:text-violet-300 transition-colors">{item.title}</h4>
              {item.summary && (
                <p className="text-xs text-slate-400 mt-1 line-clamp-2">{item.summary}</p>
              )}
              {item.date && (
                <p className="text-[10px] text-slate-500 mt-2 font-mono">{item.date}</p>
              )}
            </div>
            <FileText className="w-4 h-4 text-slate-600 flex-shrink-0 mt-1 group-hover:text-white transition-colors" />
          </div>
        </button>
      ))}
    </div>
  )
}
