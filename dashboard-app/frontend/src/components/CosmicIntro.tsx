import { useRef, useState, useEffect } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { motion, AnimatePresence } from 'framer-motion'

function WarpStars() {
    const count = 2000
    const mesh = useRef<THREE.InstancedMesh>(null)

    const [dummy] = useState(() => new THREE.Object3D())
    const [positions] = useState(() => {
        const pos = new Float32Array(count * 3)
        for (let i = 0; i < count; i++) {
            pos[i * 3] = (Math.random() - 0.5) * 100
            pos[i * 3 + 1] = (Math.random() - 0.5) * 100
            pos[i * 3 + 2] = (Math.random() - 0.5) * 100
        }
        return pos
    })

    useFrame((state) => {
        if (!mesh.current) return

        // Move stars towards camera (z-axis)
        // Speed increases with time for "warp" effect
        const speed = 2 + state.clock.elapsedTime * 5

        for (let i = 0; i < count; i++) {
            let x = positions[i * 3]
            let y = positions[i * 3 + 1]
            let z = positions[i * 3 + 2]

            z += speed
            if (z > 50) z -= 100 // Reset to back

            positions[i * 3 + 2] = z

            dummy.position.set(x, y, z)

            // Streak effect: Scale z based on speed
            dummy.scale.z = 1 + speed * 2
            dummy.updateMatrix()

            mesh.current.setMatrixAt(i, dummy.matrix)
        }
        mesh.current.instanceMatrix.needsUpdate = true
    })

    return (
        <instancedMesh ref={mesh} args={[undefined, undefined, count]}>
            <boxGeometry args={[0.1, 0.1, 0.5]} />
            <meshBasicMaterial color="#a78bfa" transparent opacity={0.8} />
        </instancedMesh>
    )
}

interface CosmicIntroProps {
    onComplete: () => void
}

export default function CosmicIntro({ onComplete }: CosmicIntroProps) {
    const [finished, setFinished] = useState(false)

    // Auto-complete after 3.5 seconds
    useEffect(() => {
        const timer = setTimeout(() => {
            setFinished(true)
            setTimeout(onComplete, 1000) // Wait for exit animation
        }, 3500)
        return () => clearTimeout(timer)
    }, [onComplete])

    return (
        <AnimatePresence>
            {!finished && (
                <motion.div
                    className="fixed inset-0 z-[100] bg-black"
                    initial={{ opacity: 1 }}
                    exit={{ opacity: 0, scale: 1.5, filter: 'blur(20px)' }} // "Hyperspace exit" blur
                    transition={{ duration: 1.0, ease: "easeInOut" }}
                >
                    <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
                        <motion.h1
                            initial={{ opacity: 0, scale: 0.5, letterSpacing: '0em' }}
                            animate={{ opacity: 1, scale: 1, letterSpacing: '0.5em' }}
                            exit={{ opacity: 0, scale: 2 }}
                            transition={{ duration: 2 }}
                            className="text-6xl md:text-8xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 uppercase tracking-widest"
                            style={{ textShadow: '0 0 30px rgba(59, 130, 246, 0.5)' }}
                        >
                            System
                            <br />
                            Online
                        </motion.h1>
                    </div>

                    <Canvas camera={{ position: [0, 0, 50], fov: 75 }}>
                        <color attach="background" args={['#000000']} />
                        <fog attach="fog" args={['#000000', 30, 60]} />
                        <WarpStars />
                    </Canvas>
                </motion.div>
            )}
        </AnimatePresence>
    )
}
