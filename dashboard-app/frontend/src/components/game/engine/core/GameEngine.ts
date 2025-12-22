
import { createGameState, GameState } from './GameState'
import { GameLoop } from './GameLoop'
import { InputManager } from './InputManager'
import { System } from '../systems/System'

export class GameEngine {
    public state: GameState
    public input: InputManager
    public sound: any = null // Injected Service
    private loop: GameLoop
    private systems: System[] = []

    constructor() {
        this.state = createGameState()
        this.input = new InputManager()
        this.loop = new GameLoop(this)
    }

    registerSystem(system: System) {
        this.systems.push(system)
        system.initialize(this)
    }

    start(canvasElement: HTMLElement) {
        this.input.attach(canvasElement)
        this.loop.start()
    }

    stop() {
        this.loop.stop()
        this.input.dispose()
    }

    // Called by GameLoop
    update(delta: number) {
        // Time is now updated in GameLoop before fixedUpdate runs

        // Poll Input
        this.input.update(this.state)

        // Apply Mouse Look to Player Rotation
        const sensitivity = 0.0015 // Slightly reduced for smoother control
        this.state.player.rotation.y -= this.state.input.mouseX * sensitivity
        this.state.player.rotation.x -= this.state.input.mouseY * sensitivity
        // Clamp pitch to ~60 degrees to prevent gimbal lock and wonky behavior
        const maxPitch = Math.PI * 0.33 // ~60 degrees
        this.state.player.rotation.x = Math.max(-maxPitch, Math.min(maxPitch, this.state.player.rotation.x))
        // Update quaternion from euler
        this.state.player.quaternion.setFromEuler(this.state.player.rotation)

        // Run Systems (Variable Update)
        for (const system of this.systems) {
            system.update(delta, this.state)
        }
    }

    // Called by GameLoop
    fixedUpdate(delta: number) {
        // Run Systems (Fixed Physics Update)
        for (const system of this.systems) {
            system.fixedUpdate(delta, this.state)
        }
    }

    // Render Interpolation Stub (optional for Systems to hook into if needed, though React usually handles this via Refs)
    render(alpha: number) {
        // This is where we might interpolate positions for the Renderer to read
        // For now, React components read directly from state in useFrame
        // But for InstancedMesh, we might want to push data here.
    }
}
