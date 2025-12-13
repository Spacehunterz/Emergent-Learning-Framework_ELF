import { Particle } from './Particle'
import { Mouse } from './types'

export const drawConnections = (
  ctx: CanvasRenderingContext2D,
  particles: Particle[],
  mouse: Mouse,
  time: number,
  particleColor: string
) => {
  const nearbyParticles: Particle[] = []

  // Pulse animation for connections
  const pulse = Math.sin(time * 0.03) * 0.3 + 0.7
  const clickPulse = mouse.isClicked ? Math.sin(time * 0.1) * 0.2 + 1.2 : 1

  // Find particles near the cursor
  for (const p of particles) {
    const dx = p.x - mouse.x
    const dy = p.y - mouse.y
    const dist = Math.sqrt(dx * dx + dy * dy)

    const effectiveRadius = mouse.radius * clickPulse

    if (dist < effectiveRadius) {
      nearbyParticles.push(p)

      const baseOpacity = (1 - dist / effectiveRadius) * 0.6
      const opacity = baseOpacity * pulse
      const lineWidth = mouse.isClicked ? 1.5 + Math.sin(time * 0.08 + dist * 0.01) * 0.5 : 1

      ctx.strokeStyle = 'rgba(' + particleColor + ', ' + opacity + ')'
      ctx.lineWidth = lineWidth
      ctx.beginPath()
      ctx.moveTo(mouse.x, mouse.y)
      ctx.lineTo(p.x, p.y)
      ctx.stroke()
    }
  }

  // Draw connections between nearby particles (the web effect)
  for (let i = 0; i < nearbyParticles.length; i++) {
    for (let j = i + 1; j < nearbyParticles.length; j++) {
      const p1 = nearbyParticles[i]
      const p2 = nearbyParticles[j]
      const dx = p1.x - p2.x
      const dy = p1.y - p2.y
      const dist = Math.sqrt(dx * dx + dy * dy)

      const maxDist = mouse.radius * 0.8 * clickPulse

      if (dist < maxDist) {
        const baseOpacity = (1 - dist / maxDist) * 0.3
        const shimmer = Math.sin(time * 0.05 + i * 0.5 + j * 0.3) * 0.15 + 0.85
        const opacity = baseOpacity * shimmer

        ctx.strokeStyle = 'rgba(' + particleColor + ', ' + opacity + ')'
        ctx.lineWidth = mouse.isClicked ? 0.8 : 0.5
        ctx.beginPath()
        ctx.moveTo(p1.x, p1.y)
        ctx.lineTo(p2.x, p2.y)
        ctx.stroke()
      }
    }
  }

  // Draw a subtle glow at cursor position when near particles
  if (nearbyParticles.length > 0) {
    const glowSize = mouse.isClicked ? 30 + Math.sin(time * 0.1) * 10 : 20
    const glowOpacity = mouse.isClicked ? 0.5 : 0.3

    const gradient = ctx.createRadialGradient(
      mouse.x, mouse.y, 0,
      mouse.x, mouse.y, glowSize
    )
    gradient.addColorStop(0, 'rgba(' + particleColor + ', ' + (glowOpacity * pulse) + ')')
    gradient.addColorStop(1, 'rgba(' + particleColor + ', 0)')
    ctx.fillStyle = gradient
    ctx.beginPath()
    ctx.arc(mouse.x, mouse.y, glowSize, 0, Math.PI * 2)
    ctx.fill()
  }
}
