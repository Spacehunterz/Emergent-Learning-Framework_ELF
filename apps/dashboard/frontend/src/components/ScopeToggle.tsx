import { useScopeStore } from '../store/scopeStore'
import { Globe, FolderOpen } from 'lucide-react'
import { motion } from 'framer-motion'
import { useEffect } from 'react'

export default function ScopeToggle() {
    const { scope, toggleScope, projectContext, isLoading, fetchProjectContext } = useScopeStore()

    // Fetch project context on mount
    useEffect(() => {
        fetchProjectContext()
    }, [fetchProjectContext])

    // Don't show toggle if no project context or loading
    if (isLoading) {
        return (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/30 border border-slate-700/50">
                <div className="w-4 h-4 rounded-full bg-slate-600 animate-pulse" />
                <span className="text-xs text-slate-500">Loading...</span>
            </div>
        )
    }

    // If no project, just show "Global" indicator (no toggle needed)
    if (!projectContext?.has_project) {
        return (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/30 border border-slate-700/50">
                <Globe className="w-4 h-4 text-blue-400" />
                <span className="text-xs text-slate-400">Global</span>
            </div>
        )
    }

    // Show toggle between Global and Project
    const isProject = scope === 'project'

    return (
        <button
            onClick={toggleScope}
            className={`
                relative flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-all duration-300
                ${isProject
                    ? 'bg-emerald-900/30 border-emerald-500/50 text-emerald-300 shadow-[0_0_15px_rgba(16,185,129,0.3)]'
                    : 'bg-blue-900/30 border-blue-500/50 text-blue-300 shadow-[0_0_15px_rgba(59,130,246,0.3)]'}
            `}
            title={isProject 
                ? `Project: ${projectContext.project_name}\nClick to switch to Global`
                : `Global scope\nClick to switch to Project: ${projectContext.project_name}`
            }
        >
            <div className="relative z-10 flex items-center gap-2">
                {isProject ? (
                    <FolderOpen className="w-4 h-4" />
                ) : (
                    <Globe className="w-4 h-4" />
                )}
                <span className="text-xs font-medium max-w-[100px] truncate">
                    {isProject ? projectContext.project_name : 'Global'}
                </span>
            </div>

            {/* Background glow */}
            <motion.div
                layoutId="scope-highlight"
                className={`absolute inset-0 rounded-lg ${isProject ? 'bg-emerald-500/10' : 'bg-blue-500/10'}`}
                initial={false}
                transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }}
            />
        </button>
    )
}
