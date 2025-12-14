import { useEffect } from 'react'
import * as d3 from 'd3'
import { VelocityChartsProps } from './types'

export default function VelocityCharts({ data }: VelocityChartsProps) {
  useEffect(() => {
    if (!data) return

    // Draw line chart for heuristics over time
    drawLineChart('heuristics-chart', data.heuristics_by_day, 'count', '#3b82f6', 'Heuristics')

    // Draw stacked bar chart for learnings
    drawStackedBarChart('learnings-chart', data.learnings_by_day)

    // Draw confidence trend
    drawLineChart('confidence-chart', data.confidence_by_day, 'avg_confidence', '#10b981', 'Confidence')
  }, [data])

  const drawLineChart = (
    elementId: string,
    chartData: any[],
    valueKey: string,
    color: string,
    _label: string
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
    })).filter((d): d is { date: Date; value: number } => d.date !== null)

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
    })).filter((d): d is { date: Date; successes: number; failures: number } => d.date !== null)

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
      .call(d3.axisBottom(x).tickFormat((_, i) => {
        const date = data[i]?.date
        if (!date) return ''
        return d3.timeFormat('%m/%d')(date)
      }).tickValues(x.domain().filter((_, i) => i % Math.ceil(data.length / 5) === 0)))
      .attr('color', '#94a3b8')

    svg.append('g')
      .call(d3.axisLeft(y).ticks(5))
      .attr('color', '#94a3b8')
  }

  return (
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
  )
}
