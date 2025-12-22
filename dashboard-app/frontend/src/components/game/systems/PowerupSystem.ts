import { create } from 'zustand'
import { Vector3 } from 'three'

export type PowerupType = 'shield' | 'hull' | 'rapid'

export interface Powerup {
    id: string
    type: PowerupType
    position: Vector3
    createdAt: number
}

interface PowerupState {
    powerups: Powerup[]
    spawnPowerup: (position: Vector3, type?: PowerupType) => void
    removePowerup: (id: string) => void
    expireOldPowerups: (maxAge?: number) => void
}

export const usePowerupStore = create<PowerupState>((set, get) => ({
    powerups: [],

    spawnPowerup: (position: Vector3, type) => {
        // Random type if not specified
        if (!type) {
            const r = Math.random()
            if (r < 0.4) type = 'shield' // 40%
            else if (r < 0.7) type = 'hull' // 30%
            else type = 'rapid' // 30%
        }

        const newPowerup: Powerup = {
            id: Math.random().toString(36).substr(2, 9),
            type,
            position: position.clone(),
            createdAt: Date.now()
        }

        set(state => ({
            powerups: [...state.powerups, newPowerup]
        }))
    },

    removePowerup: (id) => {
        set(state => ({
            powerups: state.powerups.filter(p => p.id !== id)
        }))
    },

    expireOldPowerups: (maxAge = 15000) => { // 15 seconds lifetime
        const now = Date.now()
        set(state => ({
            powerups: state.powerups.filter(p => now - p.createdAt < maxAge)
        }))
    }
}))
