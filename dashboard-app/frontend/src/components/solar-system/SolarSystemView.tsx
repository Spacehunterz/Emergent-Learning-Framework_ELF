import { useRef, useMemo, useState, useEffect } from 'react'
import { Canvas, useFrame, useThree, extend, ReactThreeFiber } from '@react-three/fiber'
import { OrbitControls, Stars, Text, Float, Billboard, Html, shaderMaterial } from '@react-three/drei'
import { useDataContext } from '../../context/DataContext'
import * as THREE from 'three'
import { sunVertexShader, sunFragmentShader, planetVertexShader, planetFragmentShader } from './shaders'

// Create custom shader materials
const SunMaterial = shaderMaterial(
    { time: 0, color: new THREE.Color(1, 0.6, 0.0) },
    sunVertexShader,
    sunFragmentShader
)

const PlanetAtmosphereMaterial = shaderMaterial(
    { baseColor: new THREE.Color(0, 0.5, 1), time: 0, atmosphereDensity: 0.3 },
    planetVertexShader,
    planetFragmentShader
)

// Extend R3F with custom materials
extend({ SunMaterial, PlanetAtmosphereMaterial })

// Add types to JSX
declare global {
    namespace JSX {
        interface IntrinsicElements {
            sunMaterial: ReactThreeFiber.Object3DNode<THREE.ShaderMaterial, typeof SunMaterial>
            planetAtmosphereMaterial: ReactThreeFiber.Object3DNode<THREE.ShaderMaterial, typeof PlanetAtmosphereMaterial>
        }
    }
}

interface PlanetProps {
    position: [number, number, number]
    color: string
    label: string
    size: number
    speed: number
    orbitRadius: number
    onClick: (label: string) => void
}

// Camera controller for smooth zoom transitions
interface CameraControllerProps {
    target: THREE.Vector3 | null
    defaultPosition: THREE.Vector3
    defaultTarget: THREE.Vector3
    isSelected: boolean
    planetSize: number
}

function CameraController({ target, defaultPosition, defaultTarget, isSelected, planetSize, onEscape }: CameraControllerProps & { onEscape: () => void }) {
    const { camera } = useThree()
    const controlsRef = useRef<any>(null)

    // Store refs for animation
    const currentTarget = useRef(new THREE.Vector3())
    const currentPosition = useRef(new THREE.Vector3())

    useEffect(() => {
        currentPosition.current.copy(camera.position)
        currentTarget.current.copy(defaultTarget)
    }, [camera, defaultTarget])

    // ESC key handler
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && isSelected) {
                onEscape()
            }
        }
        window.addEventListener('keydown', handleKeyDown)
        return () => window.removeEventListener('keydown', handleKeyDown)
    }, [isSelected, onEscape])

    useFrame(() => {
        if (!controlsRef.current) return

        // If user is manually interacting (rotating/zooming), don't force camera position unless we are in a transition
        if (controlsRef.current.enableZoom) { // active "free look" mode
            // Optional: Add some gentle drift or constraint if needed, but legal user control is priority
        }

        const lerpFactor = 0.03

        if (isSelected && target) {
            // TARGETED MODE
            const zoomDistance = planetSize * 6 + 4
            const targetPos = new THREE.Vector3(
                target.x + zoomDistance * 0.5,
                target.y + zoomDistance * 0.3,
                target.z + zoomDistance * 0.7
            )

            // Look at the planet
            camera.position.lerp(targetPos, lerpFactor)
            controlsRef.current.target.lerp(target, lerpFactor)
        } else if (!isSelected) {
            // OVERVIEW MODE - Only gently pull back if we are way off, otherwise let user explore
            // Actually, for "Overview", users expect to be able to rotate freely.
            // Let's only enforce position if we just came back from a selection (transition logic could be more complex, 
            // but for now, let's just default to a nice view if we are "resetting").

            // To recover "lost" users, we can have a "Reset View" button, but for now, 
            // let's just make the "default" lerp very weak or conditional.

            // FIX: Don't fight the user. Only set target to center (sun).
            controlsRef.current.target.lerp(defaultTarget, lerpFactor)

            // Allow manual rotation to persist, only nudge position if needed
            // Ensure camera is not stuck inside the sun
            if (camera.position.length() < 10) {
                camera.position.lerp(defaultPosition, lerpFactor)
            }
        }

        controlsRef.current.update()
    })

    return (
        <OrbitControls
            ref={controlsRef}
            enablePan={true}
            enableZoom={true}
            enableRotate={true}
            minDistance={10}
            maxDistance={200}
            rotateSpeed={0.5}
            zoomSpeed={0.5}
            // Temporarily disable damping to see if it helps with "fighting"
            enableDamping={true}
            dampingFactor={0.05}
        />
    )
}

