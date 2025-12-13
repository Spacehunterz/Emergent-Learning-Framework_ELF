import { Shield, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'
import { FraudReport, AnomalySignal } from '../../types'

export function getClassificationBadge(classification: FraudReport['classification']) {
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

export function getSeverityBadge(severity: AnomalySignal['severity']) {
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

export function calculateSuccessRate(report: FraudReport) {
  const total = (report.times_validated || 0) + (report.times_violated || 0) + (report.times_contradicted || 0)
  if (total === 0) return 0
  return ((report.times_validated || 0) / total) * 100
}
