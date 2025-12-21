import { create as createStore } from 'zustand'

class SoundEngine {
    ctx: AudioContext | null = null
    masterGain: GainNode | null = null

    constructor() {
        try {
            const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext
            this.ctx = new AudioContextClass()
            this.masterGain = this.ctx.createGain()
            this.masterGain.gain.value = 0.5 // Default 50% volume
            this.masterGain.connect(this.ctx.destination)
        } catch (e) {
            console.error("AudioContext not supported", e)
        }
    }

    playLaser(type: 'player' | 'enemy' = 'player') {
        if (!this.ctx || !this.masterGain) return

        const osc = this.ctx.createOscillator()
        const gain = this.ctx.createGain()

        osc.connect(gain)
        gain.connect(this.masterGain)

        const now = this.ctx.currentTime

        if (type === 'player') {
            osc.type = 'square'
            osc.frequency.setValueAtTime(800, now)
            osc.frequency.exponentialRampToValueAtTime(100, now + 0.15)
            gain.gain.setValueAtTime(0.5, now)
            gain.gain.exponentialRampToValueAtTime(0.01, now + 0.15)
            osc.start(now)
            osc.stop(now + 0.2)
        } else {
            osc.type = 'sawtooth'
            osc.frequency.setValueAtTime(400, now)
            osc.frequency.exponentialRampToValueAtTime(50, now + 0.3)
            gain.gain.setValueAtTime(0.3, now)
            gain.gain.exponentialRampToValueAtTime(0.01, now + 0.3)
            osc.start(now)
            osc.stop(now + 0.35)
        }
    }

    playExplosion(size: 'small' | 'large' = 'small') {
        if (!this.ctx || !this.masterGain) return
        const now = this.ctx.currentTime

        // White Noise Buffer
        const bufferSize = this.ctx.sampleRate * 2
        const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate)
        const data = buffer.getChannelData(0)
        for (let i = 0; i < bufferSize; i++) {
            data[i] = Math.random() * 2 - 1
        }

        const noise = this.ctx.createBufferSource()
        noise.buffer = buffer

        const filter = this.ctx.createBiquadFilter()
        filter.type = 'lowpass'
        filter.frequency.setValueAtTime(1000, now)
        filter.frequency.exponentialRampToValueAtTime(10, now + (size === 'large' ? 1.0 : 0.4))

        const gain = this.ctx.createGain()
        gain.gain.setValueAtTime(size === 'large' ? 0.8 : 0.4, now)
        gain.gain.exponentialRampToValueAtTime(0.01, now + (size === 'large' ? 1.0 : 0.4))

