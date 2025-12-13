import { useState, useEffect } from 'react'
import { FraudReport, AnomalySignal } from '../types'
import { Shield, AlertTriangle, CheckCircle, XCircle, ChevronDown, Eye, Clock, TrendingUp } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { useAPI } from '../hooks/useAPI'

interface FraudReviewPanelProps {
  className?: string
}

export default function FraudReviewPanel({ className = '' }: FraudReviewPanelProps) {
  const api = useAPI()

  const [reports, setReports] = useState<FraudReport[]>([])
  const [selectedReport, setSelectedReport] = useState<FraudReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [actionLoading, setActionLoading] = useState<number | null>(null)

  // Load pending fraud reports
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

  const handleReview = async (reportId: number, outcome: 'true_positive' | 'false_positive') => {
    setActionLoading(reportId)
    try {
      await api.post(`/api/fraud-reports/${reportId}/review`, {
        outcome,
        reviewed_by: 'human',
        notes: null
      })

      // Remove from list after review
      setReports(prev => prev.filter(r => r.id !== reportId))
      setSelectedReport(null)
      setExpandedId(null)
    } catch (err) {
      console.error('Failed to review report:', err)
    } finally {
      setActionLoading(null)
    }
  }

  const getClassificationBadge = (classification: FraudReport['classification']) => {
    const badges = {
      clean: { color: 'bg-emerald-500/20 text-emerald-400', icon: CheckCircle, label: 'Clean' },
      low_confidence: { color: 'bg-gray-500/20 text-gray-400', icon: Shield, label: 'Low Confidence' },
      suspicious: { color: 'bg-amber-500/20 text-amber-400', icon: AlertTriangle, label: 'Suspicious' },
      fraud_likely: { color: 'bg-orange-500/20 text-orange-400', icon: AlertTriangle, label: 'Fraud Likely' },
      fraud_confirmed: { color: 'bg-red-500/20 text-red-400', icon: XCircle, label: 'Fraud Confirmed' }
    }

    const badge = badges[classification] || badges.clean
    const Icon = badge.icon

    return (
      <span className={`flex items-center space-x-1 px-2 py-0.5 rounded ${badge.color} text-xs font-medium`}>
        <Icon className="w-3 h-3" />
        <span>{badge.label}</span>
      </span>
    )
  }

  const getSeverityBadge = (severity: AnomalySignal['severity']) => {
    const colors = {
      low: 'bg-blue-500/20 text-blue-400',
      medium: 'bg-amber-500/20 text-amber-400',
      high: 'bg-orange-500/20 text-orange-400',
      critical: 'bg-red-500/20 text-red-400'
    }

    return (
      <span className={`px-2 py-0.5 rounded ${colors[severity]} text-xs font-medium uppercase`}>
        {severity}
      </span>
    )
  }

  const calculateSuccessRate = (report: FraudReport) => {
    const total = (report.times_validated || 0) + (report.times_violated || 0) + (report.times_contradicted || 0)
    if (total === 0) return 0
    return ((report.times_validated || 0) / total) * 100
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
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <Shield className="w-6 h-6 text-red-400" />
          <h2 className="text-xl font-semibold text-gray-100">Fraud Reports</h2>
          <span className="px-2 py-0.5 rounded bg-red-500/20 text-red-400 text-xs font-medium">
            {reports.length} Pending
          </span>
        </div>
      </div>

      {/* Reports List */}
      <div className="space-y-4">
        {reports.map(report => {
          const isExpanded = expandedId === report.id
          const successRate = calculateSuccessRate(report)

          return (
            <div
              key={report.id}
              className="bg-gray-800/50 border border-gray-700 rounded-lg overflow-hidden hover:border-gray-600 transition-colors"
            >
              {/* Report Header */}
              <div className="p-4">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-2">
                      {getClassificationBadge(report.classification)}
                      <span className="text-xs text-gray-500">
                        Report #{report.id}
                      </span>
                      <span className="text-xs text-gray-500">•</span>
                      <span className="text-xs text-gray-400">
                        {formatDistanceToNow(new Date(report.created_at), { addSuffix: true })}
                      </span>
                    </div>

                    <h3 className="text-sm font-medium text-gray-200 mb-1">
                      [{report.domain}] {report.rule.substring(0, 80)}
                      {report.rule.length > 80 && '...'}
                    </h3>

                    <div className="flex items-center space-x-4 text-xs text-gray-400">
                      <div className="flex items-center space-x-1">
                        <TrendingUp className="w-3 h-3" />
                        <span>Fraud Score: {(report.fraud_score * 100).toFixed(1)}%</span>
                      </div>
                      <div>Success Rate: {successRate.toFixed(1)}%</div>
                      <div>{report.signal_count} signals</div>
                      <div>Confidence: {(report.confidence * 100).toFixed(0)}%</div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2 ml-4">
                    <button
                      onClick={() => {
                        if (isExpanded) {
                          setExpandedId(null)
                          setSelectedReport(null)
                        } else {
                          loadReportDetails(report.id)
                        }
                      }}
                      className="p-1.5 rounded hover:bg-gray-700 text-gray-400 hover:text-gray-200 transition-colors"
                      title="View details"
                    >
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 transform rotate-180" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center space-x-2 mt-4">
                  <button
                    onClick={() => handleReview(report.id, 'true_positive')}
                    disabled={actionLoading === report.id}
                    className="px-3 py-1.5 rounded bg-red-500/20 hover:bg-red-500/30 text-red-400 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {actionLoading === report.id ? 'Processing...' : 'Confirm Fraud'}
                  </button>
                  <button
                    onClick={() => handleReview(report.id, 'false_positive')}
                    disabled={actionLoading === report.id}
                    className="px-3 py-1.5 rounded bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {actionLoading === report.id ? 'Processing...' : 'Mark as Safe'}
                  </button>
                </div>
              </div>

              {/* Expanded Details */}
              {isExpanded && selectedReport && (
                <div className="border-t border-gray-700 bg-gray-900/50 p-4">
                  <h4 className="text-sm font-medium text-gray-300 mb-3">Anomaly Signals</h4>

                  {selectedReport.signals && selectedReport.signals.length > 0 ? (
                    <div className="space-y-3">
                      {selectedReport.signals.map(signal => (
                        <div
                          key={signal.id}
                          className="bg-gray-800/50 border border-gray-700 rounded p-3"
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex-1">
                              <div className="flex items-center space-x-2 mb-1">
                                <span className="text-xs font-mono text-gray-400">{signal.detector_name}</span>
                                {getSeverityBadge(signal.severity)}
                              </div>
                              <p className="text-sm text-gray-300">{signal.reason}</p>
                            </div>
                            <div className="text-right">
                              <div className="text-sm font-medium text-orange-400">
                                {(signal.score * 100).toFixed(0)}%
                              </div>
                              <div className="text-xs text-gray-500">score</div>
                            </div>
                          </div>

                          {signal.evidence && Object.keys(signal.evidence).length > 0 && (
                            <div className="mt-2 pt-2 border-t border-gray-700">
                              <div className="text-xs text-gray-500 mb-1">Evidence:</div>
                              <div className="grid grid-cols-2 gap-2">
                                {Object.entries(signal.evidence).map(([key, value]) => (
                                  <div key={key} className="text-xs">
                                    <span className="text-gray-500">{key}:</span>{' '}
                                    <span className="text-gray-300">
                                      {typeof value === 'number'
                                        ? value.toFixed(3)
                                        : String(value)}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-sm text-gray-500 italic">No signals available</div>
                  )}

                  {/* Heuristic Details */}
                  <div className="mt-4 pt-4 border-t border-gray-700">
                    <h4 className="text-sm font-medium text-gray-300 mb-2">Heuristic Performance</h4>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <div className="text-gray-500">Validated</div>
                        <div className="text-gray-200 font-medium">{selectedReport.times_validated || 0}</div>
                      </div>
                      <div>
                        <div className="text-gray-500">Violated</div>
                        <div className="text-gray-200 font-medium">{selectedReport.times_violated || 0}</div>
                      </div>
                      <div>
                        <div className="text-gray-500">Contradicted</div>
                        <div className="text-gray-200 font-medium">{selectedReport.times_contradicted || 0}</div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
