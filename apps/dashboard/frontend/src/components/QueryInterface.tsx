import { useState, useRef, useEffect } from 'react'
import { useAPI } from '../hooks/useAPI'
import { Sparkles } from 'lucide-react'
import { QueryInput, ExampleQueries, QueryResults, QueryHistory } from './query-interface'
import type { QueryResult } from './query-interface/types'

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

  const handleSelectQuery = (q: string) => {
    setQuery(q)
    handleSubmit(q)
  }

  return (
    <div className="bg-slate-800 rounded-lg p-4">
      {/* Header */}
      <div className="flex items-center space-x-2 mb-6">
        <Sparkles className="w-5 h-5 text-sky-400" />
        <h3 className="text-lg font-semibold text-white">Natural Language Query</h3>
      </div>

      <QueryInput
        query={query}
        onQueryChange={setQuery}
        onSubmit={() => handleSubmit()}
        isLoading={isLoading}
        inputRef={inputRef}
      />

      {!result && !isLoading && (
        <ExampleQueries onSelectQuery={handleSelectQuery} />
      )}

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="flex items-center space-x-3 text-sky-400">
            <div className="animate-spin w-5 h-5 border-2 border-current border-t-transparent rounded-full" />
            <span>Analyzing your question...</span>
          </div>
        </div>
      )}

      {result && <QueryResults result={result} />}

      {history.length > 0 && !result && !isLoading && (
        <QueryHistory history={history} onSelectQuery={handleSelectQuery} />
      )}
    </div>
  )
}
