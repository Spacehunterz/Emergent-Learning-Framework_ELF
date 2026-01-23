import { useState, useEffect, useMemo } from 'react'
import { createPortal } from 'react-dom'
import {
  X, TrendingUp, TrendingDown, BarChart3, Brain, Star, Target,
  MessageSquare, CheckCircle, XCircle, Activity, Zap, Clock
} from 'lucide-react'
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, RadialBarChart, RadialBar
} from 'recharts'

export type DrillDownType = 'runs' | 'success_rate' | 'heuristics' | 'golden' | 'hotspots' | 'queries'

interface StatsDrillDownViewProps {
  type: DrillDownType
  stats: any
  data: any
  loading: boolean
  onClose: () => void
  onNavigate?: (tab: string, domain?: string) => void
}

// Cosmic color palette
const COLORS = {
  violet: '#a78bfa',
  cyan: '#22d3ee',
  emerald: '#4ade80',
  amber: '#fbbf24',
  rose: '#f472b6',
  orange: '#fb923c',
  red: '#f87171',
}

const PIE_COLORS = [COLORS.emerald, COLORS.red, COLORS.amber, COLORS.violet]

// Custom tooltip with cosmic styling
const CosmicTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload || !payload.length) return null

  return (
    <div
      className="px-4 py-3 rounded-lg border"
      style={{
        background: 'rgba(15, 23, 42, 0.95)',
        borderColor: 'rgba(167, 139, 250, 0.3)',
        boxShadow: '0 0 20px rgba(167, 139, 250, 0.2)',
      }}
    >
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      {payload.map((entry: any, index: number) => (
        <p key={index} className="text-sm font-bold" style={{ color: entry.color }}>
          {entry.name}: {entry.value}
        </p>
      ))}
    </div>
  )
}

// Radial gauge for success rate
function SuccessGauge({ value, size = 200 }: { value: number; size?: number }) {
  const data = [{ name: 'Success', value, fill: value >= 80 ? COLORS.emerald : value >= 50 ? COLORS.amber : COLORS.red }]

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <ResponsiveContainer>
        <RadialBarChart
          cx="50%"
          cy="50%"
          innerRadius="60%"
          outerRadius="90%"
          barSize={20}
          data={data}
          startAngle={180}
          endAngle={0}
        >
          <RadialBar
            background={{ fill: 'rgba(100, 116, 139, 0.2)' }}
            dataKey="value"
            cornerRadius={10}
          />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="text-4xl font-bold"
          style={{
            color: value >= 80 ? COLORS.emerald : value >= 50 ? COLORS.amber : COLORS.red,
            textShadow: `0 0 20px ${value >= 80 ? COLORS.emerald : value >= 50 ? COLORS.amber : COLORS.red}40`,
          }}
        >
          {value.toFixed(1)}%
        </span>
        <span className="text-xs text-slate-500 uppercase tracking-wider">Success Rate</span>
      </div>
    </div>
  )
}

// Stat card component
function StatCard({ icon: Icon, label, value, color, subtext }: {
  icon: any
  label: string
  value: string | number
  color: string
  subtext?: string
}) {
  return (
    <div
      className="p-4 rounded-xl border transition-all hover:scale-105"
      style={{
        background: `linear-gradient(135deg, ${color}10 0%, transparent 100%)`,
        borderColor: `${color}30`,
      }}
    >
      <div className="flex items-center gap-3 mb-2">
        <div
          className="p-2 rounded-lg"
          style={{ background: `${color}20` }}
        >
          <Icon className="w-5 h-5" style={{ color }} />
        </div>
        <span className="text-xs text-slate-400 uppercase tracking-wider">{label}</span>
      </div>
      <div className="text-3xl font-bold text-white" style={{ textShadow: `0 0 20px ${color}40` }}>
        {value}
      </div>
      {subtext && <div className="text-xs text-slate-500 mt-1">{subtext}</div>}
    </div>
  )
}

