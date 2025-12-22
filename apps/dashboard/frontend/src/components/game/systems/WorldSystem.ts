import { create } from 'zustand'
import { Vector3 } from 'three'

export interface GameEntity {
    id: string
    position: Vector3
    radius: number
    type: 'NODE' | 'ENEMY' | 'ASTEROID'
    health: number
    maxHealth: number
    // DataNode specific
    isFolder?: boolean
    name?: string
}

interface WorldState {
    entities: GameEntity[]
    addEntity: (e: GameEntity) => void
    setEntities: (e: GameEntity[]) => void
    removeEntity: (id: string) => void
    damageEntity: (id: string, amount: number) => void // Returns true if destroyed
}

export const useWorldStore = create<WorldState>((set) => ({
    entities: [],
    addEntity: (e) => set((state) => ({ entities: [...state.entities, e] })),
    setEntities: (e) => set({ entities: e }),
    removeEntity: (id) => set((state) => ({ entities: state.entities.filter(e => e.id !== id) })),
    damageEntity: (id, amount) => {
        set((state) => {
            const entities = state.entities.map(e => {
                if (e.id === id) {
                    return { ...e, health: e.health - amount }
                }
                return e
            })
            // Filter dead entities (handled by caller or here? Better to keep them and let loop handle death events)
            // For now, let's just update health.
            return { entities }
        })
    }
}))
