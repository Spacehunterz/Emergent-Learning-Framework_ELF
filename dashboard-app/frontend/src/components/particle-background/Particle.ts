import { Mouse, ParticleInterface } from './types'

export class Particle implements ParticleInterface {
  x: number
  y: number
  vx: number
  vy: number
  size: number
  alpha: number
  targetAlpha: number
  baseVx: number
  baseVy: number

  constructor(width: number, height: number) {
    this.x = Math.random() * width
    this.y = Math.random() * height
    this.vx = (Math.random() - 0.5) * 0.3
    this.vy = (Math.random() - 0.5) * 0.3
    this.baseVx = this.vx
    this.baseVy = this.vy
    this.size = Math.random() * 2.5 + 0.5
    this.alpha = Math.random()
    this.targetAlpha = Math.random()
  }

  update(mouse: Mouse, width: number, height: number) {
    // Attraction to cursor when clicked
    if (mouse.isClicked && mouse.x > 0) {
      const dx = mouse.x - this.x
      const dy = mouse.y - this.y
      const dist = Math.sqrt(dx * dx + dy * dy)

      if (dist < mouse.radius * 2) {
        const force = (1 - dist / (mouse.radius * 2)) * 0.08
        this.vx += (dx / dist) * force
        this.vy += (dy / dist) * force
      }
    }

    // Apply velocity with friction
    this.vx *= 0.98
    this.vy *= 0.98

    // Slowly return to base velocity when not attracted
    if (!mouse.isClicked) {
      this.vx += (this.baseVx - this.vx) * 0.01
      this.vy += (this.baseVy - this.vy) * 0.01
    }

    this.x += this.vx
    this.y += this.vy

    if (this.x < 0) this.x = width
    if (this.x > width) this.x = 0
    if (this.y < 0) this.y = height
    if (this.y > height) this.y = 0

    if (Math.abs(this.alpha - this.targetAlpha) < 0.01) {
      this.targetAlpha = Math.random()
    } else {
      this.alpha += (this.targetAlpha - this.alpha) * 0.02
    }
  }

  draw(ctx: CanvasRenderingContext2D, particleColor: string) {
    ctx.fillStyle = 'rgba(' + particleColor + ', ' + (this.alpha * 0.6) + ')'
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
    ctx.fill()
  }
}
