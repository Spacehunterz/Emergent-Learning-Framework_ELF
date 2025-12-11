import { useState, useEffect, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

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
}

export function CommandPalette({ isOpen, onClose, commands }: CommandPaletteProps) {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  const filteredCommands = commands.filter(cmd =>
    cmd.label.toLowerCase().includes(query.toLowerCase()) ||
    cmd.category.toLowerCase().includes(query.toLowerCase())
  )

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
        setSelectedIndex(i => Math.min(i + 1, filteredCommands.length - 1))
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex(i => Math.max(i - 1, 0))
        break
      case 'Enter':
        e.preventDefault()
        if (filteredCommands[selectedIndex]) {
          filteredCommands[selectedIndex].action()
          onClose()
        }
        break
      case 'Escape':
        onClose()
        break
    }
  }, [filteredCommands, selectedIndex, onClose])

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
            {filteredCommands.length === 0 ? (
              <div className="p-4 text-center text-gray-500">No commands found</div>
            ) : (
              filteredCommands.map((cmd, index) => (
                <button
                  key={cmd.id}
                  onClick={() => {
                    cmd.action()
                    onClose()
                  }}
                  className={`w-full flex items-center justify-between p-3 rounded-lg text-left transition-colors ${
                    index === selectedIndex ? 'bg-blue-600 text-white' : 'hover:bg-gray-800 text-gray-200'
                  }`}
                >
                  <div>
                    <div className="font-medium">{cmd.label}</div>
                    <div className="text-sm text-gray-400">{cmd.category}</div>
                  </div>
                  {cmd.shortcut && (
                    <kbd className="px-2 py-1 bg-gray-800 rounded text-xs text-gray-400">
                      {cmd.shortcut}
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
