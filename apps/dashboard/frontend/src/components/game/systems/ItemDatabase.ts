
export type ItemRarity = 'COMMON' | 'UNCOMMON' | 'RARE' | 'EPIC' | 'LEGENDARY'
export type ItemType = 'WEAPON' | 'MINING_TOOL' | 'SHIELD' | 'ENGINE'

export interface GameItem {
    id: string
    name: string
    type: ItemType
    rarity: ItemRarity
    levelRequirement: number
    isPremium: boolean // For future monetization
    description: string
    stats: {
        damage?: number
        fireRate?: number // Shots per second
        heatGeneration?: number
        coolingRate?: number
        miningPower?: number
        shieldCapacity?: number
        speedMultiplier?: number
    }
}

export const ITEM_DATABASE: Record<string, GameItem> = {
    'weapon_pulse_mk1': {
        id: 'weapon_pulse_mk1',
        name: 'Pulse Laser Mk.I',
        type: 'WEAPON',
        rarity: 'COMMON',
        levelRequirement: 1,
        isPremium: false,
        description: 'Standard issue rapid-fire energy weapon.',
        stats: {
            damage: 10,
            fireRate: 5,
            heatGeneration: 5,
            coolingRate: 20
        }
    },
    'mining_beam_mk1': {
        id: 'mining_beam_mk1',
        name: 'Prospector Beam',
        type: 'MINING_TOOL',
        rarity: 'COMMON',
        levelRequirement: 1,
        isPremium: false,
        description: 'Continuous beam for extracting data fragments.',
        stats: {
            miningPower: 10,
            heatGeneration: 2,
            coolingRate: 10
        }
    }
}