function Sun({ score }: { score: number }) {
    const meshRef = useRef<THREE.Mesh>(null)
    const materialRef = useRef<THREE.ShaderMaterial>(null)

    useFrame((state) => {
        if (materialRef.current) {
            materialRef.current.uniforms.time.value = state.clock.elapsedTime
        }
        if (meshRef.current) {
            meshRef.current.rotation.y += 0.0005 // Slower sun rotation
        }
    })

    // Color changes based on score (health)
    const color = score > 0.8 ? '#fbbf24' : score > 0.5 ? '#f97316' : '#ef4444'

    return (
        <group>
            <Float speed={1} rotationIntensity={0.2} floatIntensity={0.2}>
                <mesh ref={meshRef}>
                    <sphereGeometry args={[2.5, 64, 64]} />
                    {/* @ts-ignore */}
                    <sunMaterial ref={materialRef} color={new THREE.Color(color)} transparent />
                    <pointLight intensity={3} distance={50} color={color} decay={2} />
                </mesh>
            </Float>
            <Billboard position={[0, 3.5, 0]}>
                <Text
                    fontSize={0.5}
                    color="white"
                    anchorX="center"
                    anchorY="middle"
                    outlineWidth={0.02}
                    outlineColor="#000000"
                >
                    System Core
                </Text>
            </Billboard>
        </group>
    )
}

