import { useEffect, useState } from 'react'
import { LearningVelocityData } from './types'

export function useVelocityData(timeframe: number) {
  const [data, setData] = useState<LearningVelocityData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchData()
  }, [timeframe])

  const fetchData = async () => {
    try {
      setLoading(true)
      const response = await fetch(`/api/learning-velocity?days=${timeframe}`)
      const result = await response.json()
      setData(result)
    } catch (error) {
      console.error('Failed to fetch learning velocity:', error)
    } finally {
      setLoading(false)
    }
  }

  return { data, loading }
}
