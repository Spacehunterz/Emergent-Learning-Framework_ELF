import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Text, Billboard } from '@react-three/drei'
import { useGraphData } from './useGraphData'
import { GraphNode, GraphEdge, getColorForDomain } from './types'
import { forceSimulation, forceLink, forceManyBody, forceCenter } from 'd3-force'

function GraphScene({ data }: { data: { nodes: GraphNode[], edges: GraphEdge[] } }) {
    const groupRef = useRef<any>(null)

    // Run Force Simulation (one-time calculation for static 3D layout, or allow it to cool)
    useMemo(() => {
        // Initialize random Z for "cosmic depth" since d3-force is 2D
        data.nodes.forEach(node => {
            if (node.z === undefined || node.z === 0) {
                node.z = (Math.random() - 0.5) * 200 // Spread out in Z
            }
        })

        const sim = forceSimulation(data.nodes)
            .force("link", forceLink(data.edges).id((d: any) => d.id).distance(50))
            .force("charge", forceManyBody().strength(-300))
            .force("center", forceCenter(0, 0))
            .stop()

        // Pre-warm the simulation
        for (let j = 0; j < 300; ++j) sim.tick()
        return sim
    }, [data])

    // Auto-rotate the universe
    useFrame((_state, delta) => {
        if (groupRef.current) {
            groupRef.current.rotation.y += delta * 0.05
        }
    })

    return (
        <group ref={groupRef}>
            {/* Draw Lines */}
            <group>
                {data.edges.map((link, idx) => {
                    const source = link.source as unknown as GraphNode // D3 mutates this to be the object
                    const target = link.target as unknown as GraphNode

                    // Ensure safely typed coordinates for Float32Array
                    const sx = source.x ?? 0
                    const sy = source.y ?? 0
                    const sz = source.z ?? 0
                    const tx = target.x ?? 0
                    const ty = target.y ?? 0
                    const tz = target.z ?? 0

                    return (
                        // @ts-ignore
                        <line key={idx} frustumCulled={false}>
                            <bufferGeometry attach="geometry">
                                <float32BufferAttribute
                                    attach="attributes-position"
                                    count={2}
                                    array={new Float32Array([sx, sy, sz, tx, ty, tz])}
                                    itemSize={3}
                                />
                            </bufferGeometry>
                            <lineBasicMaterial attach="material" color="#64748b" transparent opacity={0.2} linewidth={1} />
                        </line>
                    )
                })}
            </group>

            {/* Draw Nodes - using Sprites or Glow for "Cosmic" feel */}
            <group position={[0, -50, 0]}>
                <group>
                    {data.nodes.map((node) => (
                        <group key={node.id} position={[node.x ?? 0, node.y ?? 0, node.z ?? 0]}>
                            <mesh onClick={() => console.log('Clicked', node.id)}>
                                <sphereGeometry args={[2.5, 16, 16]} />
                                <meshStandardMaterial
                                    color={getColorForDomain(node.domain)}
                                    emissive={getColorForDomain(node.domain)}
                                    emissiveIntensity={0.5}
                                    toneMapped={false}
                                />
                            </mesh>
                            {/* Glow halo */}
                            <mesh scale={[1.5, 1.5, 1.5]}>
                                <sphereGeometry args={[2.5, 16, 16]} />
                                <meshBasicMaterial
                                    color={getColorForDomain(node.domain)}
                                    transparent
                                    opacity={0.15}
                                />
                            </mesh>
                            {/* Label */}
                            <Billboard>
                                <Text
                                    position={[0, 4, 0]}
                                    fontSize={3}
                                    color="white"
                                    anchorX="center"
                                    anchorY="middle"
                                    outlineWidth={0.1}
                                    outlineColor="black"
                                >
                                    {node.label || node.id}
                                </Text>
                            </Billboard>
                        </group>
                    ))}
                </group>

                <OrbitControls enablePan={true} enableZoom={true} maxDistance={500} minDistance={10} />
            </group>
        </group>
    )
}


export default function CosmicGraphView() {
    const { graphData, loading } = useGraphData()

    if (loading || !graphData) {
        return <div className="text-white">Loading Graph...</div>
    }

    // graphData from hook matches {nodes: GraphNode[], edges: GraphEdge[], ... }
    return (
        <div className="w-full h-full rounded-xl overflow-hidden relative">
            <Canvas camera={{ position: [0, 0, 300], fov: 60 }} gl={{ alpha: true }} style={{ background: 'transparent' }} resize={{ scroll: false, debounce: 0 }}>
                <ambientLight intensity={0.5} />
                <pointLight position={[100, 100, 100]} />
                <GraphScene data={graphData} />
            </Canvas>
        </div>
    )
}
