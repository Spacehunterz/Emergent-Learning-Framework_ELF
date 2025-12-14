import { useState, useEffect, useCallback, useMemo } from 'react'
import { Stats, Hotspot, ApiRun, RawEvent, TimelineData, ApiAnomaly } from '../types'
import { useAPI } from './useAPI'

export function useDashboardData() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [hotspots, setHotspots] = useState<Hotspot[]>([])
  const [runs, setRuns] = useState<ApiRun[]>([])
  const [events, setEvents] = useState<RawEvent[]>([])
  const [timeline, setTimeline] = useState<TimelineData | null>(null)
  const [anomalies, setAnomalies] = useState<ApiAnomaly[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const api = useAPI()

  const loadData = useCallback(async () => {
    try {
      const [statsData, hotspotsData, runsData, timelineData, anomaliesData, eventsData] = await Promise.all([
        api.get('/api/stats').catch(() => null),
        api.get('/api/hotspots').catch(() => []),
        api.get('/api/runs?limit=100').catch(() => []),
        api.get('/api/timeline').catch(() => null),
        api.get('/api/anomalies').catch(() => []),
        api.get('/api/events?limit=100').catch(() => []),
      ])
      if (statsData) setStats(statsData)
      setHotspots(hotspotsData || [])
      setRuns(runsData || [])
      if (timelineData) setTimeline(timelineData)
      setAnomalies(anomaliesData || [])
      setEvents(eventsData || [])
    } catch (err) {
      console.error('Failed to load dashboard data:', err)
    } finally {
      setIsLoading(false)
    }
  }, [api])

  const reload = useCallback(() => {
    setIsLoading(true)
    loadData()
  }, [loadData])

  const loadStats = useCallback(async () => {
    try {
      const data = await api.get('/api/stats')
      if (data) setStats(data)
    } catch (err) {
      console.error('Failed to load stats:', err)
    }
  }, [api])

  // Initial data load
  useEffect(() => {
    loadData()

    // Auto-refresh stats, runs, and events every 10 seconds
    const interval = setInterval(() => {
      // Refresh stats
      api.get('/api/stats').then(data => {
        if (data) setStats(data)
      }).catch(() => {})
      // Refresh runs
      api.get('/api/runs?limit=100').then(data => {
        if (data) setRuns(data)
      }).catch(() => {})
      // Refresh events
      api.get('/api/events?limit=100').then(data => {
        if (data) setEvents(data)
      }).catch(() => {})
    }, 10000)

    return () => clearInterval(interval)
  }, [loadData, api])

  return useMemo(() => ({
    stats,
    hotspots,
    runs,
    events,
    timeline,
    anomalies,
    isLoading,
    reload,
    loadStats,
    setStats,
    setAnomalies,
  }), [stats, hotspots, runs, events, timeline, anomalies, isLoading, reload, loadStats])
}
