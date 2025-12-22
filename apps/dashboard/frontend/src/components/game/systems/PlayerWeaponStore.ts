import { create } from 'zustand'
import { WEAPON_TYPES, WeaponType } from './WeaponTypes'

interface WeaponUpgrades {
    damageMultiplier: number    // 1.0 = base, 1.5 = +50% damage
    fireRateMultiplier: number  // 1.0 = base, 1.5 = +50% fire rate
    energyEfficiency: number    // 1.0 = base, 0.7 = 30% less energy cost
}

interface PlayerWeaponState {
    // Currently equipped weapon
    equippedWeaponId: string

    // Unlocked weapon IDs
    unlockedWeapons: string[]

    // Per-weapon upgrades
    weaponUpgrades: Record<string, WeaponUpgrades>

    // Player credits (separate from score for shop)
    credits: number

    // Actions
    equipWeapon: (weaponId: string) => void
    unlockWeapon: (weaponId: string) => boolean // returns true if successful
    upgradeWeapon: (weaponId: string, upgradeType: 'damage' | 'fireRate' | 'energy') => boolean
    addCredits: (amount: number) => void
    spendCredits: (amount: number) => boolean // returns true if successful
    getEquippedWeapon: () => WeaponType
    getEffectiveStats: (weaponId: string) => {
        damage: number
        fireRate: number
        energyCost: number
    }
    getUpgradeCost: (weaponId: string, upgradeType: 'damage' | 'fireRate' | 'energy') => number
    getUpgradeLevel: (weaponId: string, upgradeType: 'damage' | 'fireRate' | 'energy') => number

    // Ship Upgrades
    shipUpgrades: {
        shield: number // 0-5
        hull: number   // 0-5
        energy: number // 0-5
        power: number  // 0-5
    }
    upgradeShipSystem: (type: 'shield' | 'hull' | 'energy' | 'power') => boolean
    getShipUpgradeCost: (type: 'shield' | 'hull' | 'energy' | 'power') => number
}

// Upgrade costs scale with level
const getUpgradeCostForLevel = (level: number): number => {
    const baseCosts = [500, 1000, 2000, 4000, 8000] // Levels 1-5
    return baseCosts[Math.min(level, baseCosts.length - 1)] || 8000
}

// Max upgrade level
const MAX_UPGRADE_LEVEL = 5

