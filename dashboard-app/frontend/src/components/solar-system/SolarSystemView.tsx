import { useRef, useMemo, useState, useEffect } from 'react'
import { Canvas, useFrame, useThree, extend, ReactThreeFiber } from '@react-three/fiber'
import { OrbitControls, Stars, Text, Float, Billboard, Html, shaderMaterial } from '@react-three/drei'
import { XR, useXR } from '@react-three/xr'
import { useDataContext } from '../../context/DataContext'
import * as THREE from 'three'
import { sunVertexShader, sunFragmentShader, planetVertexShader, planetFragmentShader } from './shaders'
import { Floating3DParticles } from './Floating3DParticles'
import { xrStore } from '../xr/xrStore'

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
            planetAtmosphereMaterial: ReactThreeFiber.Object3DNode<THREE.ShaderMaterial, typeof PlanetAtmosphereMaterial> & { baseColor?: THREE.Color }
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
    const isPresenting = useXR((state) => state.mode === 'immersive-vr')

    // Store refs for animation
    const savedView = useRef<{ position: THREE.Vector3, target: THREE.Vector3 } | null>(null)
    const isRestoring = useRef(false)

    // Handle selection state changes
    useEffect(() => {
        if (isSelected) {
            // About to zoom in: SAVE current state
            if (controlsRef.current) {
                savedView.current = {
                    position: camera.position.clone(),
                    target: controlsRef.current.target.clone()
                }
            }
            isRestoring.current = false
        } else {
            // Just zoomed out: START restoring
            if (savedView.current) {
                isRestoring.current = true
            }
        }
    }, [isSelected, camera])

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
        if (isPresenting) return
        if (!controlsRef.current) return

        // If user is manually interacting, cancel any restoration
        if (controlsRef.current.enableZoom) { // active "free look" mode
            // We could check if user is actively dragging here, but OrbitControls doesn't expose 'isDragging' easily without events.
            // For now, let the lerp fight smoothly or just override.
        }

        const lerpFactor = 0.05 // Slightly faster for responsiveness

        if (isSelected && target) {
            // TARGETED MODE (Drill-down)
            const zoomDistance = planetSize * 6 + 4
            const targetPos = new THREE.Vector3(
                target.x + zoomDistance * 0.5,
                target.y + zoomDistance * 0.3,
                target.z + zoomDistance * 0.7
            )

            camera.position.lerp(targetPos, lerpFactor)
            controlsRef.current.target.lerp(target, lerpFactor)

        } else if (isRestoring.current && savedView.current) {
            // RESTORING MODE (Returning to previous view)
            const destPos = savedView.current.position
            const destTarget = savedView.current.target

            camera.position.lerp(destPos, lerpFactor)
            controlsRef.current.target.lerp(destTarget, lerpFactor)

            // Check if we're close enough to stop forcing the restoration
            if (camera.position.distanceTo(destPos) < 0.5 && controlsRef.current.target.distanceTo(destTarget) < 0.5) {
                isRestoring.current = false
            }

        } else {
            // FREE ROAM / DEFAULT IDLE
            // If we have no saved view (initial load), gently drift to default
            if (!savedView.current) {
                controlsRef.current.target.lerp(defaultTarget, lerpFactor * 0.1)
                if (camera.position.length() < 10) {
                    camera.position.lerp(defaultPosition, lerpFactor * 0.1)
                }
            }
            // Otherwise, do nothing and let the user orbit freely
        }

        controlsRef.current.update()
    })

    if (isPresenting) return null

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
            mouseButtons={{
                LEFT: undefined as any, // Disable Left Click Rotation to allow Weapon Fire
                MIDDLE: THREE.MOUSE.DOLLY,
                RIGHT: THREE.MOUSE.ROTATE
            }}
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
    const [viewMode, setViewMode] = useState<'summary' | 'details'>('summary')
    const isPresenting = useXR((state) => state.mode === 'immersive-vr')

    // Reset view mode when selection changes
    useEffect(() => {
        if (!selected) setViewMode('summary')
    }, [selected])

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
                onPointerOver={() => { if (!isPresenting) document.body.style.cursor = 'pointer'; setHovered(true) }}
                onPointerOut={() => { if (!isPresenting) document.body.style.cursor = 'auto'; setHovered(false) }}
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
                onPointerOver={() => { if (!isPresenting) document.body.style.cursor = 'pointer'; setHovered(true) }}
                onPointerOut={() => { if (!isPresenting) document.body.style.cursor = 'auto'; setHovered(false) }}
            >
                <sphereGeometry args={[size * 1.8, 16, 16]} />
                <meshBasicMaterial />
            </mesh>

            {/* Atmosphere Glow */}
            <mesh scale={[1.2, 1.2, 1.2]}>
                <sphereGeometry args={[size, 32, 32]} />
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
            {hovered && !selected && !isPresenting && (
                <Html position={[0, size + 2, 0]} center style={{ pointerEvents: 'none' }}>
                    <div className="w-48 p-3 rounded-lg bg-black/80 glass-panel shadow-neon backdrop-blur-md" style={{ borderColor: 'var(--theme-accent)' }}>
                        <div className="relative z-10 text-center">
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

            {/* Expanded info panel when selected - SHARP TEXT MODE (No 3D Transform) */}
            {selected && !isPresenting && (
                <Html position={[0, 0, 0]} center zIndexRange={[100, 0]} style={{ pointerEvents: 'auto' }}>
                    <div className="relative flex flex-col items-center justify-center">
                        {/* Connecting Line (visual only) */}
                        <div className="absolute top-0 w-px h-16 bg-gradient-to-t from-transparent via-white/50 to-transparent -translate-y-full" style={{ left: '50%' }} />

                        <div className={`w-80 p-4 rounded-xl glass-panel shadow-2xl border border-white/20 transition-all duration-300 ${viewMode === 'details' ? 'h-96' : 'h-auto'}`} style={{ borderColor: color, backgroundColor: 'rgba(10, 10, 20, 0.9)' }}>
                            <div className="relative z-10 h-full flex flex-col">
                                {/* Header */}
                                <div className="flex items-center justify-between mb-4 pb-3 border-b border-white/10 shrink-0">
                                    <div className="flex items-center gap-2">
                                        <span className="w-3 h-3 rounded-full animate-pulse" style={{ backgroundColor: color }} />
                                        <span className="font-bold uppercase tracking-wider text-sm" style={{ color: color }}>
                                            {label}
                                        </span>
                                    </div>
                                    <div className="flex gap-2">
                                        {viewMode === 'details' && (
                                            <button
                                                onClick={(e) => { e.stopPropagation(); setViewMode('summary') }}
                                                className="text-[10px] font-mono px-2 py-1 bg-white/5 hover:bg-white/10 rounded transition-colors"
                                            >
                                                BACK
                                            </button>
                                        )}
                                        <span className="text-[10px] text-cosmic-cyan font-mono px-2 py-1 bg-cosmic-cyan/10 rounded border border-cosmic-cyan/20">
                                            DOMAIN
                                        </span>
                                    </div>
                                </div>

                                {viewMode === 'summary' ? (
                                    <>
                                        {/* Stats Grid */}
                                        <div className="grid grid-cols-2 gap-3 mb-4">
                                            <div className="bg-white/5 rounded-lg p-2 text-center border border-white/5 hover:border-white/10 transition-colors">
                                                <div className="text-2xl font-bold text-white font-mono">{details.count}</div>
                                                <div className="text-[10px] text-slate-400 uppercase tracking-wider">Heuristics</div>
                                            </div>
                                            <div className="bg-white/5 rounded-lg p-2 text-center border border-white/5 hover:border-white/10 transition-colors">
                                                <div className="text-2xl font-bold text-white font-mono">{details.goldenCount || 0}</div>
                                                <div className="text-[10px] text-amber-400 uppercase tracking-wider">Golden Rules</div>
                                            </div>
                                        </div>

                                        {/* Confidence Stat */}
                                        <div className="mb-6 p-3 bg-white/5 rounded-lg border border-white/5">
                                            <div className="flex justify-between items-end mb-2">
                                                <span className="text-xs text-slate-400 uppercase tracking-wider">Avg Confidence</span>
                                                <span className="text-lg font-mono font-bold" style={{ color: color }}>
                                                    {((details.avgConfidence || 0) * 100).toFixed(0)}%
                                                </span>
                                            </div>
                                            <div className="w-full h-1.5 bg-black/50 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full rounded-full transition-all duration-1000 ease-out"
                                                    style={{ width: `${(details.avgConfidence || 0) * 100}%`, backgroundColor: color }}
                                                />
                                            </div>
                                        </div>

                                        {/* Action Button */}
                                        <button
                                            onClick={(e) => { e.stopPropagation(); setViewMode('details') }}
                                            className="w-full py-2.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/30 transition-all flex items-center justify-center gap-2 group"
                                        >
                                            <span className="text-xs font-bold tracking-wider uppercase text-white group-hover:text-cyan-300">View Insights</span>
                                            <span className="text-white/50 group-hover:translate-x-1 transition-transform">→</span>
                                        </button>
                                    </>
                                ) : (
                                    <div className="flex-1 overflow-hidden flex flex-col">
                                        <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-2 shrink-0">Top Heuristics</div>
                                        <div className="flex-1 overflow-y-auto pr-1 space-y-2 custom-scrollbar">
                                            {details.topHeuristics && details.topHeuristics.length > 0 ? (
                                                details.topHeuristics.map((h: any, i: number) => (
                                                    <div key={i} className="p-2.5 rounded bg-white/5 border border-white/5 hover:bg-white/10 hover:border-white/20 transition-all group">
                                                        <div className="text-xs text-slate-300 line-clamp-2 mb-2 group-hover:text-white transition-colors">
                                                            "{h.rule}"
                                                        </div>
                                                        <div className="flex justify-between items-center">
                                                            <div className="flex items-center gap-1.5">
                                                                {h.is_golden && <span className="text-[8px] px-1 bg-amber-500/20 text-amber-400 rounded border border-amber-500/30">GOLDEN</span>}
                                                            </div>
                                                            <div className="text-[10px] font-mono" style={{ color: h.confidence > 0.8 ? '#4ade80' : '#fbbf24' }}>
                                                                {(h.confidence * 100).toFixed(0)}%
                                                            </div>
                                                        </div>
                                                    </div>
                                                ))
                                            ) : (
                                                <div className="text-center py-8 text-slate-500 italic text-xs">No heuristics recorded yet</div>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </Html>
            )}

            {selected && isPresenting && (
                <group position={[0, size + 2.2, 0]}>
                    <mesh>
                        <planeGeometry args={[2.4, 1.4]} />
                        <meshStandardMaterial color="#0b1220" transparent opacity={0.85} />
                    </mesh>
                    <Text position={[0, 0.45, 0.02]} fontSize={0.16} color={color} anchorX="center" anchorY="middle">
                        {label}
                    </Text>
                    <Text position={[-1.05, 0.1, 0.02]} fontSize={0.1} color="#94a3b8" anchorX="left" anchorY="middle">
                        Heuristics:
                    </Text>
                    <Text position={[1.05, 0.1, 0.02]} fontSize={0.12} color="#ffffff" anchorX="right" anchorY="middle">
                        {details.count}
                    </Text>
                    <Text position={[-1.05, -0.18, 0.02]} fontSize={0.1} color="#f59e0b" anchorX="left" anchorY="middle">
                        Golden:
                    </Text>
                    <Text position={[1.05, -0.18, 0.02]} fontSize={0.12} color="#f59e0b" anchorX="right" anchorY="middle">
                        {details.goldenCount || 0}
                    </Text>
                    <Text position={[-1.05, -0.46, 0.02]} fontSize={0.1} color="#22d3ee" anchorX="left" anchorY="middle">
                        Confidence:
                    </Text>
                    <Text position={[1.05, -0.46, 0.02]} fontSize={0.12} color="#22d3ee" anchorX="right" anchorY="middle">
                        {((details.avgConfidence || 0) * 100).toFixed(0)}%
                    </Text>
                </group>
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

function SolarSystemScene({ onDomainSelect, selectedDomainProp }: { onDomainSelect?: (domain: string) => void, selectedDomainProp?: string | null }) {
    const { stats, heuristics } = useDataContext()
    const [selectedDomain, setSelectedDomain] = useState<string | null>(null)
    const [selectedPlanetPosition, setSelectedPlanetPosition] = useState<THREE.Vector3 | null>(null)
    const [selectedPlanetSize, setSelectedPlanetSize] = useState(1)

    // Sync with global prop
    useEffect(() => {
        if (selectedDomainProp !== undefined) {
            setSelectedDomain(selectedDomainProp)
            // If cleared externally, clear position too
            if (selectedDomainProp === null) {
                setSelectedPlanetPosition(null)
            }
        }
    }, [selectedDomainProp])

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
            size: Math.log(data.count + 1) * 0.3 + 0.8,
            // Get top 5 heuristics by confidence
            topHeuristics: heuristics
                .filter(h => h.domain === name)
                .sort((a, b) => (b.confidence || 0) - (a.confidence || 0))
                .slice(0, 5)
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
                        avgConfidence: domain.avgConfidence,
                        topHeuristics: domain.topHeuristics
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

export default function SolarSystemView({ onDomainSelect, selectedDomain }: { onDomainSelect?: (domain: string) => void, selectedDomain?: string | null }) {
    const [vrSupported, setVrSupported] = useState(false)

    useEffect(() => {
        let active = true
        const checkSupport = async () => {
            if (!navigator.xr || !navigator.xr.isSessionSupported) {
                if (active) setVrSupported(false)
                return
            }
            try {
                const supported = await navigator.xr.isSessionSupported('immersive-vr')
                if (active) setVrSupported(supported)
            } catch (e) {
                if (active) setVrSupported(false)
            }
        }
        checkSupport()
        return () => {
            active = false
        }
    }, [])

    return (
        <div className="w-full h-full min-h-[600px] relative">
            {/* Overlay Title - pointer-events-none ensures we can click through to canvas */}
            {/* MOVED DOWN to avoid header overlap */}
            {/* Overlay Title Removed */}

            {/* Controls hint */}
            <div className="absolute bottom-6 left-6 z-10 pointer-events-none select-none">
                <div className="flex items-center gap-4 text-[10px] text-slate-500 font-mono">
                    <span className="flex items-center gap-1">
                        <kbd className="px-1.5 py-0.5 bg-slate-800/80 rounded border border-slate-700 text-slate-400">Right Drag</kbd>
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

            {vrSupported && (
                <div className="absolute bottom-6 right-6 z-20">
                    <button
                        onClick={() => xrStore.enterVR()}
                        className="px-4 py-2 bg-slate-900/90 border border-cyan-500/40 text-cyan-200 font-mono text-xs tracking-[0.2em] uppercase rounded-lg hover:bg-slate-800/90 transition-colors"
                    >
                        Enter VR
                    </button>
                </div>
            )}

            <Canvas camera={{ position: [0, 30, 40], fov: 45 }} className="w-full h-full" gl={{ alpha: true }}>
                <XR store={xrStore}>
                    <SolarSystemScene onDomainSelect={onDomainSelect} selectedDomainProp={selectedDomain} />
                    <Floating3DParticles count={300} />
                </XR>
            </Canvas>
        </div>
    )
}