function Planet({ label, color, size, speed, orbitRadius, onClick, selected, paused, details, onPositionUpdate }: PlanetProps & { selected: boolean, paused: boolean, details: any, onPositionUpdate?: (pos: THREE.Vector3) => void }) {
    const meshRef = useRef<THREE.Mesh>(null)
    const orbitGroupRef = useRef<THREE.Group>(null)
    const angleRef = useRef(Math.random() * Math.PI * 2)
    const atmosphereRef = useRef<THREE.ShaderMaterial>(null)
    const [hovered, setHovered] = useState(false)

    useFrame((state, delta) => {
        // Orbit Logic - pause when selected or globally paused
        if (!paused) {
            angleRef.current += speed * delta
        }

        if (orbitGroupRef.current) {
            const x = Math.cos(angleRef.current) * orbitRadius
            const z = Math.sin(angleRef.current) * orbitRadius
            orbitGroupRef.current.position.set(x, 0, z)

            // Report position when selected (for camera targeting)
            if (selected && onPositionUpdate) {
                onPositionUpdate(new THREE.Vector3(x, 0, z))
            }
        }

        // Spin Logic - slow spin when selected for visual interest
        if (meshRef.current) {
            const spinSpeed = selected ? delta * 0.2 : (hovered ? 0 : delta)
            meshRef.current.rotation.y += spinSpeed
        }

        // Atmosphere animation
        if (atmosphereRef.current) {
            atmosphereRef.current.uniforms.time.value = state.clock.elapsedTime
        }
    })

    return (
        <group ref={orbitGroupRef}>
            {/* Actual Planet Surface */}
            <mesh
                ref={meshRef}
                onClick={(e) => {
                    e.stopPropagation()
                    onClick(label)
                }}
                onPointerOver={() => { document.body.style.cursor = 'pointer'; setHovered(true) }}
                onPointerOut={() => { document.body.style.cursor = 'auto'; setHovered(false) }}
            >
                <sphereGeometry args={[size, 32, 32]} />
                <meshStandardMaterial
                    color={color}
                    roughness={0.7}
                    metalness={0.2}
                    emissive={hovered || selected ? color : '#000000'}
                    emissiveIntensity={selected ? 0.5 : hovered ? 0.2 : 0}
                />
            </mesh>

            {/* Invisible Hit Target (Larger) */}
            <mesh
                visible={false}
                onClick={(e) => {
                    e.stopPropagation()
                    onClick(label)
                }}
                onPointerOver={() => { document.body.style.cursor = 'pointer'; setHovered(true) }}
                onPointerOut={() => { document.body.style.cursor = 'auto'; setHovered(false) }}
            >
                <sphereGeometry args={[size * 1.8, 16, 16]} />
                <meshBasicMaterial />
            </mesh>

            {/* Atmosphere Glow */}
            <mesh scale={[1.2, 1.2, 1.2]}>
                <sphereGeometry args={[size, 32, 32]} />
                {/* @ts-ignore */}
                {/* @ts-ignore */}
                <planetAtmosphereMaterial
                    ref={atmosphereRef}
                    baseColor={new THREE.Color(color)}
                    transparent
                    blending={THREE.AdditiveBlending}
                    depthWrite={false}
                    side={THREE.BackSide}
                />
            </mesh>

            {/* Planet Label */}
            <Billboard position={[0, size + 1.2, 0]}>
                <Text
                    fontSize={0.4}
                    color={color}
                    anchorX="center"
                    anchorY="middle"
                    outlineWidth={0.02}
                    outlineColor="#000000"
                >
                    {label}
                </Text>
            </Billboard>

            {/* Info Popup - Using HTML to overlay UI elements on 3D objects */}
            {hovered && !selected && (
                <Html position={[0, size + 2, 0]} center transform style={{ pointerEvents: 'none' }}>
                    <div className="w-48 p-3 rounded-lg transform transition-all duration-300 scale-100 opacity-100 glass-panel shadow-neon" style={{ borderColor: 'var(--theme-accent)' }}>
                        <div className="absolute inset-0 bg-gradient-to-b from-transparent to-black/20 rounded-lg pointer-events-none" />
                        <div className="relative z-10">
                            <div className="font-bold mb-1 uppercase tracking-wider text-xs" style={{ color: color }}>
                                {label}
                            </div>
                            <div className="space-y-1 text-[10px]">
                                <div className="flex justify-between text-slate-400">
                                    <span>Heuristics</span>
                                    <span className="text-white font-mono">{details.count}</span>
                                </div>
                            </div>
                            <div className="mt-2 text-[10px] text-cosmic-cyan/70 font-mono text-center">
                                Click to focus
                            </div>
                        </div>
                    </div>
                </Html>
            )}

            {/* Expanded info panel when selected */}
            {selected && (
                <Html position={[size + 2, 0, 0]} center transform style={{ pointerEvents: 'auto' }}>
                    <div className="w-72 p-4 rounded-xl glass-panel shadow-neon border border-white/20 transform transition-all duration-500 scale-100 opacity-100" style={{ borderColor: color }}>
                        <div className="absolute inset-0 bg-gradient-to-br from-black/60 to-black/80 rounded-xl pointer-events-none" />
                        <div className="relative z-10">
                            {/* Header */}
                            <div className="flex items-center justify-between mb-4 pb-3 border-b border-white/10">
                                <div className="flex items-center gap-2">
                                    <span className="w-3 h-3 rounded-full animate-pulse" style={{ backgroundColor: color }} />
                                    <span className="font-bold uppercase tracking-wider text-sm" style={{ color: color }}>
                                        {label}
                                    </span>
                                </div>
                                <span className="text-[10px] text-cosmic-cyan font-mono px-2 py-1 bg-cosmic-cyan/10 rounded">
                                    DOMAIN
                                </span>
                            </div>

                            {/* Stats Grid */}
                            <div className="grid grid-cols-2 gap-3 mb-4">
                                <div className="bg-white/5 rounded-lg p-2 text-center">
                                    <div className="text-2xl font-bold text-white font-mono">{details.count}</div>
                                    <div className="text-[10px] text-slate-400 uppercase tracking-wider">Heuristics</div>
                                </div>
                                <div className="bg-white/5 rounded-lg p-2 text-center">
                                    <div className="text-2xl font-bold text-white font-mono">{details.goldenCount || 0}</div>
                                    <div className="text-[10px] text-amber-400 uppercase tracking-wider">Golden Rules</div>
                                </div>
                            </div>

                            {/* Details */}
                            <div className="space-y-2 text-xs">
                                <div className="flex justify-between text-slate-400">
                                    <span>Orbit Radius</span>
                                    <span className="text-white font-mono">{orbitRadius.toFixed(1)} AU</span>
                                </div>
                                <div className="flex justify-between text-slate-400">
                                    <span>Avg Confidence</span>
                                    <span className="text-white font-mono">{((details.avgConfidence || 0.7) * 100).toFixed(0)}%</span>
                                </div>
                            </div>

                            {/* Action hint */}
                            <div className="mt-4 pt-3 border-t border-white/10 text-center">
                                <span className="text-[10px] text-slate-500 font-mono">
                                    Click elsewhere to return
                                </span>
                            </div>
                        </div>
                    </div>
                </Html>
            )}
        </group>
    )
}

