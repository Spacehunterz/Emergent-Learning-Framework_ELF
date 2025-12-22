import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, Command as CommandIcon, Navigation, Settings, Zap, BookOpen, Crown, ChevronRight } from 'lucide-react'
import { useDataContext } from '../context/DataContext'
import { fuzzyMatch, highlightMatches } from '../store/commandPaletteStore'

interface Command {
  id: string
  label: string
  shortcut?: string
  action: () => void
  category: string
}

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
  commands: Command[]
  onHeuristicSelect?: (heuristicId: number) => void
}

const categoryIcons: Record<string, React.ReactNode> = {
  Navigation: <Navigation className="w-4 h-4" />,
  Actions: <Zap className="w-4 h-4" />,
  Settings: <Settings className="w-4 h-4" />,
  System: <CommandIcon className="w-4 h-4" />,
  Heuristics: <BookOpen className="w-4 h-4" />,
}

const categoryColors: Record<string, string> = {
  Navigation: 'text-blue-400',
  Actions: 'text-emerald-400',
  Settings: 'text-purple-400',
  System: 'text-amber-400',
  Heuristics: 'text-cyan-400',
}

interface SearchResult {
  type: 'command' | 'heuristic'
  id: string | number
  label: string
  category: string
  score: number
  indices: number[]
  data: Command | { id: number; rule: string; domain: string; confidence: number; is_golden: boolean }
}

function HighlightedText({ parts }: { parts: { text: string; highlighted: boolean }[] }) {
  return (
    <>
      {parts.map((part, i) =>
        part.highlighted ? (
          <span key={i} className="text-purple-300 font-semibold bg-purple-500/20 rounded px-0.5">
            {part.text}
          </span>
        ) : (
          <span key={i}>{part.text}</span>
        )
      )}
    </>
  )
}

export function CommandPalette({ isOpen, onClose, commands, onHeuristicSelect }: CommandPaletteProps) {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [mode, setMode] = useState<'all' | 'commands' | 'heuristics'>('all')
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const { heuristics } = useDataContext()

  const searchResults = useMemo((): SearchResult[] => {
    const results: SearchResult[] = []

    if (mode === 'all' || mode === 'commands') {
      for (const cmd of commands) {
        const labelMatch = fuzzyMatch(cmd.label, query)
        const categoryMatch = fuzzyMatch(cmd.category, query)
        const bestMatch = labelMatch.score > categoryMatch.score ? labelMatch : categoryMatch

        if (bestMatch.matched) {
          results.push({
            type: 'command',
            id: cmd.id,
            label: cmd.label,
            category: cmd.category,
            score: bestMatch.score + (cmd.category === 'Navigation' ? 5 : 0),
            indices: labelMatch.matched ? labelMatch.indices : [],
            data: cmd,
          })
        }
      }
    }

    if (mode === 'all' || mode === 'heuristics') {
      for (const h of heuristics) {
        const ruleMatch = fuzzyMatch(h.rule, query)
        const domainMatch = fuzzyMatch(h.domain, query)
        const bestMatch = ruleMatch.score > domainMatch.score ? ruleMatch : domainMatch

        if (bestMatch.matched) {
          results.push({
            type: 'heuristic',
            id: h.id,
            label: h.rule.length > 60 ? h.rule.slice(0, 60) + '...' : h.rule,
            category: h.domain,
            score: bestMatch.score + (h.is_golden ? 10 : 0),
            indices: ruleMatch.matched ? ruleMatch.indices : [],
            data: {
              id: h.id,
              rule: h.rule,
              domain: h.domain,
              confidence: h.confidence,
              is_golden: Boolean(h.is_golden),
            },
          })
        }
      }
    }

    results.sort((a, b) => b.score - a.score)

    return results.slice(0, 20)
  }, [commands, heuristics, query, mode])

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus()
      setQuery('')
      setSelectedIndex(0)
    }
  }, [isOpen])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex(i => Math.min(i + 1, searchResults.length - 1))
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex(i => Math.max(i - 1, 0))
        break
      case 'Enter':
        e.preventDefault()
        const result = searchResults[selectedIndex]
        if (result) {
          if (result.type === 'command') {
            (result.data as Command).action()
          }
          onClose()
        }
        break
      case 'Escape':
        onClose()
        break
    }
  }, [searchResults, selectedIndex, onClose])

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-start justify-center pt-[20vh]"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: -20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: -20 }}
          className="w-full max-w-xl bg-gray-900 rounded-xl shadow-2xl border border-gray-700 overflow-hidden"
          onClick={e => e.stopPropagation()}
        >
          <div className="p-4 border-b border-gray-700">
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={e => {
                setQuery(e.target.value)
                setSelectedIndex(0)
              }}
              onKeyDown={handleKeyDown}
              placeholder="Type a command..."
              className="w-full bg-transparent text-lg outline-none placeholder-gray-500 text-white"
            />
          </div>

          <div className="max-h-80 overflow-y-auto p-2">
            {searchResults.length === 0 ? (
              <div className="p-4 text-center text-gray-500">No commands found</div>
            ) : (
              searchResults.map((result, index) => (
                <button
                  key={`${result.type}-${result.id}`}
                  onClick={() => {
                    if (result.type === 'command') {
                      (result.data as Command).action()
                    }
                    onClose()
                  }}
                  className={`w-full flex items-center justify-between p-3 rounded-lg text-left transition-colors ${
                    index === selectedIndex ? 'bg-blue-600 text-white' : 'hover:bg-gray-800 text-gray-200'
                  }`}
                >
                  <div>
                    <div className="font-medium">{result.label}</div>
                    <div className="text-sm text-gray-400">{result.category}</div>
                  </div>
                  {result.type === 'command' && (result.data as Command).shortcut && (
                    <kbd className="px-2 py-1 bg-gray-800 rounded text-xs text-gray-400">
                      {(result.data as Command).shortcut}
                    </kbd>
                  )}
                </button>
              ))
            )}
          </div>

          <div className="p-2 border-t border-gray-700 text-xs text-gray-500 flex gap-4">
            <span><kbd className="px-1 bg-gray-800 rounded">↑↓</kbd> Navigate</span>
            <span><kbd className="px-1 bg-gray-800 rounded">Enter</kbd> Select</span>
            <span><kbd className="px-1 bg-gray-800 rounded">Esc</kbd> Close</span>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
