import { create } from 'zustand'

export type GraphicsQuality = 'low' | 'medium' | 'high'

// Graphics presets for different quality levels
export const GRAPHICS_PRESETS: Record<GraphicsQuality, {
    starCount: number
    explosionParticles: number
    shadowsEnabled: boolean
    bloomEnabled: boolean
    antialiasing: boolean
}> = {
    low: {
        starCount: 2000,
        explosionParticles: 10,
        shadowsEnabled: false,
        bloomEnabled: false,
        antialiasing: false
    },
    medium: {
        starCount: 5000,
        explosionParticles: 25,
        shadowsEnabled: false,
        bloomEnabled: true,
        antialiasing: true
    },
    high: {
        starCount: 7000,
        explosionParticles: 50,
        shadowsEnabled: true,
        bloomEnabled: true,
        antialiasing: true
    }
}

interface GameSettingsState {
    sensitivityX: number
    sensitivityY: number
    smoothness: number
    isPaused: boolean
    graphicsQuality: GraphicsQuality
    showMainMenu: boolean // Controls main menu visibility
    setSensitivityX: (val: number) => void
    setSensitivityY: (val: number) => void
    setSmoothness: (val: number) => void
    setPaused: (paused: boolean) => void
    setGraphicsQuality: (quality: GraphicsQuality) => void
    setShowMainMenu: (show: boolean) => void
}

export const useGameSettings = create<GameSettingsState>((set) => ({
    sensitivityX: 1.0,
    sensitivityY: 0.8, // "Lower Z sensitivity" request (User likely means Vertical/Pitch)
    smoothness: 0.1,    // 0 = rigid, 1 = very smooth/laggy
    isPaused: false,
    graphicsQuality: 'high',
    showMainMenu: true, // Start with main menu visible
    setSensitivityX: (v) => set({ sensitivityX: v }),
    setSensitivityY: (v) => set({ sensitivityY: v }),
    setSmoothness: (v) => set({ smoothness: v }),
    setPaused: (p) => set({ isPaused: p }),
    setGraphicsQuality: (q) => set({ graphicsQuality: q }),
    setShowMainMenu: (s) => set({ showMainMenu: s })
}))
