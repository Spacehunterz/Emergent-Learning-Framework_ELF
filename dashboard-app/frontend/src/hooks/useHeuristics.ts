import { useState, useCallback, useEffect, useMemo } from 'react'
import { Heuristic } from '../types'
import { useAPI } from './useAPI'

interface UseHeuristicsOptions {
  onStatsChange?: () => void
}

export function useHeuristics(options?: UseHeuristicsOptions) {
  const [heuristics, setHeuristics] = useState<Heuristic[]>([])
  const api = useAPI()
  const { onStatsChange } = options || {}

  const reloadHeuristics = useCallback(async () => {
    try {
      const data = await api.get('/api/heuristics')
      setHeuristics(data || [])
    } catch (err) {
      console.error('Failed to load heuristics:', err)
    }
  }, [api])

  const promoteHeuristic = useCallback(async (id: number) => {
    try {
      await api.post(`/api/heuristics/${id}/promote`)
      setHeuristics(prev => prev.map(h =>
        h.id === id ? { ...h, is_golden: true } : h
      ))
      if (onStatsChange) onStatsChange()
    } catch (err) {
      console.error('Failed to promote heuristic:', err)
      throw err
    }
  }, [api, onStatsChange])

  const demoteHeuristic = useCallback(async (id: number) => {
    try {
      await api.post(`/api/heuristics/${id}/demote`)
      setHeuristics(prev => prev.map(h =>
        h.id === id ? { ...h, is_golden: false } : h
      ))
      if (onStatsChange) onStatsChange()
    } catch (err) {
      console.error('Failed to demote heuristic:', err)
      throw err
    }
  }, [api, onStatsChange])

  const deleteHeuristic = useCallback(async (id: number) => {
    try {
      await api.del(`/api/heuristics/${id}`)
      setHeuristics(prev => prev.filter(h => h.id !== id))
      if (onStatsChange) onStatsChange()
    } catch (err) {
      console.error('Failed to delete heuristic:', err)
      throw err
    }
  }, [api, onStatsChange])

  const updateHeuristic = useCallback(async (
    id: number,
    updates: { rule?: string; explanation?: string; domain?: string }
  ) => {
    try {
      await api.put(`/api/heuristics/${id}`, updates)
      setHeuristics(prev => prev.map(h =>
        h.id === id ? { ...h, ...updates } : h
      ))
    } catch (err) {
      console.error('Failed to update heuristic:', err)
      throw err
    }
  }, [api])

  useEffect(() => {
    reloadHeuristics()
  }, [reloadHeuristics])

  return useMemo(() => ({
    heuristics,
    setHeuristics,
    promoteHeuristic,
    demoteHeuristic,
    deleteHeuristic,
    updateHeuristic,
    reloadHeuristics,
  }), [heuristics, promoteHeuristic, demoteHeuristic, deleteHeuristic, updateHeuristic, reloadHeuristics])
}
