import { create } from 'zustand'

export interface Command {
  id: string
  label: string
  shortcut?: string
  action: () => void
  category: 'Navigation' | 'Actions' | 'Settings' | 'System' | 'Heuristics'
  icon?: string
  description?: string
}

export interface HeuristicResult {
  id: number
  rule: string
  domain: string
  confidence: number
  is_golden: boolean
}

interface CommandPaletteState {
  isOpen: boolean
  query: string
  selectedIndex: number
  mode: 'commands' | 'heuristics' | 'all'

  open: () => void
  close: () => void
  toggle: () => void
  setQuery: (query: string) => void
  setSelectedIndex: (index: number) => void
  setMode: (mode: 'commands' | 'heuristics' | 'all') => void
  reset: () => void
}

export const useCommandPaletteStore = create<CommandPaletteState>((set) => ({
  isOpen: false,
  query: '',
  selectedIndex: 0,
  mode: 'all',

  open: () => set({ isOpen: true, query: '', selectedIndex: 0 }),
  close: () => set({ isOpen: false }),
  toggle: () => set((state) => ({
    isOpen: !state.isOpen,
    query: state.isOpen ? state.query : '',
    selectedIndex: state.isOpen ? state.selectedIndex : 0
  })),
  setQuery: (query) => set({ query, selectedIndex: 0 }),
  setSelectedIndex: (index) => set({ selectedIndex: index }),
  setMode: (mode) => set({ mode, selectedIndex: 0 }),
  reset: () => set({ query: '', selectedIndex: 0, mode: 'all' }),
}))

export function fuzzyMatch(text: string, pattern: string): { matched: boolean; score: number; indices: number[] } {
  if (!pattern) return { matched: true, score: 0, indices: [] }

  const textLower = text.toLowerCase()
  const patternLower = pattern.toLowerCase()

  let patternIdx = 0
  let score = 0
  const indices: number[] = []
  let consecutiveBonus = 0
  let lastMatchIdx = -1

  for (let i = 0; i < textLower.length && patternIdx < patternLower.length; i++) {
    if (textLower[i] === patternLower[patternIdx]) {
      indices.push(i)

      if (lastMatchIdx === i - 1) {
        consecutiveBonus += 5
      } else {
        consecutiveBonus = 0
      }

      if (i === 0 || text[i - 1] === ' ' || text[i - 1] === '-' || text[i - 1] === '_') {
        score += 10
      }

      score += 1 + consecutiveBonus
      lastMatchIdx = i
      patternIdx++
    }
  }

  const matched = patternIdx === patternLower.length

  if (matched) {
    const startBonus = indices[0] === 0 ? 15 : 0
    const lengthPenalty = text.length - pattern.length
    score = score + startBonus - lengthPenalty * 0.5
  }

  return { matched, score, indices }
}

export function highlightMatches(text: string, indices: number[]): { text: string; highlighted: boolean }[] {
  if (indices.length === 0) return [{ text, highlighted: false }]

  const result: { text: string; highlighted: boolean }[] = []
  let lastIdx = 0

  const sortedIndices = [...indices].sort((a, b) => a - b)

  for (const idx of sortedIndices) {
    if (idx > lastIdx) {
      result.push({ text: text.slice(lastIdx, idx), highlighted: false })
    }
    result.push({ text: text[idx], highlighted: true })
    lastIdx = idx + 1
  }

  if (lastIdx < text.length) {
    result.push({ text: text.slice(lastIdx), highlighted: false })
  }

  return result
}
