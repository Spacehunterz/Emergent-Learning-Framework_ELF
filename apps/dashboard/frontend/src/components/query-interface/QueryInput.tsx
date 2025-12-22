import { Search, Send } from 'lucide-react'
import { QueryInputProps } from './types'

export default function QueryInput({
  query,
  onQueryChange,
  onSubmit,
  isLoading,
  inputRef
}: QueryInputProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSubmit()
    }
  }

  return (
    <div className="relative mb-6">
      <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
      <input
        ref={inputRef}
        type="text"
        value={query}
        onChange={(e) => onQueryChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask anything about your learning data..."
        className="w-full bg-slate-700 text-white rounded-xl pl-12 pr-12 py-4 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent"
      />
      <button
        onClick={onSubmit}
        disabled={isLoading || !query.trim()}
        className="absolute right-3 top-1/2 -translate-y-1/2 p-2 rounded-lg bg-sky-500 text-white hover:bg-sky-400 disabled:opacity-50 disabled:cursor-not-allowed transition"
      >
        <Send className="w-4 h-4" />
      </button>
    </div>
  )
}
