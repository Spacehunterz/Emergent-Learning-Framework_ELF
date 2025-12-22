import { useMemo } from 'react'
import type { ApiHotspot, TreemapData } from './types'

// Determine severity from scents
const getSeverity = (scents: string[]): string => {
  if (!scents) return 'low'
  if (scents.includes('blocker')) return 'critical'
  if (scents.includes('warning')) return 'high'
  if (scents.includes('discovery')) return 'medium'
  return 'low'
}

// Convert hotspots to hierarchical data
const buildHierarchy = (data: ApiHotspot[]): TreemapData => {
  const root: TreemapData = { name: 'root', children: [] }

  if (!data || !Array.isArray(data)) return root

  data.forEach(hotspot => {
    if (!hotspot.location) return

    const parts = hotspot.location.split(/[\/\\]/).filter(Boolean)
    let currentLevel = root.children!

    parts.forEach((part, index) => {
      const isFile = index === parts.length - 1

      let existing = currentLevel.find(c => c.name === part)

      if (!existing) {
        existing = {
          name: part,
          children: isFile ? undefined : [],
          value: isFile ? hotspot.trail_count : undefined,
          strength: isFile ? hotspot.total_strength : undefined,
          severity: isFile ? getSeverity(hotspot.scents) : undefined,
          scents: isFile ? hotspot.scents : undefined,
          path: isFile ? hotspot.location : undefined,
        }
        currentLevel.push(existing)
      }

      if (!isFile && existing.children) {
        currentLevel = existing.children
      }
    })
  })

  return root
}

export function useTreemapData(hotspots: ApiHotspot[], selectedDomain: string | null) {
  // Get unique scents as "domains"
  const domains = useMemo(() => {
    const allScents = hotspots?.flatMap(h => h.scents || []) || []
    return Array.from(new Set(allScents)).filter(Boolean)
  }, [hotspots])

  // Filter hotspots by scent (domain)
  // Only filter if selectedDomain is an actual scent, not a GridView domain name
  const filteredHotspots = useMemo(() => {
    if (!hotspots || !Array.isArray(hotspots)) return []
    if (!selectedDomain) return hotspots
    // Check if selectedDomain is a valid scent before filtering
    const allScents = hotspots.flatMap(h => h.scents || [])
    const validScents = new Set(allScents)
    if (!validScents.has(selectedDomain)) return hotspots
    return hotspots.filter(h => h.scents?.includes(selectedDomain))
  }, [hotspots, selectedDomain])

  // Build hierarchical data
  const hierarchy = useMemo(() => {
    return buildHierarchy(filteredHotspots)
  }, [filteredHotspots])

  return {
    domains,
    filteredHotspots,
    hierarchy,
  }
}