        noise.connect(filter)
        filter.connect(gain)
        gain.connect(this.masterGain)
        noise.start(now)
        noise.stop(now + 1.2)
    }

    playHit() {
        if (!this.ctx || !this.masterGain) return
        const now = this.ctx.currentTime
        const osc = this.ctx.createOscillator()
        osc.type = 'triangle'
        osc.frequency.setValueAtTime(150, now)
        osc.frequency.exponentialRampToValueAtTime(50, now + 0.1)
        const gain = this.ctx.createGain()
        gain.gain.setValueAtTime(0.5, now)
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.1)
        osc.connect(gain)
        gain.connect(this.masterGain)
        osc.start(now)
        osc.stop(now + 0.15)
    }

    playShieldHit() {
        if (!this.ctx || !this.masterGain) return
        const now = this.ctx.currentTime
        const osc = this.ctx.createOscillator()
        osc.type = 'sine'
        osc.frequency.setValueAtTime(200, now)
        osc.frequency.linearRampToValueAtTime(400, now + 0.1)
        osc.frequency.linearRampToValueAtTime(100, now + 0.3)
        const gain = this.ctx.createGain()
        gain.gain.setValueAtTime(0.4, now)
        gain.gain.linearRampToValueAtTime(0, now + 0.3)
        osc.connect(gain)
        gain.connect(this.masterGain)
        osc.start(now)
        osc.stop(now + 0.35)
    }

    // --- NEW PHASE 4 SOUNDS ---
    ambienceOsc: OscillatorNode | null = null
    ambienceGain: GainNode | null = null

    startAmbience() {
        if (!this.ctx || !this.masterGain || this.ambienceOsc) return
        const now = this.ctx.currentTime
        this.ambienceOsc = this.ctx.createOscillator()
        this.ambienceGain = this.ctx.createGain()
        this.ambienceOsc.type = 'sawtooth'
        this.ambienceOsc.frequency.setValueAtTime(50, now)
        const filter = this.ctx.createBiquadFilter()
        filter.type = 'lowpass'
        filter.frequency.setValueAtTime(120, now)
        this.ambienceGain.gain.setValueAtTime(0, now)
        this.ambienceGain.gain.linearRampToValueAtTime(0.15, now + 2)
        this.ambienceOsc.connect(filter)
        filter.connect(this.ambienceGain)
        this.ambienceGain.connect(this.masterGain)
        this.ambienceOsc.start(now)
    }

    stopAmbience() {
        if (!this.ctx || !this.ambienceOsc || !this.ambienceGain) return
        const now = this.ctx.currentTime
        this.ambienceGain.gain.cancelScheduledValues(now)
        this.ambienceGain.gain.linearRampToValueAtTime(0, now + 1)
        const oldOsc = this.ambienceOsc
        oldOsc.stop(now + 1.1)
        this.ambienceOsc = null
    }

    playUiHover() {
        if (!this.ctx || !this.masterGain) return
        const now = this.ctx.currentTime
        const osc = this.ctx.createOscillator()
        osc.type = 'sine'
        osc.frequency.setValueAtTime(800, now)
        osc.frequency.exponentialRampToValueAtTime(1200, now + 0.05)
        const gain = this.ctx.createGain()
        gain.gain.setValueAtTime(0.05, now)
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.05)
        osc.connect(gain)
        gain.connect(this.masterGain)
        osc.start(now)
        osc.stop(now + 0.05)
    }

    playUiClick() {
        if (!this.ctx || !this.masterGain) return
        const now = this.ctx.currentTime
        const osc = this.ctx.createOscillator()
        osc.type = 'square'
        osc.frequency.setValueAtTime(1200, now)
        osc.frequency.exponentialRampToValueAtTime(600, now + 0.1)
        const gain = this.ctx.createGain()
        gain.gain.setValueAtTime(0.1, now)
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.1)
        osc.connect(gain)
        gain.connect(this.masterGain)
        osc.start(now)
        osc.stop(now + 0.1)
    }

    playLevelUp() {
        if (!this.ctx || !this.masterGain) return
        const now = this.ctx.currentTime
        const freqs = [440, 554.37, 659.25, 880]
        freqs.forEach((f, i) => {
            const osc = this.ctx!.createOscillator()
            const gain = this.ctx!.createGain()
            const start = now + (i * 0.1)
            osc.frequency.setValueAtTime(f, start)
            osc.type = 'triangle'
            gain.gain.setValueAtTime(0, start)
            gain.gain.linearRampToValueAtTime(0.2, start + 0.05)
            gain.gain.exponentialRampToValueAtTime(0.001, start + 0.5)
            osc.connect(gain)
            gain.connect(this.masterGain!)
            osc.start(start)
            osc.stop(start + 0.6)
        })
    }

    playBossSpawn() {
        if (!this.ctx || !this.masterGain) return
        const now = this.ctx.currentTime
        const osc1 = this.ctx.createOscillator()
        const osc2 = this.ctx.createOscillator()
        const gain = this.ctx.createGain()
        osc1.type = 'sawtooth'
        osc2.type = 'sawtooth'
        osc1.frequency.setValueAtTime(60, now)
        osc1.frequency.linearRampToValueAtTime(50, now + 2)
        osc2.frequency.setValueAtTime(62, now)
        osc2.frequency.linearRampToValueAtTime(52, now + 2)
        const filter = this.ctx.createBiquadFilter()
        filter.type = 'lowpass'
        filter.frequency.setValueAtTime(100, now)
        filter.frequency.exponentialRampToValueAtTime(800, now + 1)
        filter.frequency.exponentialRampToValueAtTime(100, now + 2.5)
        gain.gain.setValueAtTime(0, now)
        gain.gain.linearRampToValueAtTime(0.6, now + 0.5)
        gain.gain.linearRampToValueAtTime(0, now + 3)
        osc1.connect(filter)
        osc2.connect(filter)
        filter.connect(gain)
        gain.connect(this.masterGain)
        osc1.start(now)
        osc2.start(now)
        osc1.stop(now + 3)
        osc2.stop(now + 3)
    }

    // --- ENEMY-SPECIFIC DEATH SOUNDS ---

    // Drone death - quick electronic pop/zap
    playDroneDeath() {
        if (!this.ctx || !this.masterGain) return
        const now = this.ctx.currentTime

        const osc = this.ctx.createOscillator()
        osc.type = 'square'
        osc.frequency.setValueAtTime(2000, now)
        osc.frequency.exponentialRampToValueAtTime(100, now + 0.15)

        const gain = this.ctx.createGain()
        gain.gain.setValueAtTime(0.3, now)
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.15)

        osc.connect(gain)
        gain.connect(this.masterGain)
        osc.start(now)
        osc.stop(now + 0.2)
    }

    // Fighter death - metallic crash/shatter
    playFighterDeath() {
        if (!this.ctx || !this.masterGain) return
        const now = this.ctx.currentTime

        // Metallic hit
        const osc1 = this.ctx.createOscillator()
        osc1.type = 'sawtooth'
        osc1.frequency.setValueAtTime(300, now)
        osc1.frequency.exponentialRampToValueAtTime(50, now + 0.3)

        // High metallic ring
        const osc2 = this.ctx.createOscillator()
        osc2.type = 'triangle'
        osc2.frequency.setValueAtTime(1200, now)
        osc2.frequency.exponentialRampToValueAtTime(800, now + 0.4)

        // Noise burst for crash
        const bufferSize = this.ctx.sampleRate * 0.5
        const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate)
        const data = buffer.getChannelData(0)
        for (let i = 0; i < bufferSize; i++) {
            data[i] = Math.random() * 2 - 1
        }
        const noise = this.ctx.createBufferSource()
        noise.buffer = buffer

        const filter = this.ctx.createBiquadFilter()
        filter.type = 'highpass'
        filter.frequency.setValueAtTime(2000, now)

        const gain1 = this.ctx.createGain()
        const gain2 = this.ctx.createGain()
        const noiseGain = this.ctx.createGain()

        gain1.gain.setValueAtTime(0.25, now)
        gain1.gain.exponentialRampToValueAtTime(0.01, now + 0.3)
        gain2.gain.setValueAtTime(0.15, now)
        gain2.gain.exponentialRampToValueAtTime(0.01, now + 0.4)
        noiseGain.gain.setValueAtTime(0.2, now)
        noiseGain.gain.exponentialRampToValueAtTime(0.01, now + 0.2)

        osc1.connect(gain1)
        osc2.connect(gain2)
        noise.connect(filter)
        filter.connect(noiseGain)
        gain1.connect(this.masterGain)
        gain2.connect(this.masterGain)
        noiseGain.connect(this.masterGain)

        osc1.start(now)
        osc2.start(now)
        noise.start(now)
        osc1.stop(now + 0.35)
        osc2.stop(now + 0.45)
        noise.stop(now + 0.25)
    }

    // Elite death - deep rumble with electric crackle
    playEliteDeath() {
        if (!this.ctx || !this.masterGain) return
        const now = this.ctx.currentTime

        // Deep rumble
        const osc1 = this.ctx.createOscillator()
        osc1.type = 'sawtooth'
        osc1.frequency.setValueAtTime(80, now)
        osc1.frequency.exponentialRampToValueAtTime(30, now + 0.8)

        // Electric crackle - multiple short bursts
        for (let i = 0; i < 5; i++) {
            const t = now + i * 0.1
            const crackle = this.ctx.createOscillator()
            crackle.type = 'square'
            crackle.frequency.setValueAtTime(3000 - i * 400, t)
            crackle.frequency.exponentialRampToValueAtTime(500, t + 0.05)
            const cGain = this.ctx.createGain()
            cGain.gain.setValueAtTime(0.15, t)
            cGain.gain.exponentialRampToValueAtTime(0.01, t + 0.05)
            crackle.connect(cGain)
            cGain.connect(this.masterGain)
            crackle.start(t)
            crackle.stop(t + 0.06)
        }

        const filter = this.ctx.createBiquadFilter()
        filter.type = 'lowpass'
        filter.frequency.setValueAtTime(200, now)

        const gain1 = this.ctx.createGain()
        gain1.gain.setValueAtTime(0.4, now)
        gain1.gain.exponentialRampToValueAtTime(0.01, now + 0.8)

        osc1.connect(filter)
        filter.connect(gain1)
        gain1.connect(this.masterGain)
        osc1.start(now)
        osc1.stop(now + 0.85)
    }

    // Boss death - massive explosion with sub-bass
    playBossDeath() {
        if (!this.ctx || !this.masterGain) return
        const now = this.ctx.currentTime

        // Sub-bass thump
        const subOsc = this.ctx.createOscillator()
        subOsc.type = 'sine'
        subOsc.frequency.setValueAtTime(60, now)
        subOsc.frequency.exponentialRampToValueAtTime(20, now + 1.5)

        // Mid explosion
        const midOsc = this.ctx.createOscillator()
        midOsc.type = 'sawtooth'
        midOsc.frequency.setValueAtTime(150, now)
        midOsc.frequency.exponentialRampToValueAtTime(40, now + 1.2)

        // White noise burst
        const bufferSize = this.ctx.sampleRate * 2
        const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate)
        const data = buffer.getChannelData(0)
        for (let i = 0; i < bufferSize; i++) {
            data[i] = Math.random() * 2 - 1
        }
        const noise = this.ctx.createBufferSource()
        noise.buffer = buffer

        const noiseFilter = this.ctx.createBiquadFilter()
        noiseFilter.type = 'lowpass'
        noiseFilter.frequency.setValueAtTime(2000, now)
        noiseFilter.frequency.exponentialRampToValueAtTime(50, now + 1.5)

        const subGain = this.ctx.createGain()
        subGain.gain.setValueAtTime(0.6, now)
        subGain.gain.exponentialRampToValueAtTime(0.01, now + 1.5)

        const midGain = this.ctx.createGain()
        midGain.gain.setValueAtTime(0.4, now)
        midGain.gain.exponentialRampToValueAtTime(0.01, now + 1.2)

        const noiseGain = this.ctx.createGain()
        noiseGain.gain.setValueAtTime(0.5, now)
        noiseGain.gain.exponentialRampToValueAtTime(0.01, now + 1.5)

        subOsc.connect(subGain)
        midOsc.connect(midGain)
        noise.connect(noiseFilter)
        noiseFilter.connect(noiseGain)
        subGain.connect(this.masterGain)
        midGain.connect(this.masterGain)
        noiseGain.connect(this.masterGain)

        subOsc.start(now)
        midOsc.start(now)
        noise.start(now)
        subOsc.stop(now + 1.6)
        midOsc.stop(now + 1.3)
        noise.stop(now + 1.6)
    }

    // Asteroid destruction - rocky crunch/crumble
    playAsteroidDeath() {
        if (!this.ctx || !this.masterGain) return
        const now = this.ctx.currentTime

        // Multiple rock impacts
        for (let i = 0; i < 4; i++) {
            const t = now + i * 0.05
            const osc = this.ctx.createOscillator()
            osc.type = 'triangle'
            osc.frequency.setValueAtTime(200 - i * 30, t)
            osc.frequency.exponentialRampToValueAtTime(50, t + 0.15)

            const gain = this.ctx.createGain()
            gain.gain.setValueAtTime(0.2, t)
            gain.gain.exponentialRampToValueAtTime(0.01, t + 0.15)

            osc.connect(gain)
            gain.connect(this.masterGain)
            osc.start(t)
            osc.stop(t + 0.2)
        }

        // Gravel noise
        const bufferSize = this.ctx.sampleRate * 0.4
        const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate)
        const data = buffer.getChannelData(0)
        for (let i = 0; i < bufferSize; i++) {
            data[i] = Math.random() * 2 - 1
        }
        const noise = this.ctx.createBufferSource()
        noise.buffer = buffer

        const filter = this.ctx.createBiquadFilter()
        filter.type = 'bandpass'
        filter.frequency.setValueAtTime(800, now)
        filter.Q.setValueAtTime(2, now)

        const noiseGain = this.ctx.createGain()
        noiseGain.gain.setValueAtTime(0.15, now)
        noiseGain.gain.exponentialRampToValueAtTime(0.01, now + 0.3)

        noise.connect(filter)
        filter.connect(noiseGain)
        noiseGain.connect(this.masterGain)
        noise.start(now)
        noise.stop(now + 0.35)
    }

    // Generic enemy death based on type
    playEnemyDeath(type: 'drone' | 'fighter' | 'elite' | 'boss' | 'asteroid' | 'scout') {
        switch (type) {
            case 'drone':
            case 'scout':
                this.playDroneDeath()
                break
            case 'fighter':
                this.playFighterDeath()
                break
            case 'elite':
                this.playEliteDeath()
                break
            case 'boss':
                this.playBossDeath()
                break
            case 'asteroid':
                this.playAsteroidDeath()
                break
            default:
                this.playExplosion('small')
        }
    }
}

