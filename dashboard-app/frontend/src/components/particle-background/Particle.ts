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

  update(mouse: Mouse, width: number, height: number): boolean {
    const dx = mouse.x - this.x
    const dy = mouse.y - this.y
    const dist = Math.sqrt(dx * dx + dy * dy)
    let collected = false

    // Tractor Beam (Right Click) - STRONG Attraction
    if (mouse.isRightClicked && mouse.x > 0) {
      if (dist < mouse.radius * 4) {
        // Strong Pull
        const force = (1 - dist / (mouse.radius * 4)) * 0.8
        this.vx += (dx / dist) * force
        this.vy += (dy / dist) * force

        // Collection Threshold
        if (dist < 20) {
          collected = true
          // Respawn elsewhere
          this.x = Math.random() * width
          this.y = Math.random() * height
          this.vx = (Math.random() - 0.5) * 0.5
          this.vy = (Math.random() - 0.5) * 0.5
        }
      }
    }

    // Pulse Repulsion (Left Click) - Push away
    else if (mouse.isClicked && mouse.x > 0) {
      if (dist < mouse.radius * 2) {
        const force = (1 - dist / (mouse.radius * 2)) * 0.5
        this.vx -= (dx / dist) * force
        this.vy -= (dy / dist) * force
      }
    }
    // REMOVED: Gentle Repulsion (User wants them to stay put unless sucked)

    // Apply velocity with friction
    this.vx *= 0.96 // Slightly more drag for floaty feel
    this.vy *= 0.96

    // Slowly return to base drift velocity
    if (!mouse.isRightClicked && !mouse.isClicked) {
      // Random wandering force
      this.vx += (Math.random() - 0.5) * 0.002
      this.vy += (Math.random() - 0.5) * 0.002

      this.vx += (this.baseVx - this.vx) * 0.005
      this.vy += (this.baseVy - this.vy) * 0.005
    }

    this.x += this.vx
    this.y += this.vy

    if (this.x < 0) this.x = width
    if (this.x > width) this.x = 0
    if (this.y < 0) this.y = height
    if (this.y > height) this.y = 0

    // Twinkle effect
    if (Math.abs(this.alpha - this.targetAlpha) < 0.01) {
      this.targetAlpha = Math.random() * 0.8 + 0.2 // Keep them somewhat visible
    } else {
      this.alpha += (this.targetAlpha - this.alpha) * 0.02
    }

    return collected
  }

  draw(ctx: CanvasRenderingContext2D, particleColor: string) {
    ctx.fillStyle = 'rgba(' + particleColor + ', ' + (this.alpha * 0.6) + ')'
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
    ctx.fill()
  }
}
