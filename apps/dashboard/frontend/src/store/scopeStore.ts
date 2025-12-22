import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface ProjectContext {
    has_project: boolean
    project_name: string | null
    project_root: string | null
    has_project_db: boolean
    default_scope: 'global' | 'project'
}

interface ScopeState {
    scope: 'global' | 'project'
    projectContext: ProjectContext | null
    isLoading: boolean
    setScope: (scope: 'global' | 'project') => void
    toggleScope: () => void
    setProjectContext: (ctx: ProjectContext) => void
    setLoading: (loading: boolean) => void
    fetchProjectContext: () => Promise<void>
}

export const useScopeStore = create<ScopeState>()(
    persist(
        (set, get) => ({
            scope: 'global',
            projectContext: null,
            isLoading: true,
            setScope: (scope) => set({ scope }),
            toggleScope: () => set((state) => ({
                scope: state.scope === 'global' ? 'project' : 'global'
            })),
            setProjectContext: (ctx) => set({
                projectContext: ctx,
                // Default to project scope when in a project context
                scope: ctx.has_project ? 'project' : 'global'
            }),
            setLoading: (loading) => set({ isLoading: loading }),
            fetchProjectContext: async () => {
                set({ isLoading: true })
                try {
                    const response = await fetch('/api/context')
                    if (response.ok) {
                        const ctx = await response.json()
                        set({
                            projectContext: ctx,
                            scope: ctx.default_scope,
                            isLoading: false
                        })
                    } else {
                        set({ isLoading: false })
                    }
                } catch (error) {
                    console.error('Failed to fetch project context:', error)
                    set({ isLoading: false })
                }
            }
        }),
        {
            name: 'scope-storage',
            partialize: (state) => ({ scope: state.scope }), // Only persist scope, not projectContext
        }
    )
)
