
import { GameState } from './GameState'

// Mapping standard keys to actions
const CONTROLS = {
    FORWARD: ['KeyW', 'ArrowUp'],
    BACKWARD: ['KeyS', 'ArrowDown'],
    LEFT: ['KeyA', 'ArrowLeft'],
    RIGHT: ['KeyD', 'ArrowRight'],
    BOOST: ['ShiftLeft', 'ShiftRight'],
    FIRE: ['Space', 'Mouse0'], // Special case handled manually
}

export class InputManager {
    private keys: Set<string> = new Set()
    private element: HTMLElement | null = null
    private isPointerLocked: boolean = false

    // Mouse Delta (reset every frame)
    private mouseDeltaX: number = 0
    private mouseDeltaY: number = 0

    constructor() {
        window.addEventListener('keydown', this.onKeyDown)
        window.addEventListener('keyup', this.onKeyUp)
        window.addEventListener('mousedown', this.onMouseDown)
        window.addEventListener('mouseup', this.onMouseUp)
        window.addEventListener('mousemove', this.onMouseMove)
        document.addEventListener('pointerlockchange', this.onPointerLockChange)
    }

    attach(element: HTMLElement) {
        this.element = element
    }

    dispose() {
        window.removeEventListener('keydown', this.onKeyDown)
        window.removeEventListener('keyup', this.onKeyUp)
        window.removeEventListener('mousedown', this.onMouseDown)
        window.removeEventListener('mouseup', this.onMouseUp)
        window.removeEventListener('mousemove', this.onMouseMove)
        document.removeEventListener('pointerlockchange', this.onPointerLockChange)
    }

    update(state: GameState) {
        // Map Keys to Input State
        state.input.forward = (this.isPressed(CONTROLS.FORWARD) ? 1 : 0) - (this.isPressed(CONTROLS.BACKWARD) ? 1 : 0)
        state.input.right = (this.isPressed(CONTROLS.RIGHT) ? 1 : 0) - (this.isPressed(CONTROLS.LEFT) ? 1 : 0)
        state.input.up = (this.isPressed(CONTROLS.BOOST) ? 1 : 0) // Boost
        state.input.fire = this.isPressed(CONTROLS.FIRE)

        // Mouse Look
        state.input.mouseX = this.mouseDeltaX
        state.input.mouseY = this.mouseDeltaY

        // Reset Delta
        this.mouseDeltaX = 0
        this.mouseDeltaY = 0
    }

    private isPressed(keys: string[]) {
        return keys.some(k => this.keys.has(k))
    }

    // --- EVENTS ---

    private onKeyDown = (e: KeyboardEvent) => {
        this.keys.add(e.code)
    }

    private onKeyUp = (e: KeyboardEvent) => {
        this.keys.delete(e.code)
    }

    private onMouseDown = (e: MouseEvent) => {
        if (e.button === 0) {
            this.keys.add('Mouse0')
            // Auto-lock on click
            if (!this.isPointerLocked && this.element) {
                this.element.requestPointerLock()
            }
        }
        if (e.button === 2) this.keys.add('Mouse2')
    }

    private onMouseUp = (e: MouseEvent) => {
        if (e.button === 0) this.keys.delete('Mouse0')
        if (e.button === 2) this.keys.delete('Mouse2')
    }

    private onMouseMove = (e: MouseEvent) => {
        if (this.isPointerLocked) {
            this.mouseDeltaX += e.movementX
            this.mouseDeltaY += e.movementY
        }
    }

    private onPointerLockChange = () => {
        this.isPointerLocked = !!document.pointerLockElement
    }
}
