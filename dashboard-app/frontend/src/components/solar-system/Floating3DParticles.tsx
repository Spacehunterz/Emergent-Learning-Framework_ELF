import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

export function Floating3DParticles({ count = 200 }) {
    const mesh = useRef<THREE.InstancedMesh>(null)
    const dummy = useMemo(() => new THREE.Object3D(), [])

    // Random positions and speeds
    const particles = useMemo(() => {
        const temp = []
        for (let i = 0; i < count; i++) {
            const position = new THREE.Vector3(
                (Math.random() - 0.5) * 100, // Spread X
                (Math.random() - 0.5) * 60,  // Spread Y
                (Math.random() - 0.5) * 100  // Spread Z
            )
            const speed = 0.02 + Math.random() * 0.05
            const phase = Math.random() * Math.PI * 2
            temp.push({ position, speed, phase, yOffset: position.y })
        }
        return temp
    }, [count])

    useFrame((state) => {
        if (!mesh.current) return

        particles.forEach((particle, i) => {
            // Gentle floating animation
            const time = state.clock.getElapsedTime()

            // Update Y position (sine wave)
            particle.position.y = particle.yOffset + Math.sin(time * particle.speed + particle.phase) * 5

            // Slow rotation around center

            // Rotate x/z slightly
            // Keeping original spread but adding slight orbital drift would be cool
            // For now just plain floating

            dummy.position.copy(particle.position)

            // Face camera (billboard effect for cubes? na, just rotate)
            dummy.rotation.x += 0.01
            dummy.rotation.y += 0.01

            // Scale based on "closeness" to wave
            const scale = 0.5 + Math.sin(time + particle.phase) * 0.2
            dummy.scale.set(scale, scale, scale)

            dummy.updateMatrix()
            mesh.current!.setMatrixAt(i, dummy.matrix)
        })

        mesh.current.instanceMatrix.needsUpdate = true
    })

    return (
        <instancedMesh ref={mesh} args={[undefined, undefined, count]}>
            <dodecahedronGeometry args={[0.2, 0]} />
            <meshBasicMaterial color="#22d3ee" transparent opacity={0.6} />
        </instancedMesh>
    )
}
