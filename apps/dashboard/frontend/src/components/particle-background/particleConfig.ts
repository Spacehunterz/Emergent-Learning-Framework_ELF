export const getParticleColor = () => {
  const style = getComputedStyle(document.documentElement)
  return style.getPropertyValue('--theme-particle-color').trim() || '160, 200, 255'
}

export const DEFAULT_MOUSE_RADIUS = 150
export const MAX_PARTICLE_COUNT = 300