export const usePlayerWeaponStore = create<PlayerWeaponState>((set, get) => ({
    equippedWeaponId: 'plasma_bolt',
    unlockedWeapons: ['plasma_bolt'], // Start with default weapon unlocked
    weaponUpgrades: {
        plasma_bolt: { damageMultiplier: 1, fireRateMultiplier: 1, energyEfficiency: 1 }
    },
    credits: 0,

    equipWeapon: (weaponId) => {
        const state = get()
        if (state.unlockedWeapons.includes(weaponId)) {
            set({ equippedWeaponId: weaponId })
        }
    },

    unlockWeapon: (weaponId) => {
        const state = get()
        const weapon = WEAPON_TYPES[weaponId]
        if (!weapon || state.unlockedWeapons.includes(weaponId)) {
            return false
        }

        if (state.credits >= weapon.price) {
            set({
                credits: state.credits - weapon.price,
                unlockedWeapons: [...state.unlockedWeapons, weaponId],
                weaponUpgrades: {
                    ...state.weaponUpgrades,
                    [weaponId]: { damageMultiplier: 1, fireRateMultiplier: 1, energyEfficiency: 1 }
                }
            })
            return true
        }
        return false
    },

    upgradeWeapon: (weaponId, upgradeType) => {
        const state = get()
        if (!state.unlockedWeapons.includes(weaponId)) return false

        const currentUpgrades = state.weaponUpgrades[weaponId] || {
            damageMultiplier: 1,
            fireRateMultiplier: 1,
            energyEfficiency: 1
        }

        // Calculate current level based on multiplier
        let currentLevel = 0
        let currentValue = 1
        let newValue = 1

        switch (upgradeType) {
            case 'damage':
                currentLevel = Math.round((currentUpgrades.damageMultiplier - 1) / 0.15)
                if (currentLevel >= MAX_UPGRADE_LEVEL) return false
                newValue = 1 + (currentLevel + 1) * 0.15 // +15% per level
                break
            case 'fireRate':
                currentLevel = Math.round((currentUpgrades.fireRateMultiplier - 1) / 0.1)
                if (currentLevel >= MAX_UPGRADE_LEVEL) return false
                newValue = 1 + (currentLevel + 1) * 0.1 // +10% per level
                break
            case 'energy':
                currentLevel = Math.round((1 - currentUpgrades.energyEfficiency) / 0.08)
                if (currentLevel >= MAX_UPGRADE_LEVEL) return false
                newValue = 1 - (currentLevel + 1) * 0.08 // -8% per level
                break
        }

        const cost = getUpgradeCostForLevel(currentLevel)
        if (state.credits < cost) return false

        const newUpgrades = { ...currentUpgrades }
        switch (upgradeType) {
            case 'damage':
                newUpgrades.damageMultiplier = newValue
                break
            case 'fireRate':
                newUpgrades.fireRateMultiplier = newValue
                break
            case 'energy':
                newUpgrades.energyEfficiency = newValue
                break
        }

        set({
            credits: state.credits - cost,
            weaponUpgrades: {
                ...state.weaponUpgrades,
                [weaponId]: newUpgrades
            }
        })
        return true
    },

    addCredits: (amount) => {
        set((state) => ({ credits: state.credits + amount }))
    },

    spendCredits: (amount) => {
        const state = get()
        if (state.credits >= amount) {
            set({ credits: state.credits - amount })
            return true
        }
        return false
    },

    getEquippedWeapon: () => {
        const state = get()
        return WEAPON_TYPES[state.equippedWeaponId] || WEAPON_TYPES.plasma_bolt
    },

    getEffectiveStats: (weaponId) => {
        const state = get()
        const weapon = WEAPON_TYPES[weaponId]
        const upgrades = state.weaponUpgrades[weaponId] || {
            damageMultiplier: 1,
            fireRateMultiplier: 1,
            energyEfficiency: 1
        }

        return {
            damage: Math.round(weapon.damage * upgrades.damageMultiplier),
            fireRate: weapon.fireRate * upgrades.fireRateMultiplier,
            energyCost: Math.round(weapon.energyCost * upgrades.energyEfficiency)
        }
    },

    getUpgradeCost: (weaponId, upgradeType) => {
        const state = get()
        const upgrades = state.weaponUpgrades[weaponId] || {
            damageMultiplier: 1,
            fireRateMultiplier: 1,
            energyEfficiency: 1
        }

        let currentLevel = 0
        switch (upgradeType) {
            case 'damage':
                currentLevel = Math.round((upgrades.damageMultiplier - 1) / 0.15)
                break
            case 'fireRate':
                currentLevel = Math.round((upgrades.fireRateMultiplier - 1) / 0.1)
                break
            case 'energy':
                currentLevel = Math.round((1 - upgrades.energyEfficiency) / 0.08)
                break
        }

        if (currentLevel >= MAX_UPGRADE_LEVEL) return -1 // Max level
        return getUpgradeCostForLevel(currentLevel)
    },

    getUpgradeLevel: (weaponId, upgradeType) => {
        const state = get()
        const upgrades = state.weaponUpgrades[weaponId] || {
            damageMultiplier: 1,
            fireRateMultiplier: 1,
            energyEfficiency: 1
        }

        switch (upgradeType) {
            case 'damage':
                return Math.round((upgrades.damageMultiplier - 1) / 0.15)
            case 'fireRate':
                return Math.round((upgrades.fireRateMultiplier - 1) / 0.1)
            case 'energy':
                return Math.round((1 - upgrades.energyEfficiency) / 0.08)
        }
        return 0
    },

    // --- SHIP SYSTEM UPGRADES ---
    shipUpgrades: {
        shield: 0,
        hull: 0,
        energy: 0,
        power: 0
    },

    upgradeShipSystem: (type) => {
        const state = get()
        const currentLevel = state.shipUpgrades[type]
        if (currentLevel >= MAX_UPGRADE_LEVEL) return false

        const cost = getUpgradeCostForLevel(currentLevel)
        if (state.credits < cost) return false

        set({
            credits: state.credits - cost,
            shipUpgrades: {
                ...state.shipUpgrades,
                [type]: currentLevel + 1
            }
        })
        return true
    },

    getShipUpgradeCost: (type) => {
        const state = get()
        const currentLevel = state.shipUpgrades[type]
        if (currentLevel >= MAX_UPGRADE_LEVEL) return -1
        return getUpgradeCostForLevel(currentLevel)
    }
}))

// Hook to sync score with credits (earn credits from kills)
export const useSyncCreditsFromScore = () => {
    const addCredits = usePlayerWeaponStore(s => s.addCredits)
    return { addCredits }
}
