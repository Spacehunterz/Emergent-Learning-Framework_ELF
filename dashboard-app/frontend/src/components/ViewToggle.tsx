import { useViewStore } from '../store/viewStore'
import { LayoutGrid, Orbit } from 'lucide-react'
import { motion } from 'framer-motion'

export default function ViewToggle() {
    const { mode, toggleMode } = useViewStore()

    return (
        <button
            onClick={toggleMode}
            className={`
        relative flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-all duration-300
        ${mode === 'cosmic'
                    ? 'bg-purple-900/30 border-purple-500/50 text-purple-300 shadow-[0_0_15px_rgba(168,85,247,0.3)]'
                    : 'bg-slate-800/50 border-slate-700 text-slate-400 hover:bg-slate-800 hover:text-slate-200'}
      `}
        >
            <div className="relative z-10 flex items-center gap-2">
                {mode === 'cosmic' ? (
                    <Orbit className="w-4 h-4 animate-spin-slow" />
                ) : (
                    <LayoutGrid className="w-4 h-4" />
                )}
                <span className="text-xs font-medium">
                    {mode === 'cosmic' ? 'Cosmic View' : 'Grid View'}
                </span>
            </div>

            {/* Background glow for cosmic mode */}
            {mode === 'cosmic' && (
                <motion.div
                    layoutId="view-highlight"
                    className="absolute inset-0 bg-purple-500/10 rounded-lg"
                    initial={false}
                    transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }}
                />
            )}
        </button>
    )
}
