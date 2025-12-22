
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type SkillType = 'COMBAT' | 'MINING'

interface ProgressionState {
    combatXP: number
    miningXP: number
    combatLevel: number
    miningLevel: number

    // Session Stats
    sessionKills: number
    sessionResources: number

    // Actions
    addXP: (type: SkillType, amount: number) => void
    recordKill: () => void
    recordResource: () => void
    resetSession: () => void
}

// Math: Level = Floor(Constant * Sqrt(XP))
// XP Level Curve:
// Lvl 1: 0 XP
// Lvl 2: 100 XP
// Lvl 3: 400 XP
// Lvl 4: 900 XP
// XP = (Level/0.1)^2
const LEVEL_CONSTANT = 0.1

const calculateLevel = (xp: number) => {
    return Math.floor(LEVEL_CONSTANT * Math.sqrt(xp)) + 1
}

export const useProgression = create<ProgressionState>()(
    persist(
        (set) => ({
            combatXP: 0,
            miningXP: 0,
            combatLevel: 1,
            miningLevel: 1,
            sessionKills: 0,
            sessionResources: 0,

            addXP: (type, amount) => {
                set((state) => {
                    const currentXP = type === 'COMBAT' ? state.combatXP : state.miningXP
                    const newXP = currentXP + amount
                    const newLevel = calculateLevel(newXP)

                    // TODO: Trigger Level Up Effect if newLevel > currentLevel

                    if (type === 'COMBAT') {
                        return { combatXP: newXP, combatLevel: newLevel }
                    } else {
                        return { miningXP: newXP, miningLevel: newLevel }
                    }
                })
            },

            recordKill: () => set((state) => ({ sessionKills: state.sessionKills + 1 })),
            recordResource: () => set((state) => ({ sessionResources: state.sessionResources + 1 })),

            resetSession: () => set({ sessionKills: 0, sessionResources: 0 })
        }),
        {
            name: 'antigravity-progression',
        }
    )
)
