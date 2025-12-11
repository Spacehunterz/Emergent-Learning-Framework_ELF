import { useEffect, useState } from 'react'
import { TrendingUp, TrendingDown, Minus, Flame, Calendar, Brain, CheckCircle } from 'lucide-react'
import * as d3 from 'd3'

interface LearningVelocityData {
  heuristics_by_day: Array<{ date: string; count: number }>
  learnings_by_day: Array<{ date: string; total: number; failures: number; successes: number }>
  promotions_by_day: Array<{ date: string; count: number }>
  confidence_by_day: Array<{ date: string; avg_confidence: number }>
  heuristics_by_week: Array<{ week: string; heuristics_count: number }>
  success_trend: Array<{ date: string; total: number; success_ratio: number }>
  current_streak: number
  heuristics_trend: number
  totals: {
    heuristics: number
    learnings: number
    promotions: number
  }
}

interface LearningVelocityProps {
  days?: number
}

export function LearningVelocity({ days = 30 }: LearningVelocityProps) {
  const [data, setData] = useState<LearningVelocityData | null>(null)
  const [loading, setLoading] = useState(true)
  const [timeframe, setTimeframe] = useState(days)

  useEffect(() => {
    fetchData()
  }, [timeframe])

  const fetchData = async () => {
    try {
      setLoading(true)
      const response = await fetch(`/api/learning-velocity?days=${timeframe}`)
      const result = await response.json()
      setData(result)
    } catch (error) {
      console.error('Failed to fetch learning velocity:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!data || loading) return

    // Draw line chart for heuristics over time
    drawLineChart('heuristics-chart', data.heuristics_by_day, 'count', '#3b82f6', 'Heuristics')

    // Draw stacked bar chart for learnings
    drawStackedBarChart('learnings-chart', data.learnings_by_day)

    // Draw confidence trend
    drawLineChart('confidence-chart', data.confidence_by_day, 'avg_confidence', '#10b981', 'Confidence')
  }, [data, loading])

  const drawLineChart = (
    elementId: string,
    chartData: any[],
    valueKey: string,
    color: string,
    label: string
  ) => {
    const container = document.getElementById(elementId)
    if (!container || !chartData || chartData.length === 0) return

    // Clear previous chart
    d3.select(container).selectAll('*').remove()

    const margin = { top: 20, right: 30, bottom: 30, left: 40 }
    const width = container.clientWidth - margin.left - margin.right
    const height = 200 - margin.top - margin.bottom

    const svg = d3.select(container)
      .append('svg')
      .attr('width', width + margin.left + margin.right)
      .attr('height', height + margin.top + margin.bottom)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`)

    // Parse dates
    const parseDate = d3.timeParse('%Y-%m-%d')
    const data = chartData.map(d => ({
      date: parseDate(d.date),
      value: d[valueKey]
    })).filter(d => d.date !== null)

    if (data.length === 0) return

    // Scales
    const x = d3.scaleTime()
      .domain(d3.extent(data, d => d.date) as [Date, Date])
      .range([0, width])

    const y = d3.scaleLinear()
      .domain([0, d3.max(data, d => d.value) as number])
      .nice()
      .range([height, 0])

    // Grid lines
    svg.append('g')
      .attr('class', 'grid')
      .attr('opacity', 0.1)
      .call(d3.axisLeft(y).tickSize(-width).tickFormat(() => ''))

    // Line
    const line = d3.line<any>()
      .x(d => x(d.date))
      .y(d => y(d.value))
      .curve(d3.curveMonotoneX)

    // Area under line
    const area = d3.area<any>()
      .x(d => x(d.date))
      .y0(height)
      .y1(d => y(d.value))
      .curve(d3.curveMonotoneX)

    svg.append('path')
      .datum(data)
      .attr('fill', color)
      .attr('opacity', 0.1)
      .attr('d', area)

    svg.append('path')
      .datum(data)
      .attr('fill', 'none')
      .attr('stroke', color)
      .attr('stroke-width', 2)
      .attr('d', line)

    // Points
    svg.selectAll('.dot')
      .data(data)
      .enter().append('circle')
      .attr('class', 'dot')
      .attr('cx', d => x(d.date))
      .attr('cy', d => y(d.value))
      .attr('r', 3)
      .attr('fill', color)
      .attr('opacity', 0.8)

    // Axes
    svg.append('g')
      .attr('transform', `translate(0,${height})`)
      .call(d3.axisBottom(x).ticks(5))
      .attr('color', '#94a3b8')

    svg.append('g')
      .call(d3.axisLeft(y).ticks(5))
      .attr('color', '#94a3b8')
  }

  const drawStackedBarChart = (elementId: string, chartData: any[]) => {
    const container = document.getElementById(elementId)
    if (!container || !chartData || chartData.length === 0) return

    // Clear previous chart
    d3.select(container).selectAll('*').remove()

    const margin = { top: 20, right: 30, bottom: 30, left: 40 }
    const width = container.clientWidth - margin.left - margin.right
    const height = 200 - margin.top - margin.bottom

    const svg = d3.select(container)
      .append('svg')
      .attr('width', width + margin.left + margin.right)
      .attr('height', height + margin.top + margin.bottom)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`)

    // Parse dates
    const parseDate = d3.timeParse('%Y-%m-%d')
    const data = chartData.map(d => ({
      date: parseDate(d.date),
      successes: d.successes || 0,
      failures: d.failures || 0
    })).filter(d => d.date !== null)

    if (data.length === 0) return

    // Scales
    const x = d3.scaleBand()
      .domain(data.map(d => d.date.toISOString()))
      .range([0, width])
      .padding(0.2)

    const y = d3.scaleLinear()
      .domain([0, d3.max(data, d => d.successes + d.failures) as number])
      .nice()
      .range([height, 0])

    // Stack the data
    const stack = d3.stack<any>()
      .keys(['successes', 'failures'])

    const series = stack(data)

    // Colors
    const colors = {
      successes: '#10b981',
      failures: '#ef4444'
    }

    // Draw bars
    svg.selectAll('g.series')
      .data(series)
      .enter().append('g')
      .attr('class', 'series')
      .attr('fill', d => colors[d.key as keyof typeof colors])
      .selectAll('rect')
      .data(d => d)
      .enter().append('rect')
      .attr('x', d => x((d.data.date as Date).toISOString()) || 0)
      .attr('y', d => y(d[1]))
      .attr('height', d => y(d[0]) - y(d[1]))
      .attr('width', x.bandwidth())

    // Axes
    svg.append('g')
      .attr('transform', `translate(0,${height})`)
      .call(d3.axisBottom(x).tickFormat((d, i) => {
        const date = data[i]?.date
        if (!date) return ''
        return d3.timeFormat('%m/%d')(date)
      }).tickValues(x.domain().filter((_, i) => i % Math.ceil(data.length / 5) === 0)))
      .attr('color', '#94a3b8')

    svg.append('g')
      .call(d3.axisLeft(y).ticks(5))
      .attr('color', '#94a3b8')
  }

  const getTrendIcon = (trend: number) => {
    if (trend > 5) return <TrendingUp className="w-4 h-4 text-green-500" />
    if (trend < -5) return <TrendingDown className="w-4 h-4 text-red-500" />
    return <Minus className="w-4 h-4 text-slate-400" />
  }

  if (loading) {
    return (
      <div className="bg-slate-800 rounded-lg p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-slate-700 rounded w-1/3 mb-4"></div>
          <div className="h-40 bg-slate-700 rounded mb-4"></div>
          <div className="h-40 bg-slate-700 rounded"></div>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="bg-slate-800 rounded-lg p-6">
        <p className="text-slate-400">Failed to load learning velocity data</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header with timeframe selector */}
      <div className="bg-slate-800 rounded-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-amber-400 flex items-center gap-2">
              <Brain className="w-6 h-6" />
              Learning Velocity
            </h2>
            <p className="text-slate-400 text-sm mt-1">
              Track how fast your AI is learning and improving
            </p>
          </div>
          <div className="flex gap-2">
            {[7, 14, 30, 60, 90].map(d => (
              <button
                key={d}
                onClick={() => setTimeframe(d)}
                className={`px-3 py-1 rounded text-sm transition-colors ${
                  timeframe === d
                    ? 'bg-amber-500 text-black'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>

        {/* Key Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          {/* Total Heuristics */}
          <div className="bg-gradient-to-br from-blue-500/10 to-blue-600/5 border border-blue-500/20 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-400 text-sm">New Heuristics</span>
              {getTrendIcon(data.heuristics_trend)}
            </div>
            <div className="text-3xl font-bold text-blue-400">{data.totals.heuristics}</div>
            <div className="text-xs text-slate-500 mt-1">
              {data.heuristics_trend > 0 ? '+' : ''}{data.heuristics_trend}% vs last period
            </div>
          </div>

          {/* Total Learnings */}
          <div className="bg-gradient-to-br from-purple-500/10 to-purple-600/5 border border-purple-500/20 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-400 text-sm">Total Learnings</span>
              <Calendar className="w-4 h-4 text-purple-400" />
            </div>
            <div className="text-3xl font-bold text-purple-400">{data.totals.learnings}</div>
            <div className="text-xs text-slate-500 mt-1">
              Successes + Failures
            </div>
          </div>

          {/* Golden Rules */}
          <div className="bg-gradient-to-br from-amber-500/10 to-amber-600/5 border border-amber-500/20 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-400 text-sm">Golden Rules</span>
              <CheckCircle className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-3xl font-bold text-amber-400">{data.totals.promotions}</div>
            <div className="text-xs text-slate-500 mt-1">
              Promoted in period
            </div>
          </div>

          {/* Learning Streak */}
          <div className="bg-gradient-to-br from-orange-500/10 to-orange-600/5 border border-orange-500/20 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-400 text-sm">Learning Streak</span>
              <Flame className="w-4 h-4 text-orange-400" />
            </div>
            <div className="text-3xl font-bold text-orange-400">{data.current_streak}</div>
            <div className="text-xs text-slate-500 mt-1">
              Consecutive days
            </div>
          </div>
        </div>

        {/* ROI Summary */}
        <div className="bg-gradient-to-r from-green-500/10 to-emerald-600/10 border border-green-500/30 rounded-lg p-4 mb-6">
          <h3 className="text-lg font-semibold text-green-400 mb-2">Learning ROI</h3>
          <p className="text-slate-300">
            Your AI learned <span className="text-green-400 font-bold">{data.totals.heuristics} new patterns</span> this {timeframe === 7 ? 'week' : timeframe === 30 ? 'month' : 'period'}.
            {data.totals.promotions > 0 && (
              <span> Promoted <span className="text-amber-400 font-bold">{data.totals.promotions} to golden rules</span> - permanent institutional knowledge.</span>
            )}
            {data.current_streak > 1 && (
              <span> On a <span className="text-orange-400 font-bold">{data.current_streak}-day learning streak</span>!</span>
            )}
          </p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Heuristics Over Time */}
        <div className="bg-slate-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-400 mb-4">Heuristics Over Time</h3>
          <div id="heuristics-chart" className="w-full"></div>
        </div>

        {/* Learnings: Success vs Failure */}
        <div className="bg-slate-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-purple-400 mb-4">
            Learnings: Success vs Failure
          </h3>
          <div className="flex items-center gap-4 mb-2 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-green-500 rounded"></div>
              <span className="text-slate-400">Successes</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-red-500 rounded"></div>
              <span className="text-slate-400">Failures</span>
            </div>
          </div>
          <div id="learnings-chart" className="w-full"></div>
        </div>

        {/* Confidence Trend */}
        <div className="bg-slate-800 rounded-lg p-6 lg:col-span-2">
          <h3 className="text-lg font-semibold text-green-400 mb-4">
            Average Confidence Improvement
          </h3>
          <div id="confidence-chart" className="w-full"></div>
          <p className="text-xs text-slate-500 mt-2">
            Shows average confidence of heuristics updated each day
          </p>
        </div>
      </div>

      {/* Weekly Summary */}
      {data.heuristics_by_week.length > 0 && (
        <div className="bg-slate-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-indigo-400 mb-4">Weekly Activity</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {data.heuristics_by_week.map((week, idx) => (
              <div
                key={week.week}
                className="bg-slate-700/50 rounded-lg p-3 text-center"
              >
                <div className="text-xs text-slate-400 mb-1">Week {idx + 1}</div>
                <div className="text-2xl font-bold text-indigo-400">
                  {week.heuristics_count}
                </div>
                <div className="text-xs text-slate-500">heuristics</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
