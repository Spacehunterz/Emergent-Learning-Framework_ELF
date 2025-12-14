// API returns this format from /api/hotspots
export interface ApiHotspot {
  location: string
  trail_count: number
  total_strength: number
  scents: string[]
  agents: string[]
  agent_count: number
  last_activity: string
  first_activity: string
  related_heuristics: any[]
}

export interface HotspotTreemapProps {
  hotspots: ApiHotspot[]
  onSelect: (path: string, line?: number) => void
  selectedDomain: string | null
  onDomainFilter: (domain: string | null) => void
}

export interface TreemapData {
  name: string
  value?: number
  strength?: number
  severity?: string
  scents?: string[]
  path?: string
  children?: TreemapData[]
}

export interface TooltipState {
  x: number
  y: number
  data: ApiHotspot | null
}
