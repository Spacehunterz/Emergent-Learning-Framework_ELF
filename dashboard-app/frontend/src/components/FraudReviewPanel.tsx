import { useState, useEffect } from 'react'
import { FraudReport } from '../types'
import { Shield } from 'lucide-react'
import { useAPI } from '../hooks/useAPI'
import {
  ReportCard,
  FraudReviewPanelProps,
  ReviewOutcome,
} from './fraud-review'

export default function FraudReviewPanel({ className = '' }: FraudReviewPanelProps) {
  const api = useAPI()

  const [reports, setReports] = useState<FraudReport[]>([])
  const [selectedReport, setSelectedReport] = useState<FraudReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [actionLoading, setActionLoading] = useState<number | null>(null)

  useEffect(() => {
    loadReports()
  }, [])

  const loadReports = async () => {
    setLoading(true)
    try {
      const data = await api.get('/api/fraud-reports')
      setReports(data || [])
    } catch (err) {
      console.error('Failed to load fraud reports:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadReportDetails = async (reportId: number) => {
    try {
      const data = await api.get(`/api/fraud-reports/${reportId}`)
      setSelectedReport(data)
      setExpandedId(reportId)
    } catch (err) {
      console.error('Failed to load report details:', err)
    }
  }

  const handleReview = async (reportId: number, outcome: ReviewOutcome) => {
    setActionLoading(reportId)
    try {
      await api.post(`/api/fraud-reports/${reportId}/review`, {
        outcome,
        reviewed_by: 'human',
        notes: null
      })

      setReports(prev => prev.filter(r => r.id !== reportId))
      setSelectedReport(null)
      setExpandedId(null)
    } catch (err) {
      console.error('Failed to review report:', err)
    } finally {
      setActionLoading(null)
    }
  }

  const handleToggle = (reportId: number) => {
    if (expandedId === reportId) {
      setExpandedId(null)
      setSelectedReport(null)
    } else {
      loadReportDetails(reportId)
    }
  }

  if (loading) {
    return (
      <div className={`p-6 ${className}`}>
        <div className="flex items-center space-x-2 text-gray-400">
          <Shield className="w-5 h-5 animate-pulse" />
          <span>Loading fraud reports...</span>
        </div>
      </div>
    )
  }

  if (reports.length === 0) {
    return (
      <div className={`p-6 ${className}`}>
        <div className="text-center py-12">
          <Shield className="w-16 h-16 mx-auto text-emerald-500/50 mb-4" />
          <h3 className="text-lg font-medium text-gray-300 mb-2">No Pending Fraud Reports</h3>
          <p className="text-gray-400 text-sm">All fraud alerts have been reviewed!</p>
        </div>
      </div>
    )
  }

  return (
    <div className={`p-6 ${className}`}>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <Shield className="w-6 h-6 text-red-400" />
          <h2 className="text-xl font-semibold text-gray-100">Fraud Reports</h2>
          <span className="px-2 py-0.5 rounded bg-red-500/20 text-red-400 text-xs font-medium">
            {reports.length} Pending
          </span>
        </div>
      </div>

      <div className="space-y-4">
        {reports.map(report => (
          <ReportCard
            key={report.id}
            report={report}
            isExpanded={expandedId === report.id}
            isLoading={actionLoading === report.id}
            selectedReport={selectedReport}
            onToggle={() => handleToggle(report.id)}
            onReview={handleReview}
          />
        ))}
      </div>
    </div>
  )
}
