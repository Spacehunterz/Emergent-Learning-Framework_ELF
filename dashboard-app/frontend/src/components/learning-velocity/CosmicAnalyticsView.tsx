import { useMemo, useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, Text, Float, Html, Sparkles } from '@react-three/drei'
import { useVelocityData } from './useVelocityData'
import * as THREE from 'three'

function Bar({ position, height, color, label, value }: any) {
    const [hovered, setHovered] = useState(false)

    // Animate height on load or update could go here, for now simpler is safer

    return (
        <group position={position}>
            {/* The Building */}
            <mesh
                position={[0, height / 2, 0]}
                onPointerOver={(e) => { e.stopPropagation(); setHovered(true) }}
                onPointerOut={(e) => { e.stopPropagation(); setHovered(false) }}
            >
                <boxGeometry args={[0.8, height, 0.8]} />
                <meshStandardMaterial
                    color={color}
                    emissive={hovered ? color : '#000'}
                    emissiveIntensity={hovered ? 0.8 : 0.2}
                    roughness={0.1}
                    metalness={0.9}
                    transparent
                    opacity={0.9}
                />
            </mesh>

            {/* Roof Light */}
            <mesh position={[0, height + 0.05, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                <planeGeometry args={[0.7, 0.7]} />
                <meshBasicMaterial color={color} side={THREE.DoubleSide} />
            </mesh>

            {/* Base Label */}
            <Text
                position={[0, 0.1, 1]}
                fontSize={0.25}
                color="#94a3b8"
                anchorX="center"
                anchorY="bottom"
                rotation={[-Math.PI / 6, 0, 0]}
            >
                {label}
            </Text>

            {/* Holographic Tooltip */}
            {hovered && (
                <Html position={[0, height + 1.5, 0]} center transform style={{ pointerEvents: 'none' }}>
                    <div className="glass-panel px-3 py-2 rounded-lg border border-white/20 text-center min-w-[100px] shadow-neon">
                        <div className="text-2xl font-bold text-white font-mono leading-none">{value}</div>
                        <div className="text-[10px] text-cosmic-cyan uppercase tracking-widest mt-1">Velocity</div>
                    </div>
                </Html>
            )}
        </group>
    )
}

function AnalyticsScene({ data }: { data: any }) {
    // Transform data into 3D bars
    const bars = useMemo(() => {
        if (!data || !data.heuristics_by_week) return []
        return data.heuristics_by_week.map((week: any, idx: number) => ({
            index: idx,
            label: `W${week.week}`,
            value: week.heuristics_count,
            height: Math.max(1, week.heuristics_count * 0.5), // Scale height
            // Cyberpunk city palette
            color: idx % 3 === 0 ? '#00f3ff' : idx % 3 === 1 ? '#bc13fe' : '#f59e0b',
            position: [
                (idx - (data.heuristics_by_week.length - 1) / 2) * 1.5, // Center X
                0,
                0
            ]
        }))
    }, [data])

    return (
        <group>
            {/* Environment */}
            <color attach="background" args={[new THREE.Color('#030712')]} />
            <fog attach="fog" color={0x030712} near={10} far={50} />

            <Sparkles count={200} scale={30} size={4} speed={0.4} opacity={0.5} color="#ffffff" />

            <ambientLight intensity={0.5} />
            <pointLight position={[10, 20, 10]} intensity={1.5} color="#4c1d95" />
            <pointLight position={[-10, 20, -10]} intensity={1.5} color="#0e7490" />
            <spotLight position={[0, 30, 0]} angle={0.5} penumbra={1} intensity={1} castShadow />

            <Float speed={1} rotationIntensity={0.02} floatIntensity={0.1}>
                <group position={[0, -8, 0]}>
                    {bars.map((bar: any, i: number) => (
                        <Bar key={i} {...bar} />
                    ))}

                    {/* Grid Floor */}
                    <gridHelper args={[50, 50, '#1e293b', '#0f172a']} position={[0, 0, 0]} />

                    {/* Reflective Floor */}
                    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]}>
                        <planeGeometry args={[100, 100]} />
                        <meshStandardMaterial
                            color="#000000"
                            roughness={0.1}
                            metalness={0.8}
                            transparent
                            opacity={0.8}
                        />
                    </mesh>
                </group>
            </Float>

            <OrbitControls
                enableZoom={true}
                autoRotate
                autoRotateSpeed={0.5}
                maxPolarAngle={Math.PI / 2 - 0.1}
                minDistance={5}
                maxDistance={40}
            />
        </group>
    )
}

export default function CosmicAnalyticsView() {
    const { data, loading } = useVelocityData(30) // Default 30 days

    if (loading || !data) return (
        <div className="w-full h-full flex items-center justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-cosmic-cyan"></div>
        </div>
    )

    return (
        <div className="w-full h-full relative bg-cosmic-bg overflow-hidden">
            {/* Header Overlay */}
            <div className="absolute top-8 left-8 z-10 pointer-events-none">
                <h3 className="text-4xl font-display font-bold text-transparent bg-clip-text bg-gradient-to-r from-cosmic-cyan to-purple-500 drop-shadow-lg filter shadow-neon">
                    VELOCITY CITY
                </h3>
                <div className="flex items-center gap-2 mt-2">
                    <span className="w-2 h-2 rounded-full bg-cosmic-cyan animate-pulse" />
                    <p className="text-slate-400 text-sm font-mono tracking-widest uppercase">
                        Heuristic Growth Metrics // 30 Day Window
                    </p>
                </div>
            </div>

            <Canvas camera={{ position: [0, 6, 15], fov: 45 }} className="w-full h-full" resize={{ scroll: false, debounce: 0 }}>
                <AnalyticsScene data={data} />
            </Canvas>
        </div>
    )
}
