
import { GameState } from '../core/GameState'
import { GameEngine } from '../core/GameEngine'

export interface System {
    initialize(engine: GameEngine): void
    update(delta: number, state: GameState): void // Variable rate (Input, Camera)
    fixedUpdate(delta: number, state: GameState): void // Fixed rate (Physics, Logic)
}
