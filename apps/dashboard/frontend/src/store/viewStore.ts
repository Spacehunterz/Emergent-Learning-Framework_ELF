import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface ViewState {
    mode: 'grid' | 'cosmic'
    setMode: (mode: 'grid' | 'cosmic') => void
    toggleMode: () => void
}

export const useViewStore = create<ViewState>()(
    persist(
        (set) => ({
            mode: 'cosmic', // Default to cosmic
            setMode: (mode) => set({ mode }),
            toggleMode: () => set((state) => ({ mode: state.mode === 'grid' ? 'cosmic' : 'grid' })),
        }),
        {
            name: 'view-storage', // unique name
        }
    )
)