// Global Singleton
const soundEngine = new SoundEngine()

// React Hook
interface SoundState {
    playLaser: (type?: 'player' | 'enemy') => void
    playExplosion: (size: 'small' | 'large') => void
    playHit: () => void
    playShieldHit: () => void
    startAmbience: () => void
    stopAmbience: () => void
    playUiHover: () => void
    playUiClick: () => void
    playLevelUp: () => void
    playBossSpawn: () => void
    // Enemy-specific death sounds
    playDroneDeath: () => void
    playFighterDeath: () => void
    playEliteDeath: () => void
    playBossDeath: () => void
    playAsteroidDeath: () => void
    playEnemyDeath: (type: 'drone' | 'fighter' | 'elite' | 'boss' | 'asteroid' | 'scout') => void
}

export const useSound = createStore<SoundState>(() => ({
    playLaser: (type: 'player' | 'enemy' = 'player') => {
        if (soundEngine.ctx?.state === 'suspended') soundEngine.ctx.resume()
        soundEngine.playLaser(type)
    },
    playExplosion: (size: 'small' | 'large') => {
        if (soundEngine.ctx?.state === 'suspended') soundEngine.ctx.resume()
        soundEngine.playExplosion(size)
    },
    playHit: () => {
        if (soundEngine.ctx?.state === 'suspended') soundEngine.ctx.resume()
        soundEngine.playHit()
    },
    playShieldHit: () => {
        if (soundEngine.ctx?.state === 'suspended') soundEngine.ctx.resume()
        soundEngine.playShieldHit()
    },
    startAmbience: () => {
        if (soundEngine.ctx?.state === 'suspended') soundEngine.ctx.resume()
        soundEngine.startAmbience()
    },
    stopAmbience: () => soundEngine.stopAmbience(),
    playUiHover: () => {
        if (soundEngine.ctx?.state === 'suspended') soundEngine.ctx.resume()
        soundEngine.playUiHover()
    },
    playUiClick: () => {
        if (soundEngine.ctx?.state === 'suspended') soundEngine.ctx.resume()
        soundEngine.playUiClick()
    },
    playLevelUp: () => {
        if (soundEngine.ctx?.state === 'suspended') soundEngine.ctx.resume()
        soundEngine.playLevelUp()
    },
    playBossSpawn: () => {
        if (soundEngine.ctx?.state === 'suspended') soundEngine.ctx.resume()
        soundEngine.playBossSpawn()
    },
    // Enemy-specific death sounds
    playDroneDeath: () => {
        if (soundEngine.ctx?.state === 'suspended') soundEngine.ctx.resume()
        soundEngine.playDroneDeath()
    },
    playFighterDeath: () => {
        if (soundEngine.ctx?.state === 'suspended') soundEngine.ctx.resume()
        soundEngine.playFighterDeath()
    },
    playEliteDeath: () => {
        if (soundEngine.ctx?.state === 'suspended') soundEngine.ctx.resume()
        soundEngine.playEliteDeath()
    },
    playBossDeath: () => {
        if (soundEngine.ctx?.state === 'suspended') soundEngine.ctx.resume()
        soundEngine.playBossDeath()
    },
    playAsteroidDeath: () => {
        if (soundEngine.ctx?.state === 'suspended') soundEngine.ctx.resume()
        soundEngine.playAsteroidDeath()
    },
    playEnemyDeath: (type: 'drone' | 'fighter' | 'elite' | 'boss' | 'asteroid' | 'scout') => {
        if (soundEngine.ctx?.state === 'suspended') soundEngine.ctx.resume()
        soundEngine.playEnemyDeath(type)
    }
}))
