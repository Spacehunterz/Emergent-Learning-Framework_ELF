import { useState, useEffect, useCallback } from 'react'
import { SpikeReport } from '../types'
import { FileSearch, Clock } from 'lucide-react'
import { useAPI } from '../hooks/useAPI'
import {
  SpikeReportFilters,
  ReportCard,
  SpikeReportsPanelProps,
} from './spike-reports'

export default function SpikeReportsPanel({ className = '' }: SpikeReportsPanelProps) {
  const api = useAPI()

  const [reports, setReports] = useState<SpikeReport[]>([])
  const [domains, setDomains] = useState<string[]>([])
  const [allTags, setAllTags] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [domainFilter, setDomainFilter] = useState<string>('all')
  const [tagFilter, setTagFilter] = useState<string>('all')
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [ratingLoading, setRatingLoading] = useState<number | null>(null)

  const loadReports = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (domainFilter !== 'all') params.append('domain', domainFilter)
      if (tagFilter !== 'all') params.append('tags', tagFilter)

      const data = await api.get(`/api/spike-reports?${params.toString()}`)
      setReports(data || [])

      const uniqueDomains = Array.from(new Set(data?.map((r: SpikeReport) => r.domain).filter(Boolean))) as string[]
      setDomains(uniqueDomains)

      const tags = data?.flatMap((r: SpikeReport) => r.tags?.split(',').map(t => t.trim()) || []).filter(Boolean) || []
      setAllTags(Array.from(new Set(tags)))
    } catch (err) {
      console.error('Failed to load spike reports:', err)
    } finally {
      setLoading(false)
    }
  }, [api, domainFilter, tagFilter])

  const searchReports = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.get(`/api/spike-reports/search?q=${encodeURIComponent(searchQuery)}`)
      setReports(data || [])
    } catch (err) {
      console.error('Failed to search spike reports:', err)
    } finally {
      setLoading(false)
    }
  }, [api, searchQuery])

  useEffect(() => {
    loadReports()
  }, [loadReports])

  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchQuery) {
        searchReports()
      } else {
        loadReports()
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery, searchReports, loadReports])

  const handleRate = async (id: number, score: number) => {
    setRatingLoading(id)
    try {
      await api.post(`/api/spike-reports/${id}/rate`, { score })
      setReports(prev => prev.map(r =>
        r.id === id ? { ...r, usefulness_score: score } : r
      ))
    } catch (err) {
      console.error('Failed to rate spike report:', err)
    } finally {
      setRatingLoading(null)
    }
  }

  return (
    <div className={`bg-slate-800 rounded-lg p-4 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <FileSearch className="w-5 h-5 text-violet-400" />
          <h3 className="text-lg font-semibold text-white">Spike Reports</h3>
          <span className="text-sm text-slate-400">({reports.length})</span>
        </div>

        <SpikeReportFilters
          searchQuery={searchQuery}
          domainFilter={domainFilter}
          tagFilter={tagFilter}
          domains={domains}
          tags={allTags}
          onSearchChange={setSearchQuery}
          onDomainChange={setDomainFilter}
          onTagChange={setTagFilter}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[600px] overflow-y-auto pr-2">
        {loading ? (
          <div className="col-span-2 text-center text-slate-400 py-12">
            <Clock className="w-8 h-8 mx-auto mb-2 animate-spin" />
            Loading spike reports...
          </div>
        ) : reports.length === 0 ? (
          <div className="col-span-2 text-center text-slate-400 py-12">
            No spike reports found
          </div>
        ) : (
          reports.map(report => (
            <ReportCard
              key={report.id}
              report={report}
              isExpanded={expandedId === report.id}
              isRating={ratingLoading === report.id}
              onToggle={() => setExpandedId(expandedId === report.id ? null : report.id)}
              onRate={handleRate}
            />
          ))
        )}
      </div>
    </div>
  )
}
