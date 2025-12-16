import { useRef, useEffect } from 'react'
import { useThree, useFrame } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import * as THREE from 'three'
import { useCosmicStore } from '../../stores'

export function CameraController() {
  const controlsRef = useRef<any>(null)
  const { camera } = useThree()

  const cameraTarget = useCosmicStore((s) => s.cameraTarget)
  const cameraDistance = useCosmicStore((s) => s.cameraDistance)
  const autoRotate = useCosmicStore((s) => s.autoRotate)
  const selectedBody = useCosmicStore((s) => s.selectedBody)
  const hoveredBody = useCosmicStore((s) => s.hoveredBody)

  // Store target position for smooth interpolation
  const targetRef = useRef(new THREE.Vector3(...cameraTarget))
  const currentTarget = useRef(new THREE.Vector3(...cameraTarget))
  const targetDistance = useRef(cameraDistance)
  const isAnimating = useRef(false)
  const animationTimer = useRef<number | null>(null)

  // Update target when store changes
  useEffect(() => {
    targetRef.current.set(...cameraTarget)
    // Start animating toward new target
    isAnimating.current = true
    if (animationTimer.current) clearTimeout(animationTimer.current)
    animationTimer.current = window.setTimeout(() => {
      isAnimating.current = false
    }, 1500) // Stop auto-animation after 1.5s
  }, [cameraTarget])

  // Update target distance when selection changes
  useEffect(() => {
    if (selectedBody) {
      targetDistance.current = 25 // Zoom in close when selected
    } else {
      targetDistance.current = 80 // Default view of central system
    }
    // Start animating toward new distance
    isAnimating.current = true
    if (animationTimer.current) clearTimeout(animationTimer.current)
    animationTimer.current = window.setTimeout(() => {
      isAnimating.current = false
    }, 1500) // Stop auto-animation after 1.5s
  }, [selectedBody])

  // Smooth camera movement - only when animating (selection change), not during user interaction
  useFrame((_, delta) => {
    if (!controlsRef.current) return

    // Only animate camera position/target when triggered by selection change
    if (isAnimating.current) {
      // Lerp current target toward desired target
      currentTarget.current.lerp(targetRef.current, delta * 2)

      // Update controls target
      controlsRef.current.target.copy(currentTarget.current)

      // Smooth zoom in/out
      const currentDist = camera.position.distanceTo(currentTarget.current)
      if (Math.abs(currentDist - targetDistance.current) > 1) {
        const direction = camera.position.clone().sub(currentTarget.current).normalize()
        const newDist = THREE.MathUtils.lerp(currentDist, targetDistance.current, delta * 2)
        camera.position.copy(currentTarget.current).add(direction.multiplyScalar(newDist))
      }
    }
  })

  // Stop auto-rotate when hovering or selected
  const shouldAutoRotate = autoRotate && !selectedBody && !hoveredBody

  return (
    <OrbitControls
      ref={controlsRef}
      enableDamping
      dampingFactor={0.05}
      minDistance={10}
      maxDistance={500}
      autoRotate={shouldAutoRotate}
      autoRotateSpeed={0.1} // Slowed down from 0.3
      enablePan={true}
      panSpeed={0.5}
      rotateSpeed={0.5}
      zoomSpeed={0.8}
      // Left click to rotate, right click to pan
      mouseButtons={{
        LEFT: THREE.MOUSE.ROTATE,
        MIDDLE: THREE.MOUSE.DOLLY,
        RIGHT: THREE.MOUSE.PAN,
      }}
      // Start with a good viewing angle
      maxPolarAngle={Math.PI * 0.85}
      minPolarAngle={Math.PI * 0.15}
    />
  )
}

export default CameraController