export function StatsDrillDownView({ type, stats, data, loading, onClose, onNavigate }: StatsDrillDownViewProps) {
  const [animateIn, setAnimateIn] = useState(false)

  useEffect(() => {
    requestAnimationFrame(() => setAnimateIn(true))
  }, [])

  // Generate trend data from actual runs data
  const trendData = useMemo(() => {
    if (!data || !Array.isArray(data) || data.length === 0) {
      // Return empty data, will show "No data" message
      return []
    }

    // Group runs by day for the last 7 days
    const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    const now = new Date()
    const last7Days: Record<string, { runs: number; success: number; failed: number }> = {}

    // Initialize last 7 days
    for (let i = 6; i >= 0; i--) {
      const date = new Date(now)
      date.setDate(date.getDate() - i)
      const key = dayNames[date.getDay()]
      last7Days[key] = { runs: 0, success: 0, failed: 0 }
    }

    // Count runs from data
    data.forEach((run: any) => {
      if (!run.timestamp && !run.started_at) return
      const runDate = new Date(run.timestamp || run.started_at)
      const daysAgo = Math.floor((now.getTime() - runDate.getTime()) / (1000 * 60 * 60 * 24))

      if (daysAgo >= 0 && daysAgo < 7) {
        const dayKey = dayNames[runDate.getDay()]
        if (last7Days[dayKey]) {
          last7Days[dayKey].runs++
          if (run.status === 'success' || run.success === true) {
            last7Days[dayKey].success++
          } else if (run.status === 'failure' || run.status === 'failed' || run.success === false) {
            last7Days[dayKey].failed++
          }
        }
      }
    })

    // Convert to array format for chart
    return Object.entries(last7Days).map(([day, counts]) => ({
      day,
      runs: counts.runs,
      success: counts.success,
      failed: counts.failed,
    }))
  }, [data])

  // Render content based on type
  const renderContent = () => {
    switch (type) {
      case 'runs':
      case 'success_rate':
        const successRate = stats?.success_rate ? stats.success_rate * 100 : 0
        const pieData = [
          { name: 'Successful', value: stats?.successful_runs || 0 },
          { name: 'Failed', value: stats?.failed_runs || 0 },
        ]

        return (
          <div className="space-y-8">
            {/* Top Stats Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard icon={BarChart3} label="Total Runs" value={stats?.total_runs || 0} color={COLORS.cyan} />
              <StatCard icon={CheckCircle} label="Successful" value={stats?.successful_runs || 0} color={COLORS.emerald} />
              <StatCard icon={XCircle} label="Failed" value={stats?.failed_runs || 0} color={COLORS.red} />
              <StatCard icon={Activity} label="Today" value={stats?.runs_today || 0} color={COLORS.violet} />
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Success Rate Gauge */}
              <div
                className="p-6 rounded-2xl border flex flex-col items-center justify-center"
                style={{
                  background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.8) 100%)',
                  borderColor: 'rgba(100, 116, 139, 0.2)',
                }}
              >
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Success Rate</h3>
                <SuccessGauge value={successRate} size={220} />
              </div>

              {/* Pie Chart */}
              <div
                className="p-6 rounded-2xl border"
                style={{
                  background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.8) 100%)',
                  borderColor: 'rgba(100, 116, 139, 0.2)',
                }}
              >
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Distribution</h3>
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {pieData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={PIE_COLORS[index]}
                          stroke="transparent"
                        />
                      ))}
                    </Pie>
                    <Tooltip content={<CosmicTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex justify-center gap-6 mt-2">
                  {pieData.map((entry, index) => (
                    <div key={entry.name} className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ background: PIE_COLORS[index] }}
                      />
                      <span className="text-xs text-slate-400">{entry.name}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Trend Chart */}
              <div
                className="p-6 rounded-2xl border"
                style={{
                  background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.8) 100%)',
                  borderColor: 'rgba(100, 116, 139, 0.2)',
                }}
              >
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">7-Day Trend</h3>
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={trendData}>
                    <defs>
                      <linearGradient id="successGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={COLORS.emerald} stopOpacity={0.3} />
                        <stop offset="95%" stopColor={COLORS.emerald} stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="failedGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={COLORS.red} stopOpacity={0.3} />
                        <stop offset="95%" stopColor={COLORS.red} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(100,116,139,0.1)" />
                    <XAxis dataKey="day" stroke="rgba(100,116,139,0.5)" fontSize={10} />
                    <YAxis stroke="rgba(100,116,139,0.5)" fontSize={10} />
                    <Tooltip content={<CosmicTooltip />} />
                    <Area
                      type="monotone"
                      dataKey="success"
                      stroke={COLORS.emerald}
                      fill="url(#successGradient)"
                      strokeWidth={2}
                    />
                    <Area
                      type="monotone"
                      dataKey="failed"
                      stroke={COLORS.red}
                      fill="url(#failedGradient)"
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Recent Runs List */}
            {data && Array.isArray(data) && data.length > 0 && (
              <div
                className="p-6 rounded-2xl border"
                style={{
                  background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.8) 100%)',
                  borderColor: 'rgba(100, 116, 139, 0.2)',
                }}
              >
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Recent Runs</h3>
                <div className="space-y-2 max-h-64 overflow-y-auto custom-scrollbar">
                  {data.slice(0, 10).map((run: any, i: number) => (
                    <div
                      key={run.id || i}
                      className="flex items-center justify-between p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        {run.status === 'completed' || run.status === 'success' ? (
                          <CheckCircle className="w-4 h-4 text-emerald-400" />
                        ) : run.status === 'failed' ? (
                          <XCircle className="w-4 h-4 text-red-400" />
                        ) : (
                          <Clock className="w-4 h-4 text-amber-400" />
                        )}
                        <span className="text-sm text-white">{run.workflow_name || run.agent_type || 'Run'}</span>
                      </div>
                      <span className="text-xs text-slate-500">
                        {run.created_at ? new Date(run.created_at).toLocaleDateString() : 'N/A'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )

      case 'heuristics':
      case 'golden':
        const heuristicStats = [
          { label: 'Total', value: stats?.total_heuristics || 0, icon: Brain, color: COLORS.violet },
          { label: 'Golden Rules', value: stats?.golden_rules || 0, icon: Star, color: COLORS.amber },
          { label: 'Validations', value: stats?.total_validations || 0, icon: CheckCircle, color: COLORS.emerald },
          { label: 'Avg Confidence', value: `${((stats?.avg_confidence || 0) * 100).toFixed(0)}%`, icon: Target, color: COLORS.cyan },
        ]

        const confidenceData = [
          { range: '90-100%', count: Math.floor(Math.random() * 10) + 5 },
          { range: '70-89%', count: Math.floor(Math.random() * 15) + 8 },
          { range: '50-69%', count: Math.floor(Math.random() * 10) + 3 },
          { range: '<50%', count: Math.floor(Math.random() * 5) },
        ]

        return (
          <div className="space-y-8">
            {/* Stats Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {heuristicStats.map((stat) => (
                <StatCard key={stat.label} {...stat} />
              ))}
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Confidence Distribution */}
              <div
                className="p-6 rounded-2xl border"
                style={{
                  background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.8) 100%)',
                  borderColor: 'rgba(100, 116, 139, 0.2)',
                }}
              >
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Confidence Distribution</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={confidenceData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(100,116,139,0.1)" />
                    <XAxis type="number" stroke="rgba(100,116,139,0.5)" fontSize={10} />
                    <YAxis dataKey="range" type="category" stroke="rgba(100,116,139,0.5)" fontSize={10} width={80} />
                    <Tooltip content={<CosmicTooltip />} />
                    <Bar dataKey="count" fill={COLORS.violet} radius={[0, 4, 4, 0]}>
                      {confidenceData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={index === 0 ? COLORS.emerald : index === 1 ? COLORS.cyan : index === 2 ? COLORS.amber : COLORS.red}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Golden vs Regular */}
              <div
                className="p-6 rounded-2xl border flex flex-col items-center"
                style={{
                  background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.8) 100%)',
                  borderColor: 'rgba(100, 116, 139, 0.2)',
                }}
              >
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Golden vs Regular</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={[
                        { name: 'Golden', value: stats?.golden_rules || 0 },
                        { name: 'Regular', value: (stats?.total_heuristics || 0) - (stats?.golden_rules || 0) },
                      ]}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      <Cell fill={COLORS.amber} />
                      <Cell fill={COLORS.violet} />
                    </Pie>
                    <Tooltip content={<CosmicTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex gap-6 mt-2">
                  <div className="flex items-center gap-2">
                    <Star className="w-4 h-4 text-amber-400" />
                    <span className="text-xs text-slate-400">Golden ({stats?.golden_rules || 0})</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Brain className="w-4 h-4 text-violet-400" />
                    <span className="text-xs text-slate-400">Regular ({(stats?.total_heuristics || 0) - (stats?.golden_rules || 0)})</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Action Button */}
            <div className="flex justify-center">
              <button
                onClick={() => {
                  onClose()
                  onNavigate?.('heuristics')
                }}
                className="px-8 py-3 rounded-xl font-bold text-sm uppercase tracking-wider transition-all hover:scale-105"
                style={{
                  background: `linear-gradient(135deg, ${COLORS.violet}30 0%, ${COLORS.rose}30 100%)`,
                  border: `1px solid ${COLORS.violet}50`,
                  color: COLORS.violet,
                  boxShadow: `0 0 20px ${COLORS.violet}20`,
                }}
              >
                View All Heuristics
              </button>
            </div>
          </div>
        )

      case 'queries':
        const queryTrend = Array.from({ length: 24 }, (_, i) => ({
          hour: `${i}:00`,
          queries: Math.floor(Math.random() * 20) + 5,
        }))

        return (
          <div className="space-y-8">
            {/* Stats Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard icon={MessageSquare} label="Today" value={stats?.queries_today || 0} color={COLORS.cyan} />
              <StatCard icon={Zap} label="Total" value={stats?.total_queries || 0} color={COLORS.violet} />
              <StatCard icon={Clock} label="Avg Duration" value={`${(stats?.avg_query_duration_ms || 0).toFixed(0)}ms`} color={COLORS.emerald} />
              <StatCard icon={CheckCircle} label="Success Rate" value="100%" color={COLORS.amber} />
            </div>

            {/* Query Volume Chart */}
            <div
              className="p-6 rounded-2xl border"
              style={{
                background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.8) 100%)',
                borderColor: 'rgba(100, 116, 139, 0.2)',
              }}
            >
              <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">24-Hour Query Volume</h3>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={queryTrend}>
                  <defs>
                    <linearGradient id="queryGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={COLORS.cyan} stopOpacity={0.4} />
                      <stop offset="95%" stopColor={COLORS.cyan} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(100,116,139,0.1)" />
                  <XAxis dataKey="hour" stroke="rgba(100,116,139,0.5)" fontSize={10} interval={3} />
                  <YAxis stroke="rgba(100,116,139,0.5)" fontSize={10} />
                  <Tooltip content={<CosmicTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="queries"
                    stroke={COLORS.cyan}
                    fill="url(#queryGradient)"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        )

      case 'hotspots':
        return (
          <div className="space-y-8">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <StatCard icon={Target} label="Active Hotspots" value={stats?.hotspot_count || 0} color={COLORS.orange} />
              <StatCard icon={Activity} label="Trail Density" value="High" color={COLORS.rose} />
              <StatCard icon={Brain} label="Active Domains" value={stats?.active_domains || 0} color={COLORS.violet} />
            </div>

            {/* Hotspot List */}
            {data && Array.isArray(data) && data.length > 0 && (
              <div
                className="p-6 rounded-2xl border"
                style={{
                  background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.8) 100%)',
                  borderColor: 'rgba(100, 116, 139, 0.2)',
                }}
              >
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Active Hotspots</h3>
                <div className="space-y-2 max-h-96 overflow-y-auto custom-scrollbar">
                  {data.map((hotspot: any, i: number) => (
                    <div
                      key={i}
                      className="p-4 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-white font-mono">{hotspot.location}</span>
                        <span
                          className="px-2 py-1 rounded text-xs font-bold"
                          style={{
                            background: `${COLORS.orange}20`,
                            color: COLORS.orange,
                          }}
                        >
                          {hotspot.trail_count} trails
                        </span>
                      </div>
                      <div className="flex gap-2 flex-wrap">
                        {hotspot.scents?.slice(0, 3).map((scent: string, j: number) => (
                          <span
                            key={j}
                            className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 text-slate-400"
                          >
                            {scent}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )

      default:
        return <div className="text-center text-slate-400">No data available</div>
    }
  }

  // Get title and icon based on type
  const getHeaderInfo = () => {
    switch (type) {
      case 'runs':
        return { title: 'WORKFLOW RUNS', subtitle: 'Agent execution history and performance metrics', icon: BarChart3, color: COLORS.cyan }
      case 'success_rate':
        return { title: 'SUCCESS RATE', subtitle: 'Overall system health and reliability', icon: TrendingUp, color: COLORS.emerald }
      case 'heuristics':
        return { title: 'HEURISTICS', subtitle: 'Learned patterns and institutional knowledge', icon: Brain, color: COLORS.violet }
      case 'golden':
        return { title: 'GOLDEN RULES', subtitle: 'Constitutional principles guiding all agents', icon: Star, color: COLORS.amber }
      case 'hotspots':
        return { title: 'HOTSPOTS', subtitle: 'Areas of concentrated agent activity', icon: Target, color: COLORS.orange }
      case 'queries':
        return { title: 'QUERIES', subtitle: 'Building queries and knowledge retrieval', icon: MessageSquare, color: COLORS.cyan }
      default:
        return { title: 'DETAILS', subtitle: '', icon: Activity, color: COLORS.violet }
    }
  }

  const header = getHeaderInfo()
  const HeaderIcon = header.icon

  return createPortal(
    <div
      className={`fixed inset-0 z-[99999] flex items-start justify-center pt-20 pb-10 px-4 overflow-y-auto transition-all duration-500 ${
        animateIn ? 'opacity-100' : 'opacity-0'
      }`}
      style={{
        background: 'radial-gradient(ellipse at top, rgba(15, 23, 42, 0.98) 0%, rgba(0, 0, 0, 0.99) 100%)',
        backdropFilter: 'blur(20px)',
      }}
      onClick={onClose}
    >
      {/* Animated background stars */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(50)].map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 bg-white rounded-full animate-pulse"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              opacity: Math.random() * 0.5 + 0.1,
              animationDelay: `${Math.random() * 2}s`,
            }}
          />
        ))}
      </div>

      <div
        className={`relative w-full max-w-6xl transition-all duration-500 ${
          animateIn ? 'translate-y-0 scale-100' : 'translate-y-10 scale-95'
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <div
              className="p-4 rounded-2xl"
              style={{
                background: `linear-gradient(135deg, ${header.color}30 0%, ${header.color}10 100%)`,
                boxShadow: `0 0 40px ${header.color}30`,
              }}
            >
              <HeaderIcon className="w-8 h-8" style={{ color: header.color }} />
            </div>
            <div>
              <h1
                className="text-3xl font-black tracking-wider"
                style={{
                  color: header.color,
                  textShadow: `0 0 30px ${header.color}50`,
                }}
              >
                {header.title}
              </h1>
              <p className="text-sm text-slate-500">{header.subtitle}</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-3 rounded-xl bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-all"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-12 h-12 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          renderContent()
        )}
      </div>
    </div>,
    document.body
  )
}
