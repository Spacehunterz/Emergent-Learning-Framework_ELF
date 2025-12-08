import { useState, useRef, useEffect } from 'react'
import { useAPI } from '../hooks/useAPI'
import { Search, Send, Sparkles, Clock, ArrowRight, Brain, Target, AlertTriangle, Lightbulb } from 'lucide-react'

interface QueryResult {
  query: string
  heuristics: any[]
  learnings: any[]
  hotspots: any[]
  runs: any[]
  summary: string
}

const exampleQueries = [
  { icon: Brain, text: "What heuristics are most validated?", category: "Heuristics" },
  { icon: Target, text: "Show hotspots in authentication code", category: "Hotspots" },
  { icon: AlertTriangle, text: "What failures happened today?", category: "Failures" },
  { icon: Lightbulb, text: "Which rules should be promoted to golden?", category: "Insights" },
]

export default function QueryInterface() {
  const [query, setQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<QueryResult | null>(null)
  const [history, setHistory] = useState<string[]>([])
  const inputRef = useRef<HTMLInputElement>(null)
  const api = useAPI()

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleSubmit = async (q?: string) => {
    const queryText = q || query
    if (!queryText.trim()) return

    setIsLoading(true)
    setResult(null)

    try {
      const data = await api.post('/api/query', { query: queryText })
      setResult(data)
      setHistory(prev => [queryText, ...prev.filter(h => h !== queryText).slice(0, 9)])
    } catch (err) {
      console.error('Query failed:', err)
    } finally {
      setIsLoading(false)
    }

    setQuery('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const renderResultItem = (item: any, index: number) => {
    // Detect type of result and render appropriately
    if (item._type === 'heuristic' || item.rule) {
      // Heuristic
      return (
        <div key={index} className="bg-slate-700/50 rounded-lg p-3">
          <div className="flex items-center space-x-2 mb-1">
            <Brain className="w-4 h-4 text-violet-400" />
            <span className="text-sm font-medium text-white">{item.rule}</span>
          </div>
          <div className="flex items-center space-x-3 text-xs text-slate-400">
            <span>{item.domain}</span>
            <span>{((item.confidence || 0) * 100).toFixed(0)}% confidence</span>
            <span>{item.times_validated || 0} validations</span>
          </div>
        </div>
      )
    } else if (item._type === 'hotspot' || item.location) {
      // Hotspot - API returns location, strength, count
      return (
        <div key={index} className="bg-slate-700/50 rounded-lg p-3">
          <div className="flex items-center space-x-2 mb-1">
            <Target className="w-4 h-4 text-orange-400" />
            <span className="text-sm font-medium text-white">{item.location || item.file_path}</span>
          </div>
          <div className="flex items-center space-x-3 text-xs text-slate-400">
            <span>{item.count || item.hit_count || 0} trails</span>
            <span>Strength: {(item.strength || 0).toFixed(1)}</span>
          </div>
        </div>
      )
    } else if (item._type === 'learning' || (item.title && item.type)) {
      // Learning/Failure
      return (
        <div key={index} className="bg-slate-700/50 rounded-lg p-3">
          <div className="flex items-center space-x-2 mb-1">
            <AlertTriangle className={`w-4 h-4 ${item.type === 'failure' ? 'text-red-400' : 'text-amber-400'}`} />
            <span className="text-sm font-medium text-white">{item.title}</span>
          </div>
          {item.summary && (
            <div className="text-sm text-slate-300 mt-1">{item.summary.slice(0, 200)}</div>
          )}
          <div className="flex items-center space-x-3 text-xs text-slate-400 mt-2">
            <span>{item.domain}</span>
            <span>{item.created_at}</span>
          </div>
        </div>
      )
    } else {
      // Generic
      return (
        <div key={index} className="bg-slate-700/50 rounded-lg p-3">
          <pre className="text-sm text-slate-300 overflow-x-auto">
            {JSON.stringify(item, null, 2)}
          </pre>
        </div>
      )
    }
  }

  return (
    <div className="bg-slate-800 rounded-lg p-4">
      {/* Header */}
      <div className="flex items-center space-x-2 mb-6">
        <Sparkles className="w-5 h-5 text-sky-400" />
        <h3 className="text-lg font-semibold text-white">Natural Language Query</h3>
      </div>

      {/* Query input */}
      <div className="relative mb-6">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything about your learning data..."
          className="w-full bg-slate-700 text-white rounded-xl pl-12 pr-12 py-4 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent"
        />
        <button
          onClick={() => handleSubmit()}
          disabled={isLoading || !query.trim()}
          className="absolute right-3 top-1/2 -translate-y-1/2 p-2 rounded-lg bg-sky-500 text-white hover:bg-sky-400 disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>

      {/* Example queries */}
      {!result && !isLoading && (
        <div className="mb-6">
          <div className="text-sm text-slate-400 mb-3">Try asking:</div>
          <div className="grid grid-cols-2 gap-2">
            {exampleQueries.map(({ icon: Icon, text, category }) => (
              <button
                key={text}
                onClick={() => { setQuery(text); handleSubmit(text) }}
                className="flex items-center space-x-2 p-3 bg-slate-700/50 rounded-lg hover:bg-slate-700 transition text-left"
              >
                <Icon className="w-4 h-4 text-slate-400 flex-shrink-0" />
                <div>
                  <div className="text-sm text-white">{text}</div>
                  <div className="text-xs text-slate-500">{category}</div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="flex items-center space-x-3 text-sky-400">
            <div className="animate-spin w-5 h-5 border-2 border-current border-t-transparent rounded-full" />
            <span>Analyzing your question...</span>
          </div>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Summary */}
          <div className="bg-sky-500/10 border border-sky-500/20 rounded-lg p-4">
            <div className="flex items-start space-x-2">
              <Sparkles className="w-4 h-4 text-sky-400 mt-0.5 flex-shrink-0" />
              <div>
                <div className="text-sm font-medium text-sky-400 mb-1">Results Summary</div>
                <div className="text-sm text-slate-300">{result.summary}</div>
              </div>
            </div>
          </div>

          {/* Results by category */}
          <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2">
            {/* Heuristics */}
            {result.heuristics.length > 0 && (
              <div>
                <div className="text-sm text-slate-400 mb-2 flex items-center space-x-2">
                  <Brain className="w-4 h-4" />
                  <span>Heuristics ({result.heuristics.length})</span>
                </div>
                <div className="space-y-2">
                  {result.heuristics.map((item, idx) => renderResultItem({ ...item, _type: 'heuristic' }, idx))}
                </div>
              </div>
            )}

            {/* Learnings */}
            {result.learnings.length > 0 && (
              <div>
                <div className="text-sm text-slate-400 mb-2 flex items-center space-x-2">
                  <Lightbulb className="w-4 h-4" />
                  <span>Learnings ({result.learnings.length})</span>
                </div>
                <div className="space-y-2">
                  {result.learnings.map((item, idx) => renderResultItem({ ...item, _type: 'learning' }, idx))}
                </div>
              </div>
            )}

            {/* Hotspots */}
            {result.hotspots.length > 0 && (
              <div>
                <div className="text-sm text-slate-400 mb-2 flex items-center space-x-2">
                  <Target className="w-4 h-4" />
                  <span>Hotspots ({result.hotspots.length})</span>
                </div>
                <div className="space-y-2">
                  {result.hotspots.map((item, idx) => renderResultItem({ ...item, _type: 'hotspot' }, idx))}
                </div>
              </div>
            )}

            {/* No results message */}
            {result.heuristics.length === 0 && result.learnings.length === 0 && result.hotspots.length === 0 && (
              <div className="text-center text-slate-400 py-8">
                No results found. Try a different query.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Query history */}
      {history.length > 0 && !result && !isLoading && (
        <div className="border-t border-slate-700 pt-4 mt-4">
          <div className="flex items-center space-x-2 text-sm text-slate-400 mb-2">
            <Clock className="w-4 h-4" />
            <span>Recent queries</span>
          </div>
          <div className="space-y-1">
            {history.map((h, idx) => (
              <button
                key={idx}
                onClick={() => { setQuery(h); handleSubmit(h) }}
                className="w-full text-left px-3 py-2 rounded-lg text-sm text-slate-300 hover:bg-slate-700 transition"
              >
                {h}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
