import { useState, useEffect } from 'react'
import { SpikeReport } from '../types'
import { FileSearch, Search, Filter, ChevronDown, Clock, Star, Tag, BookOpen, AlertCircle, ExternalLink } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { useAPI } from '../hooks/useAPI'

interface SpikeReportsPanelProps {
  className?: string
}

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

  // Load reports
  useEffect(() => {
    loadReports()
  }, [domainFilter, tagFilter])

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchQuery) {
        searchReports()
      } else {
        loadReports()
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery])

  const loadReports = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (domainFilter !== 'all') params.append('domain', domainFilter)
      if (tagFilter !== 'all') params.append('tags', tagFilter)

      const data = await api.get(`/api/spike-reports?${params.toString()}`)
      setReports(data || [])

      // Extract unique domains and tags
      const uniqueDomains = Array.from(new Set(data?.map((r: SpikeReport) => r.domain).filter(Boolean))) as string[]
      setDomains(uniqueDomains)

      const tags = data?.flatMap((r: SpikeReport) => r.tags?.split(',').map(t => t.trim()) || []).filter(Boolean) || []
      setAllTags(Array.from(new Set(tags)))
    } catch (err) {
      console.error('Failed to load spike reports:', err)
    } finally {
      setLoading(false)
    }
  }

  const searchReports = async () => {
    setLoading(true)
    try {
      const data = await api.get(`/api/spike-reports/search?q=${encodeURIComponent(searchQuery)}`)
      setReports(data || [])
    } catch (err) {
      console.error('Failed to search spike reports:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleRate = async (id: number, score: number) => {
    setRatingLoading(id)
    try {
      await api.post(`/api/spike-reports/${id}/rate`, { score })
      // Update locally
      setReports(prev => prev.map(r =>
        r.id === id ? { ...r, usefulness_score: score } : r
      ))
    } catch (err) {
      console.error('Failed to rate spike report:', err)
    } finally {
      setRatingLoading(null)
    }
  }

  const StarRating = ({ score, onChange, loading }: { score: number; onChange?: (score: number) => void; loading?: boolean }) => {
    const [hover, setHover] = useState<number | null>(null)

    return (
      <div className="flex items-center space-x-1">
        {[1, 2, 3, 4, 5].map(star => (
          <button
            key={star}
            onClick={(e) => { e.stopPropagation(); onChange?.(star) }}
            onMouseEnter={() => setHover(star)}
            onMouseLeave={() => setHover(null)}
            disabled={loading}
            className="transition-colors disabled:opacity-50"
          >
            <Star
              className={`w-4 h-4 ${
                (hover !== null ? star <= hover : star <= score)
                  ? 'fill-amber-400 text-amber-400'
                  : 'text-slate-500'
              }`}
            />
          </button>
        ))}
      </div>
    )
  }

  return (
    <div className={`bg-slate-800 rounded-lg p-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <FileSearch className="w-5 h-5 text-violet-400" />
          <h3 className="text-lg font-semibold text-white">Spike Reports</h3>
          <span className="text-sm text-slate-400">({reports.length})</span>
        </div>

        <div className="flex items-center space-x-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search findings..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-slate-700 text-sm text-white rounded-lg pl-9 pr-4 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500 w-64"
            />
          </div>

          {/* Domain filter */}
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <select
              value={domainFilter}
              onChange={(e) => setDomainFilter(e.target.value)}
              className="bg-slate-700 text-sm text-white rounded-md px-3 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500"
            >
              <option value="all">All Domains</option>
              {domains.map(domain => (
                <option key={domain} value={domain}>{domain}</option>
              ))}
            </select>
          </div>

          {/* Tag filter */}
          <select
            value={tagFilter}
            onChange={(e) => setTagFilter(e.target.value)}
            className="bg-slate-700 text-sm text-white rounded-md px-3 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500"
          >
            <option value="all">All Tags</option>
            {allTags.map(tag => (
              <option key={tag} value={tag}>{tag}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Reports grid */}
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
          reports.map(report => {
            const isExpanded = expandedId === report.id
            const isRating = ratingLoading === report.id

            return (
              <div
                key={report.id}
                className={`bg-slate-700/50 rounded-lg border border-transparent transition-all cursor-pointer hover:bg-slate-700/70
                  ${isExpanded ? 'ring-2 ring-violet-500/50 md:col-span-2' : ''}`}
                onClick={() => setExpandedId(isExpanded ? null : report.id)}
              >
                {/* Card header */}
                <div className="p-4">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-1">
                        {report.domain && (
                          <span className="px-2 py-0.5 rounded bg-violet-500/20 text-violet-400 text-xs">
                            {report.domain}
                          </span>
                        )}
                        <span className="px-2 py-0.5 rounded bg-slate-600 text-slate-300 text-xs">
                          {report.topic}
                        </span>
                      </div>
                      <h4 className="text-sm font-medium text-white truncate">{report.title}</h4>
                    </div>

                    {/* Time invested badge */}
                    {report.time_invested_minutes && (
                      <div className="flex items-center space-x-1 px-2 py-1 bg-sky-500/20 rounded text-sky-400 text-xs flex-shrink-0 ml-2">
                        <Clock className="w-3 h-3" />
                        <span>{report.time_invested_minutes} min</span>
                      </div>
                    )}
                  </div>

                  {/* Question */}
                  <div className="text-sm text-slate-300 mb-3">
                    <span className="text-slate-400">Q: </span>
                    {report.question}
                  </div>

                  {/* Tags */}
                  {report.tags && (
                    <div className="flex flex-wrap gap-1 mb-3">
                      {report.tags.split(',').map((tag, idx) => (
                        <span key={idx} className="flex items-center space-x-1 px-1.5 py-0.5 bg-slate-600 rounded text-xs text-slate-300">
                          <Tag className="w-2.5 h-2.5" />
                          <span>{tag.trim()}</span>
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Footer */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <StarRating
                        score={report.usefulness_score}
                        onChange={(score) => handleRate(report.id, score)}
                        loading={isRating}
                      />
                      <span className="text-xs text-slate-400">
                        {report.access_count} views
                      </span>
                    </div>
                    <div className="text-xs text-slate-400">
                      {formatDistanceToNow(new Date(report.created_at), { addSuffix: true })}
                    </div>
                  </div>
                </div>

                {/* Expanded content */}
                {isExpanded && (
                  <div className="px-4 pb-4 border-t border-slate-600">
                    <div className="pt-4 space-y-4">
                      {/* Findings */}
                      <div>
                        <div className="flex items-center space-x-2 text-sm font-medium text-white mb-2">
                          <BookOpen className="w-4 h-4 text-emerald-400" />
                          <span>Findings</span>
                        </div>
                        <div className="text-sm text-slate-300 bg-slate-800/50 rounded p-3 whitespace-pre-wrap">
                          {report.findings}
                        </div>
                      </div>

                      {/* Gotchas */}
                      {report.gotchas && (
                        <div>
                          <div className="flex items-center space-x-2 text-sm font-medium text-white mb-2">
                            <AlertCircle className="w-4 h-4 text-amber-400" />
                            <span>Gotchas</span>
                          </div>
                          <div className="text-sm text-slate-300 bg-amber-500/10 rounded p-3 border border-amber-500/20 whitespace-pre-wrap">
                            {report.gotchas}
                          </div>
                        </div>
                      )}

                      {/* Resources */}
                      {report.resources && (
                        <div>
                          <div className="flex items-center space-x-2 text-sm font-medium text-white mb-2">
                            <ExternalLink className="w-4 h-4 text-sky-400" />
                            <span>Resources</span>
                          </div>
                          <div className="text-sm text-slate-300 bg-slate-800/50 rounded p-3 whitespace-pre-wrap">
                            {report.resources}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
