import { MathUtils } from 'three'

export type EnemyType = 'drone' | 'scout' | 'fighter' | 'boss' | 'asteroid' | 'elite'
export type EnemyState = 'idle' | 'spawning' | 'charging' | 'shielded' | 'enraged' | 'stunned' | 'dying'
export type SizeClass = 'small' | 'medium' | 'large' | 'boss'

export interface EnemyVisualParams {
    type: EnemyType
    stage: number
    hp: number
    maxHp: number
    state?: EnemyState
    speed?: number
    seed: number
    sizeClass?: SizeClass
    distance?: number
    lastHp?: number
    damageFlashValue?: number
}

export interface VisualControllerOutput {
    coreScale: number
    coreOpacity: number
    coreColor: string
    energyScale: number
    energyOpacity: number
    energyColor: string
    noiseOpacity: number
    glitchAmount: number
    trailLength: number
    trailOpacity: number
    orbitSpeed: number
    orbitRadius: number
    pulsePhase: number
    wobble: { x: number; y: number; z: number }
    damageFlash: number
    presence: number
}

const STAGE_PALETTES: Record<number, { primary: string; secondary: string; accent: string; critical: string }> = {
    1: { primary: '#00d4ff', secondary: '#ffffff', accent: '#0066aa', critical: '#ff6666' },
    2: { primary: '#00ffff', secondary: '#8a2be2', accent: '#ff00ff', critical: '#ff4444' },
    3: { primary: '#00ff88', secondary: '#ff69b4', accent: '#88ff00', critical: '#ff3333' },
    4: { primary: '#9966ff', secondary: '#ffffff', accent: '#cc66ff', critical: '#ff2222' },
    5: { primary: '#ff8800', secondary: '#ffcc00', accent: '#ff4400', critical: '#ff0000' },
    6: { primary: '#00ccff', secondary: '#66ffff', accent: '#9966ff', critical: '#ff4466' },
    7: { primary: '#d4a574', secondary: '#c4956a', accent: '#ffd700', critical: '#ff5544' },
    8: { primary: '#88cc00', secondary: '#ffff00', accent: '#00ff00', critical: '#ff6633' },
    9: { primary: '#cc8844', secondary: '#aa6622', accent: '#ffaa44', critical: '#ff4422' },
    10: { primary: '#7A5CFF', secondary: '#FF5FBE', accent: '#48D1FF', critical: '#ff3366' },
    11: { primary: '#44ff44', secondary: '#ffff00', accent: '#00ff00', critical: '#ff2200' },
    12: { primary: '#4488ff', secondary: '#ffffff', accent: '#00ffff', critical: '#ff4455' },
    13: { primary: '#6600cc', secondary: '#9933ff', accent: '#000000', critical: '#ff1144' },
    14: { primary: '#ff00ff', secondary: '#00ffff', accent: '#ffff00', critical: '#ff0055' },
    15: { primary: '#8b4513', secondary: '#ff7f50', accent: '#deb887', critical: '#ff3322' },
    16: { primary: '#001133', secondary: '#00ffff', accent: '#0066ff', critical: '#ff2266' },
    17: { primary: '#ff3300', secondary: '#ff8800', accent: '#000000', critical: '#ff0000' },
    18: { primary: '#00ffff', secondary: '#ff00ff', accent: '#ffffff', critical: '#ff1155' },
    19: { primary: '#ffffff', secondary: '#ffd700', accent: '#88ccff', critical: '#ff4488' },
    20: { primary: '#ff0000', secondary: '#000000', accent: '#ff6600', critical: '#ff0000' },
}

const SIZE_CLASS_SCALE: Record<SizeClass, number> = {
    small: 1,
    medium: 1.5,
    large: 2,
    boss: 3,
}

function seededRandom(seed: number): number {
    const x = Math.sin(seed * 12.9898 + seed * 78.233) * 43758.5453
    return x - Math.floor(x)
}

function seededNoise(seed: number, time: number, frequency: number = 1): number {
    const phase = seed * Math.PI * 2
    return Math.sin(time * frequency + phase)
}

function seededNoise3(seed: number, time: number, freqs: [number, number, number]): { x: number; y: number; z: number } {
    const phase = seed * Math.PI * 2
    return {
        x: Math.sin(time * freqs[0] + phase),
        y: Math.cos(time * freqs[1] + phase * 1.3),
        z: Math.sin(time * freqs[2] + phase * 0.7),
    }
}

