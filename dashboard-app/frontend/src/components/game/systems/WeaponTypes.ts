// Player Weapon Types - Designed by Codex
// Each weapon has unique projectile behavior and visual style

export interface WeaponType {
    id: string
    name: string
    description: string
    colors: string[]
    projectileType: 'standard' | 'expanding_wave' | 'chain' | 'piercing' | 'spread' | 'gravity' | 'grid' | 'delayed_burst' | 'spiral'
    speed: number
    damage: number
    energyCost: number
    fireRate: number // shots per second
    special: Record<string, any>
    price: number
    unlocked: boolean
}

export const WEAPON_TYPES: Record<string, WeaponType> = {
    // Default starting weapon
    plasma_bolt: {
        id: 'plasma_bolt',
        name: 'PLASMA BOLT',
        description: 'Standard dual plasma cannons. Reliable and energy efficient.',
        colors: ['#38bdf8', '#ffffff'],
        projectileType: 'standard',
        speed: 150,
        damage: 15,
        energyCost: 5,
        fireRate: 2,
        special: {},
        price: 0,
        unlocked: true
    },

    // Ripple Cannon - AOE expanding wave
    ripple_cannon: {
        id: 'ripple_cannon',
        name: 'RIPPLE CANNON',
        description: 'Expanding ring wave. Easier to hit, great for crowd control.',
        colors: ['#00ffff', '#67e8f9', '#ffffff'],
        projectileType: 'expanding_wave',
        speed: 130,
        damage: 12,
        energyCost: 18,
        fireRate: 1.8,
        special: {
            startRadius: 2,
            maxRadius: 40,
            expandRate: 80
        },
        price: 2500,
        unlocked: false
    },

    // Chain Lightning - bounces between enemies
    chain_lightning: {
        id: 'chain_lightning',
        name: 'CHAIN LIGHTNING',
        description: 'Electric bolt that bounces between nearby enemies.',
        colors: ['#818cf8', '#a78bfa', '#ffffff'],
        projectileType: 'chain',
        speed: 170,
        damage: 18,
        energyCost: 22,
        fireRate: 1.5,
        special: {
            maxBounces: 4,
            bounceRange: 60,
            damageDecay: 0.25
        },
        price: 5000,
        unlocked: false
    },

    // Ballistic Railgun - piercing high damage
    ballistic_railgun: {
        id: 'ballistic_railgun',
        name: 'BALLISTIC RAILGUN',
        description: 'High-velocity slug that pierces through all enemies.',
        colors: ['#f472b6', '#ffffff', '#ef4444'],
        projectileType: 'piercing',
        speed: 450,
        damage: 45,
        energyCost: 35,
        fireRate: 0.6,
        special: {
            pierceCount: 999,
            trailLength: 50
        },
        price: 7500,
        unlocked: false
    },

    // Plasma Scatter - shotgun spread
    plasma_scatter: {
        id: 'plasma_scatter',
        name: 'PLASMA SCATTER',
        description: 'Shotgun-style burst of pellets. Devastating at close range.',
        colors: ['#a3e635', '#facc15', '#ffffff'],
        projectileType: 'spread',
        speed: 210,
        damage: 8, // per pellet
        energyCost: 16,
        fireRate: 3.2,
        special: {
            pelletCount: 7,
            spreadAngle: 25,
            pelletLifetime: 0.8
        },
        price: 3000,
        unlocked: false
    },

    // Gravitas Anchor - gravity well
    gravitas_anchor: {
        id: 'gravitas_anchor',
        name: 'GRAVITAS ANCHOR',
        description: 'Deploys gravity well that pulls and damages enemies.',
        colors: ['#6366f1', '#2dd4bf', '#ffffff'],
        projectileType: 'gravity',
        speed: 110,
        damage: 5, // per tick
        energyCost: 28,
        fireRate: 0.9,
        special: {
            deployTime: 0.5,
            pullRadius: 80,
            pullStrength: 40,
            duration: 3
        },
        price: 8000,
        unlocked: false
    },

    // Photon Lattice - grid damage
    photon_lattice: {
        id: 'photon_lattice',
        name: 'PHOTON LATTICE',
        description: 'Creates expanding laser grid that damages on contact.',
        colors: ['#fbbf24', '#ffffff', '#f59e0b'],
        projectileType: 'grid',
        speed: 150,
        damage: 10,
        energyCost: 24,
        fireRate: 1.2,
        special: {
            gridSize: 60,
            lineCount: 6,
            duration: 2
        },
        price: 6000,
        unlocked: false
    },

    // Nova Spike - delayed explosion
    nova_spike: {
        id: 'nova_spike',
        name: 'NOVA SPIKE',
        description: 'Sticks to target then detonates with radial burst.',
        colors: ['#fb923c', '#ffffff', '#dc2626'],
        projectileType: 'delayed_burst',
        speed: 180,
        damage: 25,
        energyCost: 20,
        fireRate: 1.4,
        special: {
            stickDuration: 0.5,
            explosionRadius: 60,
            explosionDamage: 35
        },
        price: 4500,
        unlocked: false
    },

    // Phase Winder - dual spiral double-hit
    phase_winder: {
        id: 'phase_winder',
        name: 'PHASE WINDER',
        description: 'Twin spiraling shots that phase through and hit twice.',
        colors: ['#e879f9', '#22d3ee', '#ffffff'],
        projectileType: 'spiral',
        speed: 240,
        damage: 14, // per hit, hits twice
        energyCost: 19,
        fireRate: 2,
        special: {
            spiralRadius: 8,
            spiralSpeed: 15,
            hitsPerTarget: 2
        },
        price: 5500,
        unlocked: false
    }
}

// Get weapon by ID
export const getWeapon = (id: string): WeaponType => {
    return WEAPON_TYPES[id] || WEAPON_TYPES.plasma_bolt
}

// Get all weapons as array
export const getAllWeapons = (): WeaponType[] => {
    return Object.values(WEAPON_TYPES)
}

// Get unlocked weapons
export const getUnlockedWeapons = (): WeaponType[] => {
    return Object.values(WEAPON_TYPES).filter(w => w.unlocked)
}
