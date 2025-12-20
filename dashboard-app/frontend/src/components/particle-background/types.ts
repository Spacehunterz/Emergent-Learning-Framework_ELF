export interface Mouse {
  x: number
  y: number
  radius: number
  isClicked: boolean
  isRightClicked?: boolean
}

export interface ParticleInterface {
  x: number
  y: number
  vx: number
  vy: number
  size: number
  alpha: number
  targetAlpha: number
  baseVx: number
  baseVy: number
  update(mouse: Mouse, width: number, height: number): void
  draw: (ctx: CanvasRenderingContext2D, particleColor: string) => void
}
