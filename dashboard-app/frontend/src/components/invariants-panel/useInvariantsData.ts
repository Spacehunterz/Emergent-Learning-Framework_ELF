import { useState, useEffect } from 'react'
import { Invariant } from '../../types'
import { useAPI } from '../../hooks/useAPI'
import { ScopeFilter, SeverityFilter, StatusFilter } from './types'

interface UseInvariantsDataReturn {
  invariants: Invariant[]
  domains: string[]
  loading: boolean
  actionLoading: number | null
  handleValidate: (id: number) => Promise<void>
  handleViolate: (id: number) => Promise<void>
  setInvariants: React.Dispatch<React.SetStateAction<Invariant[]>>
  setActionLoading: React.Dispatch<React.SetStateAction<number | null>>
}

export function useInvariantsData(
  scopeFilter: ScopeFilter,
  severityFilter: SeverityFilter,
  statusFilter: StatusFilter,
  domainFilter: string
): UseInvariantsDataReturn {
  const api = useAPI()
  const [invariants, setInvariants] = useState<Invariant[]>([])
  const [domains, setDomains] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<number | null>(null)

  // Load invariants
  useEffect(() => {
    loadInvariants()
  }, [scopeFilter, severityFilter, statusFilter, domainFilter])

  const loadInvariants = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (scopeFilter !== 'all') params.append('scope', scopeFilter)
      if (severityFilter !== 'all') params.append('severity', severityFilter)
      if (statusFilter !== 'all') params.append('status', statusFilter)
      if (domainFilter !== 'all') params.append('domain', domainFilter)

      const data = await api.get(`/api/invariants?${params.toString()}`)
      setInvariants(data || [])

      // Extract unique domains
      const uniqueDomains = Array.from(new Set(data?.map((i: Invariant) => i.domain).filter(Boolean))) as string[]
      setDomains(uniqueDomains)
    } catch (err) {
      console.error('Failed to load invariants:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleValidate = async (id: number) => {
    setActionLoading(id)
    try {
      await api.post(`/api/invariants/${id}/validate`)
      // Update locally
      setInvariants(prev => prev.map(i =>
        i.id === id
          ? { ...i, status: 'active' as const, last_validated_at: new Date().toISOString() }
          : i
      ))
    } catch (err) {
      console.error('Failed to validate invariant:', err)
    } finally {
      setActionLoading(null)
    }
  }

  const handleViolate = async (id: number) => {
    setActionLoading(id)
    try {
      await api.post(`/api/invariants/${id}/violate`)
      // Update locally
      setInvariants(prev => prev.map(i =>
        i.id === id
          ? { ...i, status: 'violated' as const, violation_count: i.violation_count + 1, last_violated_at: new Date().toISOString() }
          : i
      ))
    } catch (err) {
      console.error('Failed to record violation:', err)
    } finally {
      setActionLoading(null)
    }
  }

  return {
    invariants,
    domains,
    loading,
    actionLoading,
    handleValidate,
    handleViolate,
    setInvariants,
    setActionLoading,
  }
}
