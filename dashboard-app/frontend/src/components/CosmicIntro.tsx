import { useRef, useState, useEffect } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { motion, AnimatePresence } from 'framer-motion'
import { useCosmicAudio } from '../context/CosmicAudioContext'

function WarpStars({ speedMultiplier = 1 }: { speedMultiplier?: number }) {
    const count = 3000
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

    // Non-uniform scales for variety
    const [scales] = useState(() => {
        const s = new Float32Array(count)
        for (let i = 0; i < count; i++) s[i] = Math.random()
        return s
    })

    useFrame((state) => {
        if (!mesh.current) return

        // Accelerate over time + base multiplier
        const time = state.clock.elapsedTime
        const speed = (2 + time * 8) * speedMultiplier

        for (let i = 0; i < count; i++) {
            let x = positions[i * 3]
            let y = positions[i * 3 + 1]
            let z = positions[i * 3 + 2]

            z += speed
            if (z > 50) z -= 100 // Reset to back

            positions[i * 3 + 2] = z

            dummy.position.set(x, y, z)

            // Stretch stars based on speed for warp effect
            const scale = scales[i]
            dummy.scale.set(scale, scale, scale * (1 + speed * 1.5))
            dummy.updateMatrix()

            mesh.current.setMatrixAt(i, dummy.matrix)
        }
        mesh.current.instanceMatrix.needsUpdate = true
    })

    return (
        <instancedMesh ref={mesh} args={[undefined, undefined, count]}>
            <sphereGeometry args={[0.08, 8, 8]} />
            <meshBasicMaterial color="#ffffff" transparent opacity={0.9} />
        </instancedMesh>
    )
}

interface CosmicIntroProps {
    onComplete: () => void
    mode?: 'full' | 'short'
}

export default function CosmicIntro({ onComplete, mode = 'full' }: CosmicIntroProps) {
    const [finished, setFinished] = useState(false)
    const { playToggle, playTransition } = useCosmicAudio()

    // Configuration based on mode
    const config = mode === 'full' ? {
        duration: 3500,
        text: 'System Online',
        startDelay: 0,
        audioConfirmDelay: 500,
        exitDelay: 800
    } : {
        duration: 1000,
        text: 'Warp Engaged',
        startDelay: 0,
        audioConfirmDelay: 50,
        exitDelay: 200
    }

    useEffect(() => {
        // Start Sound
        setTimeout(() => playToggle(true), config.audioConfirmDelay)

        const timer = setTimeout(() => {
            // Exit Sequence
            playTransition()
            setFinished(true)
            setTimeout(onComplete, config.exitDelay)
        }, config.duration)

        return () => clearTimeout(timer)
    }, [onComplete, mode, playToggle, playTransition])

    return (
        <AnimatePresence>
            {!finished && (
                <motion.div
                    className="fixed inset-0 z-[100] bg-black overflow-hidden"
                    initial={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.5, ease: "easeIn" }}
                >
                    {/* White Flash Overlay on Exit */}
                    <motion.div
                        className="absolute inset-0 bg-white pointer-events-none z-50"
                        initial={{ opacity: 0 }}
                        exit={{ opacity: [0, 1, 0], transition: { duration: 0.4, times: [0, 0.1, 1] } }}
                    />

                    {/* Centered Text */}
                    <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
                        <motion.div
                            initial={{ opacity: 0, scale: 0.8 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 3, filter: 'blur(10px)' }}
                            transition={{ duration: config.duration / 1500 }}
                            className="text-center"
                        >
                            <h1
                                className="text-6xl md:text-8xl font-black uppercase tracking-widest text-transparent bg-clip-text bg-gradient-to-r from-white via-cyan-200 to-white"
                                style={{
                                    textShadow: '0 0 40px rgba(6, 182, 212, 0.8)',
                                    fontFamily: '"Orbitron", "Inter", sans-serif' // Fallback to Inter
                                }}
                            >
                                {mode === 'full' ? (
                                    <>
                                        System<br />
                                        <span className="text-cyan-400">Online</span>
                                    </>
                                ) : (
                                    <span className="text-4xl md:text-6xl italic text-cyan-400">
                                        WARP<span className="text-white">SPEED</span>
                                    </span>
                                )}
                            </h1>
                            {mode === 'full' && (
                                <motion.div
                                    initial={{ width: 0 }}
                                    animate={{ width: '100%' }}
                                    transition={{ duration: 2, ease: "circOut" }}
                                    className="h-1 bg-cyan-500 mt-4 mx-auto rounded-full shadow-[0_0_20px_rgba(6,182,212,1)]"
                                    style={{ maxWidth: '300px' }}
                                />
                            )}
                        </motion.div>
                    </div>

                    {/* 3D Background */}
                    <Canvas camera={{ position: [0, 0, 50], fov: 75 }}>
                        <color attach="background" args={['#050510'] as any} />
                        <fog attach="fog" args={['#050510', 20, 90] as any} />
                        <WarpStars speedMultiplier={mode === 'short' ? 3 : 1} />
                    </Canvas>
                </motion.div>
            )}
        </AnimatePresence>
    )
}
