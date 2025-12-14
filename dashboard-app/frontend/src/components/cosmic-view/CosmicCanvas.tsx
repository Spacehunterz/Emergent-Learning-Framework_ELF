import { Canvas } from '@react-three/fiber'
import { Preload } from '@react-three/drei'
import { CosmicLighting } from './CosmicLighting'
import { CameraController } from './CameraController'
import { CosmicBackground } from './CosmicBackground'
import { SolarSystemGroup } from './SolarSystemGroup'
import { UfoTrails } from './UfoTrails'
import { useCosmicStore } from '../../stores'
import type { CosmicHierarchy, CelestialBody } from './types'
import { useMemo, useEffect } from 'react'

interface CosmicCanvasProps {
  cosmicData: CosmicHierarchy
  onSelectBody: (location: string) => void
}

export function CosmicCanvas({ cosmicData, onSelectBody }: CosmicCanvasProps) {
  const selectedBody = useCosmicStore((s) => s.selectedBody)
  const hoveredBody = useCosmicStore((s) => s.hoveredBody)
  const selectBody = useCosmicStore((s) => s.selectBody)
  const hoverBody = useCosmicStore((s) => s.hoverBody)
  const setCameraTarget = useCosmicStore((s) => s.setCameraTarget)

  // Find the selected/hovered body data
  const selectedBodyData = useMemo(() => {
    if (!selectedBody) return null
    for (const system of cosmicData.systems) {
      const body = system.allBodies.find((b) => b.id === selectedBody)
      if (body) return { body, system }
    }
    return null
  }, [selectedBody, cosmicData])

  const hoveredBodyData = useMemo(() => {
    if (!hoveredBody || selectedBody) return null // Don't show hover if selected
    for (const system of cosmicData.systems) {
      const body = system.allBodies.find((b) => b.id === hoveredBody)
      if (body) return { body, system }
    }
    return null
  }, [hoveredBody, selectedBody, cosmicData])

  // Move camera to selected body
  useEffect(() => {
    if (selectedBodyData) {
      const { body, system } = selectedBodyData
      // For sun, target the system center
      if (body.type === 'sun') {
        setCameraTarget(system.position)
      } else {
        // For planets/moons, estimate position based on orbit
        // (The actual animated position is handled by the body components)
        const estimatedPos: [number, number, number] = [
          system.position[0] + body.orbitRadius * 0.7,
          system.position[1],
          system.position[2] + body.orbitRadius * 0.7,
        ]
        setCameraTarget(estimatedPos)
      }
    } else {
      // Reset to origin when deselected
      setCameraTarget([0, 0, 0])
    }
  }, [selectedBodyData, setCameraTarget])

  // Handle body selection - update store and call external handler
  const handleSelectBody = (location: string) => {
    selectBody(location)
    onSelectBody(location)
  }

  // Handle click on empty space to deselect
  const handleCanvasClick = () => {
    if (selectedBody) {
      selectBody(null)
    }
  }

  // Calculate overlay position based on body
  const getOverlayPosition = (
    body: CelestialBody,
    system: (typeof cosmicData.systems)[0]
  ): [number, number, number] => {
    // For sun, position above center
    if (body.type === 'sun') {
      return [
        system.position[0],
        system.position[1] + body.radius + 5,
        system.position[2],
      ]
    }
    // For planets/moons, estimate position (actual position updates via animation)
    return [
      system.position[0] + body.orbitRadius,
      system.position[1] + body.radius + 3,
      system.position[2],
    ]
  }

  return (
    <Canvas
      camera={{
        position: [0, 60, 80],  // Above and back, looking down at orbital plane
        fov: 45,
        near: 0.1,
        far: 2000,
      }}
      gl={{
        antialias: true,
        alpha: true,
        powerPreference: 'high-performance',
      }}
      onPointerMissed={handleCanvasClick}
      style={{ background: 'transparent' }}
    >
      {/* Lighting */}
      <CosmicLighting />

      {/* Background stars - temporarily disabled for visibility */}
      {/* <CosmicBackground /> */}

      {/* Camera controls */}
      <CameraController />

      {/* Solar systems */}
      {cosmicData.systems.map((system) => (
        <SolarSystemGroup
          key={system.id}
          system={system}
          onSelectBody={handleSelectBody}
          onHoverBody={hoverBody}
          selectedBody={selectedBody}
          hoveredBody={hoveredBody}
        />
      ))}

      {/* UFO trails flying between bodies */}
      <UfoTrails systems={cosmicData.systems} />

      {/* Preload assets */}
      <Preload all />
    </Canvas>
  )
}

export default CosmicCanvas
