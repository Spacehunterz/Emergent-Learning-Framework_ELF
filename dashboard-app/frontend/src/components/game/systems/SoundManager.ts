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
    }
}))
