
import { GameEngine } from './GameEngine'

export class GameLoop {
    private engine: GameEngine
    private rafId: number = 0
    private lastTime: number = 0
    private accumulator: number = 0
    private readonly fixedDelta: number = 1 / 60
    private isRunning: boolean = false

    constructor(engine: GameEngine) {
        this.engine = engine
    }

    start() {
        if (this.isRunning) return
        console.log('GameLoop: Starting...')
        this.isRunning = true
        this.lastTime = performance.now()
        this.accumulator = 0
        this.tick()
    }

    stop() {
        this.isRunning = false
        cancelAnimationFrame(this.rafId)
    }

    private tick = () => {
        if (!this.isRunning) return
        // console.log('Tick') // Spammy, but proves it runs

        const now = performance.now()
        // Cap frame time to 100ms to prevent death spiral
        const frameTime = Math.min((now - this.lastTime) / 1000, 0.1)
        this.lastTime = now

        this.accumulator += frameTime

        // Update time tracking BEFORE systems run
        this.engine.state.time.elapsed += frameTime
        this.engine.state.time.delta = frameTime

        // Fixed Update (Physics)
        while (this.accumulator >= this.fixedDelta) {
            this.engine.fixedUpdate(this.fixedDelta)
            this.accumulator -= this.fixedDelta
        }

        // Render Update (Visuals)
        const alpha = this.accumulator / this.fixedDelta
        this.engine.update(frameTime) // Variable update for input/camera
        this.engine.render(alpha)      // Interpolation happens here

        this.rafId = requestAnimationFrame(this.tick)
    }
}