// Background plane to catch clicks for deselection
function BackgroundClickCatcher({ onClick }: { onClick: () => void }) {
    return (
        <mesh position={[0, 0, -100]} onClick={onClick}>
            <planeGeometry args={[500, 500]} />
            <meshBasicMaterial transparent opacity={0} />
        </mesh>
    )
}

function SolarSystemScene({ onDomainSelect }: { onDomainSelect?: (domain: string) => void }) {
    const { stats, heuristics } = useDataContext()
    const [selectedDomain, setSelectedDomain] = useState<string | null>(null)
    const [selectedPlanetPosition, setSelectedPlanetPosition] = useState<THREE.Vector3 | null>(null)
    const [selectedPlanetSize, setSelectedPlanetSize] = useState(1)

    // Default camera settings
    const defaultCameraPosition = useMemo(() => new THREE.Vector3(0, 30, 40), [])
    const defaultCameraTarget = useMemo(() => new THREE.Vector3(0, 0, 0), [])

    // Extract domains from heuristics with additional stats
    const domains = useMemo(() => {
        const d: Record<string, { count: number, goldenCount: number, totalConfidence: number }> = {}
        heuristics.forEach(h => {
            if (!d[h.domain]) {
                d[h.domain] = { count: 0, goldenCount: 0, totalConfidence: 0 }
            }
            d[h.domain].count++
            if (h.is_golden) d[h.domain].goldenCount++
            d[h.domain].totalConfidence += h.confidence || 0.5
        })
        return Object.entries(d).map(([name, data], idx) => ({
            name,
            count: data.count,
            goldenCount: data.goldenCount,
            avgConfidence: data.count > 0 ? data.totalConfidence / data.count : 0.5,
            orbitRadius: 8 + idx * 3.5,
            speed: 0.02 + Math.random() * 0.03,
            color: `hsl(${idx * 45 + 200}, 80%, 60%)`,
            size: Math.log(data.count + 1) * 0.3 + 0.8
        }))
    }, [heuristics])

    const successRate = stats && stats.total_runs > 0 ? stats.successful_runs / stats.total_runs : 1.0

    const handlePlanetClick = (label: string) => {
        const domain = domains.find(d => d.name === label)
        if (domain) {
            setSelectedDomain(label)
            setSelectedPlanetSize(domain.size)
            if (onDomainSelect) onDomainSelect(label)
        }
    }

    const handleDeselect = () => {
        setSelectedDomain(null)
        setSelectedPlanetPosition(null)
    }

    const handlePositionUpdate = (pos: THREE.Vector3) => {
        setSelectedPlanetPosition(pos)
    }

    return (
        <>
            <ambientLight intensity={0.1} />
            <pointLight position={[0, 0, 0]} intensity={2} color="#ffaa00" distance={100} />

            {/* Click catcher for deselection - only active when something is selected */}
            {selectedDomain && <BackgroundClickCatcher onClick={handleDeselect} />}

            <Sun score={successRate} />

            {domains.map((domain) => (
                <Planet
                    key={domain.name}
                    label={domain.name}
                    orbitRadius={domain.orbitRadius}
                    speed={domain.speed}
                    color={domain.color}
                    size={domain.size}
                    position={[0, 0, 0]}
                    onClick={handlePlanetClick}
                    selected={selectedDomain === domain.name}
                    paused={selectedDomain !== null}
                    details={{
                        count: domain.count,
                        goldenCount: domain.goldenCount,
                        avgConfidence: domain.avgConfidence
                    }}
                    onPositionUpdate={selectedDomain === domain.name ? handlePositionUpdate : undefined}
                />
            ))}

            <Stars radius={150} depth={50} count={7000} factor={4} saturation={1} fade speed={0.5} />

            <CameraController
                target={selectedPlanetPosition}
                defaultPosition={defaultCameraPosition}
                defaultTarget={defaultCameraTarget}
                isSelected={selectedDomain !== null}
                planetSize={selectedPlanetSize}
                onEscape={handleDeselect}
            />
        </>
    )
}

