export interface GraphNode {
  id: number
  label: string
  fullText: string
  domain: string
  confidence: number
  is_golden: boolean
  times_validated: number
  times_violated: number
  explanation?: string
  created_at: string
  // D3 simulation properties
  x?: number
  y?: number
  fx?: number | null
  fy?: number | null
}

export interface GraphEdge {
  id: number
  source: number | GraphNode
  target: number | GraphNode
  strength: number
  type: string
  label: string
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  stats: {
    total_nodes: number
    total_edges: number
    golden_rules: number
    domains: number
  }
}

export interface KnowledgeGraphProps {
  onNodeClick?: (node: GraphNode) => void
}

// Domain color palette
export const DOMAIN_COLORS: Record<string, string> = {
  'general': '#8b5cf6',      // Purple
  'code': '#3b82f6',         // Blue
  'testing': '#10b981',      // Green
  'debugging': '#f59e0b',    // Amber
  'architecture': '#06b6d4', // Cyan
  'performance': '#ec4899',  // Pink
  'security': '#ef4444',     // Red
  'documentation': '#6366f1', // Indigo
  'workflow': '#14b8a6',     // Teal
  'learning': '#a855f7',     // Purple-500
}

export const getColorForDomain = (domain: string): string => {
  if (DOMAIN_COLORS[domain]) return DOMAIN_COLORS[domain]
  // Generate consistent color based on domain name
  const hash = domain.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
  const hue = hash % 360
  return `hsl(${hue}, 70%, 60%)`
}
