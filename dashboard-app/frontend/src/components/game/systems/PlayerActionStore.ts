import { create } from 'zustand'

interface PlayerActionState {
    isShieldActive: boolean
    setShieldActive: (active: boolean) => void

    isRapidFire: boolean
    setRapidFire: (active: boolean) => void
}

export const usePlayerActionStore = create<PlayerActionState>((set) => ({
    isShieldActive: false,
    setShieldActive: (active) => set({ isShieldActive: active }),

    isRapidFire: false,
    setRapidFire: (active) => set({ isRapidFire: active })
}))