export default function SolarSystemView({ onDomainSelect }: { onDomainSelect?: (domain: string) => void }) {
    return (
        <div className="w-full h-full min-h-[600px] relative">
            {/* Overlay Title - pointer-events-none ensures we can click through to canvas */}
            {/* MOVED DOWN to avoid header overlap */}
            <div className="absolute top-24 left-6 z-10 pointer-events-none select-none">
                <h2 className="text-4xl font-display font-bold text-transparent bg-clip-text bg-gradient-to-r from-amber-200 to-yellow-500 drop-shadow-lg shadow-black">
                    SYSTEM OVERVIEW
                </h2>
                <div className="flex items-center gap-2 mt-1">
                    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                    <p className="text-cosmic-cyan/70 text-sm font-mono tracking-widest">INTERACTIVE 3D KNOWLEDGE MAP</p>
                </div>
            </div>

            {/* Controls hint */}
            <div className="absolute bottom-6 left-6 z-10 pointer-events-none select-none">
                <div className="flex items-center gap-4 text-[10px] text-slate-500 font-mono">
                    <span className="flex items-center gap-1">
                        <kbd className="px-1.5 py-0.5 bg-slate-800/80 rounded border border-slate-700 text-slate-400">Drag</kbd>
                        <span>Look around</span>
                    </span>
                    <span className="flex items-center gap-1">
                        <kbd className="px-1.5 py-0.5 bg-slate-800/80 rounded border border-slate-700 text-slate-400">Scroll</kbd>
                        <span>Zoom</span>
                    </span>
                    <span className="flex items-center gap-1">
                        <kbd className="px-1.5 py-0.5 bg-slate-800/80 rounded border border-slate-700 text-slate-400">Click</kbd>
                        <span>Select</span>
                    </span>
                    <span className="flex items-center gap-1">
                        <kbd className="px-1.5 py-0.5 bg-slate-800/80 rounded border border-slate-700 text-slate-400">ESC</kbd>
                        <span>Deselect</span>
                    </span>
                </div>
            </div>

            <Canvas camera={{ position: [0, 30, 40], fov: 45 }} className="w-full h-full">
                <SolarSystemScene onDomainSelect={onDomainSelect} />
            </Canvas>
        </div>
    )
}