export function computeEnemyVisuals(params: EnemyVisualParams, time: number, beat: number = 0): VisualControllerOutput {
    const {
        type,
        stage,
        hp,
        maxHp,
        state = 'idle',
        speed = 0,
        seed,
        sizeClass = 'medium',
        distance = 50,
        lastHp = hp,
        damageFlashValue = 0,
    } = params

    const palette = STAGE_PALETTES[stage] || STAGE_PALETTES[2]
    const hpNormalized = hp / maxHp
    const sizeScale = SIZE_CLASS_SCALE[sizeClass]

    // Damage flash: 1 when just hit, decays over time
    const damageFlash = hp < lastHp ? 1 : Math.max(0, damageFlashValue - 0.1)

    // Base visual parameters
    const baseCore = {
        scale: sizeScale,
        opacity: 0.9,
    }

    const baseEnergy = {
        scale: sizeScale * 1.2,
        opacity: 0.6,
    }

    // HP-based color selection
    let coreColor = palette.primary
    if (hpNormalized < 0.25) coreColor = palette.critical
    else if (hpNormalized < 0.5) coreColor = palette.secondary

    let energyColor = palette.accent

    // Animation parameters
    let glitchAmount = 0
    let pulseSpeed = 2
    let orbitSpeed = 1
    let noiseOpacity = 0.4

    // State-based modifiers
    switch (state) {
        case 'spawning':
            baseCore.opacity = 0.5
            baseEnergy.opacity = 0.2
            break
        case 'charging':
            baseEnergy.scale *= 0.85
            baseEnergy.opacity = 0.9
            pulseSpeed = 6
            break
        case 'shielded':
            energyColor = '#00ffff'
            baseEnergy.opacity = 0.8
            break
        case 'enraged':
            pulseSpeed = 4
            orbitSpeed = 2
            glitchAmount = 0.3
            break
        case 'stunned':
            baseCore.opacity = 0.4
            baseEnergy.opacity = 0.3
            pulseSpeed = 0.5
            noiseOpacity = 0.1
            break
        case 'dying':
            glitchAmount = 0.8
            noiseOpacity = 0.8
            break
    }

    // Type-based modifiers
    switch (type) {
        case 'asteroid':
            orbitSpeed *= 0.5
            break
        case 'drone':
            orbitSpeed *= 1.2
            break
        case 'fighter':
            pulseSpeed *= 1.5
            break
        case 'elite':
            baseEnergy.scale *= 1.3
            glitchAmount *= 0.3
            break
        case 'boss':
            baseCore.scale *= 1.5
            baseEnergy.scale *= 1.8
            orbitSpeed *= 0.7
            break
    }

    // LOD factor: reduce detail at distance
    const lodFactor = MathUtils.clamp(1 - (distance - 30) / 100, 0.3, 1)
    noiseOpacity *= lodFactor

    // Presence: how much this enemy "demands attention"
    const presence = MathUtils.clamp(
        (sizeScale / 3) * (1 - distance / 150) * (2 - hpNormalized) * (state === 'enraged' ? 1.5 : 1),
        0,
        1
    )

    // Time-based animations using seeded noise
    const pulse = seededNoise(seed, time, pulseSpeed)
    const wobble = seededNoise3(seed, time, [0.8, 1.1, 0.6])
    const beatPulse = Math.sin(beat * Math.PI * 2) * 0.5 + 0.5

    // Final computed values
    const coreScale = baseCore.scale * (1 + pulse * 0.05)
    const energyScale = baseEnergy.scale * (1 + pulse * 0.1 + beatPulse * 0.05 * presence)
    const energyOpacity = baseEnergy.opacity * (0.8 + pulse * 0.2)

    // Glitch: probabilistic based on glitchAmount
    const shouldGlitch = glitchAmount > 0 && seededRandom(seed + Math.floor(time * 10)) > (1 - glitchAmount * 0.1)

    return {
        coreScale,
        coreOpacity: baseCore.opacity,
        coreColor: damageFlash > 0.5 ? '#ffffff' : coreColor,
        energyScale,
        energyOpacity,
        energyColor,
        noiseOpacity,
        glitchAmount: shouldGlitch ? glitchAmount : 0,
        trailLength: Math.max(2, 5 * lodFactor * (1 + speed * 0.1)),
        trailOpacity: 0.4 * lodFactor,
        orbitSpeed,
        orbitRadius: 2 * baseEnergy.scale,
        pulsePhase: pulse,
        wobble: {
            x: wobble.x * 0.1,
            y: wobble.y * 0.1,
            z: wobble.z * 0.05,
        },
        damageFlash,
        presence,
    }
}

export function getStageMotion(stage: number): { verb: string; rotSpeed: number; wobbleScale: number } {
    const motions: Record<number, { verb: string; rotSpeed: number; wobbleScale: number }> = {
        1: { verb: 'hover', rotSpeed: 0.3, wobbleScale: 0.5 },
        2: { verb: 'pulse', rotSpeed: 0.5, wobbleScale: 1 },
        3: { verb: 'breathe', rotSpeed: 0.4, wobbleScale: 1.2 },
        4: { verb: 'glitch', rotSpeed: 0.6, wobbleScale: 0.8 },
        5: { verb: 'burn', rotSpeed: 0.7, wobbleScale: 1.5 },
        6: { verb: 'freeze', rotSpeed: 0.2, wobbleScale: 0.3 },
        7: { verb: 'ancient', rotSpeed: 0.15, wobbleScale: 0.4 },
        8: { verb: 'swarm', rotSpeed: 0.8, wobbleScale: 1.3 },
        9: { verb: 'mechanical', rotSpeed: 0.4, wobbleScale: 0.2 },
        10: { verb: 'cosmic', rotSpeed: 0.35, wobbleScale: 1.1 },
        11: { verb: 'radiate', rotSpeed: 0.5, wobbleScale: 1.4 },
        12: { verb: 'arc', rotSpeed: 0.6, wobbleScale: 0.9 },
        13: { verb: 'absorb', rotSpeed: 0.25, wobbleScale: 0.6 },
        14: { verb: 'shimmer', rotSpeed: 0.45, wobbleScale: 1.0 },
        15: { verb: 'pulse', rotSpeed: 0.55, wobbleScale: 1.2 },
        16: { verb: 'drift', rotSpeed: 0.2, wobbleScale: 0.7 },
        17: { verb: 'erupt', rotSpeed: 0.7, wobbleScale: 1.6 },
        18: { verb: 'flicker', rotSpeed: 0.9, wobbleScale: 0.5 },
        19: { verb: 'radiant', rotSpeed: 0.3, wobbleScale: 0.8 },
        20: { verb: 'infernal', rotSpeed: 0.8, wobbleScale: 1.4 },
    }
    return motions[stage] || motions[2]
}

export function getStagePalette(stage: number) {
    return STAGE_PALETTES[stage] || STAGE_PALETTES[2]
}
