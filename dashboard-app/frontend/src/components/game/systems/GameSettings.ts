import { create } from 'zustand'

interface GameSettingsState {
    sensitivityX: number
    sensitivityY: number
    smoothness: number
    isPaused: boolean
    setSensitivityX: (val: number) => void
    setSensitivityY: (val: number) => void
    setSmoothness: (val: number) => void
    setPaused: (paused: boolean) => void
}

export const useGameSettings = create<GameSettingsState>((set) => ({
    sensitivityX: 1.0,
    sensitivityY: 0.8, // "Lower Z sensitivity" request (User likely means Vertical/Pitch)
    smoothness: 0.1,    // 0 = rigid, 1 = very smooth/laggy
    isPaused: false,
    setSensitivityX: (v) => set({ sensitivityX: v }),
    setSensitivityY: (v) => set({ sensitivityY: v }),
    setSmoothness: (v) => set({ smoothness: v }),
    setPaused: (p) => set({ isPaused: p })
}))
