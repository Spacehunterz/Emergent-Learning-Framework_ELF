import { useEffect, useState } from 'react'
import { GraphData } from './types'

export function useGraphData() {
  const [graphData, setGraphData] = useState<GraphData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchGraphData = async () => {
      try {
        setLoading(true)
        const response = await fetch('/api/heuristic-graph')
        if (!response.ok) throw new Error('Failed to fetch graph data')
        const data = await response.json()
        setGraphData(data)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }
    fetchGraphData()
  }, [])

  return { graphData, loading, error }
}
