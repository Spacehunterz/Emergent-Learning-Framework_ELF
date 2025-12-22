import { useState, useEffect } from 'react'
import { Assumption } from '../types'
import { Lightbulb, Clock } from 'lucide-react'
import { useAPI } from '../hooks/useAPI'
import {
  AssumptionFilters,
  AssumptionCard,
  AssumptionsPanelProps,
  StatusFilter,
} from './assumptions'

export default function AssumptionsPanel({ className = '' }: AssumptionsPanelProps) {
  const api = useAPI()

  const [assumptions, setAssumptions] = useState<Assumption[]>([])
  const [domains, setDomains] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [domainFilter, setDomainFilter] = useState<string>('all')
  const [minConfidence, setMinConfidence] = useState<number>(0)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [actionLoading, setActionLoading] = useState<number | null>(null)

  useEffect(() => {
    loadAssumptions()
  }, [statusFilter, domainFilter, minConfidence])

  const loadAssumptions = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (statusFilter !== 'all') params.append('status', statusFilter)
      if (domainFilter !== 'all') params.append('domain', domainFilter)
      if (minConfidence > 0) params.append('min_confidence', (minConfidence / 100).toString())

      const data = await api.get(`/api/assumptions?${params.toString()}`)
      setAssumptions(data || [])

      const uniqueDomains = Array.from(new Set(data?.map((a: Assumption) => a.domain).filter(Boolean))) as string[]
      setDomains(uniqueDomains)
    } catch (err) {
      console.error('Failed to load assumptions:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleVerify = async (id: number) => {
    setActionLoading(id)
    try {
      await api.post(`/api/assumptions/${id}/verify`)
      setAssumptions(prev => prev.map(a =>
        a.id === id
          ? { ...a, verified_count: a.verified_count + 1, status: 'verified' as const, last_verified_at: new Date().toISOString() }
          : a
      ))
    } catch (err) {
      console.error('Failed to verify assumption:', err)
    } finally {
      setActionLoading(null)
    }
  }

  const handleChallenge = async (id: number) => {
    setActionLoading(id)
    try {
      await api.post(`/api/assumptions/${id}/challenge`)
      setAssumptions(prev => prev.map(a =>
        a.id === id
          ? { ...a, challenged_count: a.challenged_count + 1, status: 'challenged' as const }
          : a
      ))
    } catch (err) {
      console.error('Failed to challenge assumption:', err)
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div className={`bg-slate-800 rounded-lg p-4 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Lightbulb className="w-5 h-5 text-amber-400" />
          <h3 className="text-lg font-semibold text-white">Assumptions</h3>
          <span className="text-sm text-slate-400">({assumptions.length})</span>
        </div>

        <AssumptionFilters
          statusFilter={statusFilter}
          domainFilter={domainFilter}
          minConfidence={minConfidence}
          domains={domains}
          onStatusChange={setStatusFilter}
          onDomainChange={setDomainFilter}
          onConfidenceChange={setMinConfidence}
        />
      </div>

      <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2">
        {loading ? (
          <div className="text-center text-slate-400 py-12">
            <Clock className="w-8 h-8 mx-auto mb-2 animate-spin" />
            Loading assumptions...
          </div>
        ) : assumptions.length === 0 ? (
          <div className="text-center text-slate-400 py-12">
            No assumptions found
          </div>
        ) : (
          assumptions.map(assumption => (
            <AssumptionCard
              key={assumption.id}
              assumption={assumption}
              isExpanded={expandedId === assumption.id}
              isLoading={actionLoading === assumption.id}
              onToggle={() => setExpandedId(expandedId === assumption.id ? null : assumption.id)}
              onVerify={handleVerify}
              onChallenge={handleChallenge}
            />
          ))
        )}
      </div>
    </div>
  )
}
