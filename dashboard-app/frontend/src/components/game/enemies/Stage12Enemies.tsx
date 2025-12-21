import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Enemy, getSpawnEase } from '../systems/EnemySystem';

// Stage 12: Electric/Plasma themed - #00BFFF, #FFFFFF, #4169E1
const getHealthColor = (hp: number, maxHp: number) => {
    const healthPct = hp / maxHp;
    if (healthPct > 0.5) return '#00BFFF'; // DeepSkyBlue
    if (healthPct > 0.25) return '#FFFFFF'; // White
    return '#4169E1'; // RoyalBlue
};

/**
 * Stage 12 Asteroid: Smooth sphere with crackling energy nodes on surface
 */
export const Stage12Asteroid = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const mainMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const nodeRefs = useRef<(THREE.Mesh | null)[]>([]);

    const rotSpeed = useMemo(() => ({
        x: 0.04 + Math.random() * 0.06,
        y: 0.06 + Math.random() * 0.08,
        z: 0.03 + Math.random() * 0.05
    }), []);

    const nodes = useMemo(() =>
        Array.from({ length: 8 }, () => ({
            pos: new THREE.Vector3(
                (Math.random() - 0.5) * 2,
                (Math.random() - 0.5) * 2,
                (Math.random() - 0.5) * 2
            ).normalize().multiplyScalar(0.95),
            phase: Math.random() * Math.PI * 2
        })), []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);

        // Occasional teleport jitter
        if (Math.random() > 0.98) {
            ref.current.position.x += (Math.random() - 0.5) * 4;
            ref.current.position.y += (Math.random() - 0.5) * 4;
        }

        ref.current.rotation.x += rotSpeed.x * delta;
        ref.current.rotation.y += rotSpeed.y * delta;
        ref.current.rotation.z += rotSpeed.z * delta;
        ref.current.scale.setScalar(ease * 36);

        if (mainMatRef.current) {
            // Random color flashing between stage colors
            const glitch = Math.random() > 0.92;
            if (glitch) {
                mainMatRef.current.color.set(['#00BFFF', '#FFFFFF', '#4169E1'][Math.floor(Math.random() * 3)]);
            } else {
                mainMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            }
            mainMatRef.current.opacity = ease * (glitch ? 0.5 : 0.7);
        }

        // Energy nodes pulse with random crackling and jitter
        nodeRefs.current.forEach((node, i) => {
            if (!node || !(node.material instanceof THREE.MeshBasicMaterial)) return;
            const crackle = Math.random() > 0.85 ? 1.5 : 1;
            node.material.opacity = (0.5 + Math.sin(t * 8 + nodes[i].phase) * 0.5) * crackle;
            node.scale.setScalar(0.08 * crackle);
            // Random jitter
            if (Math.random() > 0.95) {
                node.position.x = nodes[i].pos.x + (Math.random() - 0.5) * 0.2;
                node.position.y = nodes[i].pos.y + (Math.random() - 0.5) * 0.2;
                node.position.z = nodes[i].pos.z + (Math.random() - 0.5) * 0.2;
            } else {
                node.position.copy(nodes[i].pos);
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Smooth plasma sphere */}
            <mesh>
                <sphereGeometry args={[1, 16, 12]} />
                <meshBasicMaterial ref={mainMatRef} color="#00BFFF" transparent opacity={0} />
            </mesh>
            <mesh scale={0.85}>
                <sphereGeometry args={[1, 12, 8]} />
                <meshBasicMaterial color="#4169E1" wireframe transparent opacity={0.5} />
            </mesh>
            {/* Energy nodes */}
            {nodes.map((n, i) => (
                <mesh
                    key={i}
                    ref={el => nodeRefs.current[i] = el}
                    position={n.pos.toArray()}
                    scale={0.08}
                >
                    <sphereGeometry args={[1, 6, 4]} />
                    <meshBasicMaterial color="#FFFFFF" transparent opacity={0.8} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 12 Drone: White icosahedron core in cage of three intersecting blue rings
 */
export const Stage12Drone = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const ringRefs = useRef<(THREE.Mesh | null)[]>([]);
    const trailRefs = useRef<(THREE.Mesh | null)[]>([]);
    const trailPositions = useRef<THREE.Vector3[]>([]);

    useMemo(() => {
        trailPositions.current = Array.from({ length: 5 }, () => new THREE.Vector3());
    }, []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);

        // Jerky discrete movement
        if (Math.random() > 0.96) {
            ref.current.position.x += (Math.random() - 0.5) * 2;
        }

        ref.current.lookAt(0, 0, 0);
        ref.current.scale.setScalar(ease * 18);

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease * 0.9;
        }

        // Rings rotate on different axes with electric arcs
        ringRefs.current.forEach((ring, i) => {
            if (!ring) return;
            ring.rotation.z += delta * (2 + i);
            if (ring.material instanceof THREE.MeshBasicMaterial) {
                // Random arc flicker
                ring.material.opacity = 0.6 + (Math.random() > 0.9 ? 0.4 : 0);
            }
        });

        // Update ghost trail
        for (let i = trailPositions.current.length - 1; i > 0; i--) {
            trailPositions.current[i].copy(trailPositions.current[i - 1]);
        }
        trailPositions.current[0].copy(data.position);

        trailRefs.current.forEach((trail, i) => {
            if (!trail) return;
            trail.position.copy(trailPositions.current[i]);
            if (trail.material instanceof THREE.MeshBasicMaterial) {
                trail.material.opacity = 0.4 - i * 0.08;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* White icosahedron core */}
            <mesh>
                <icosahedronGeometry args={[0.5, 0]} />
                <meshBasicMaterial ref={bodyMatRef} color="#FFFFFF" transparent opacity={0} />
            </mesh>
            {/* Three intersecting cage rings */}
            <mesh ref={el => ringRefs.current[0] = el} rotation={[0, 0, 0]}>
                <torusGeometry args={[1, 0.05, 8, 24]} />
                <meshBasicMaterial color="#4169E1" transparent opacity={0.7} />
            </mesh>
            <mesh ref={el => ringRefs.current[1] = el} rotation={[Math.PI / 2, 0, 0]}>
                <torusGeometry args={[1, 0.05, 8, 24]} />
                <meshBasicMaterial color="#00BFFF" transparent opacity={0.7} />
            </mesh>
            <mesh ref={el => ringRefs.current[2] = el} rotation={[0, Math.PI / 2, 0]}>
                <torusGeometry args={[1, 0.05, 8, 24]} />
                <meshBasicMaterial color="#4169E1" transparent opacity={0.7} />
            </mesh>
            {/* Ghost trail */}
            {[0, 1, 2, 3, 4].map(i => (
                <mesh
                    key={`trail-${i}`}
                    ref={el => trailRefs.current[i] = el}
                    scale={0.3 - i * 0.04}
                >
                    <icosahedronGeometry args={[0.5, 0]} />
                    <meshBasicMaterial color="#00BFFF" transparent opacity={0.3} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 12 Fighter: Sleek arrow with conductor rods and plasma trails
 */
export const Stage12Fighter = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const conductorMatRefs = useRef<(THREE.MeshBasicMaterial | null)[]>([]);
    const arcPhase = useRef(0);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.lookAt(0, 0, 0);
        ref.current.scale.setScalar(ease * 24);

        // Flicker in and out
        const visible = Math.sin(t * 18) > -0.8;
        ref.current.visible = visible;

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease * (Math.random() > 0.1 ? 1 : 0.4);
        }

        // Conductors arc with electricity
        arcPhase.current += delta * 15;
        conductorMatRefs.current.forEach((mat, i) => {
            if (!mat) return;
            const arc = Math.sin(arcPhase.current + i * Math.PI) > 0.7 ? 1 : 0.6;
            mat.opacity = arc;
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Sleek arrow body */}
            <mesh rotation={[Math.PI, 0, 0]} scale={[0.4, 1.5, 0.2]}>
                <coneGeometry args={[1, 2, 4]} />
                <meshBasicMaterial ref={bodyMatRef} color="#00BFFF" wireframe transparent opacity={0} />
            </mesh>
            {/* White conductor rods */}
            <mesh position={[-0.6, 0, 0]} scale={[0.1, 2, 0.1]}>
                <cylinderGeometry args={[1, 1, 1, 8]} />
                <meshBasicMaterial ref={el => conductorMatRefs.current[0] = el} color="#FFFFFF" transparent opacity={0.8} />
            </mesh>
            <mesh position={[0.6, 0, 0]} scale={[0.1, 2, 0.1]}>
                <cylinderGeometry args={[1, 1, 1, 8]} />
                <meshBasicMaterial ref={el => conductorMatRefs.current[1] = el} color="#FFFFFF" transparent opacity={0.8} />
            </mesh>
            {/* Plasma engine glow */}
            <mesh position={[0, 1.2, 0]} scale={0.4}>
                <sphereGeometry args={[1, 8, 6]} />
                <meshBasicMaterial color="#4169E1" transparent opacity={0.6} />
            </mesh>
        </group>
    );
};

/**
 * Stage 12 Elite: Rotating torus knot with orbiting energy nodes
 */
export const Stage12Elite = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const nodeGroupRef = useRef<THREE.Group>(null);
    const nodeRefs = useRef<(THREE.Mesh | null)[]>([]);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.rotation.y += delta * 0.8;
        ref.current.rotation.x += delta * 0.3;
        ref.current.scale.setScalar(ease * 36);

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease * 0.9;
        }

        // Nodes orbit
        if (nodeGroupRef.current) {
            nodeGroupRef.current.rotation.y += delta * 2;
        }

        // Pulsing beam connections
        nodeRefs.current.forEach((node, i) => {
            if (!node || !(node.material instanceof THREE.MeshBasicMaterial)) return;
            node.material.opacity = 0.6 + Math.sin(t * 4 + i) * 0.4;
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Central torus knot */}
            <mesh>
                <torusKnotGeometry args={[0.8, 0.2, 64, 8]} />
                <meshBasicMaterial ref={bodyMatRef} color="#FFFFFF" wireframe transparent opacity={0} />
            </mesh>
            {/* Orbiting energy nodes */}
            <group ref={nodeGroupRef}>
                {[0, 1, 2, 3].map(i => (
                    <mesh
                        key={i}
                        ref={el => nodeRefs.current[i] = el}
                        position={[
                            Math.cos(i * Math.PI / 2) * 1.8,
                            0,
                            Math.sin(i * Math.PI / 2) * 1.8
                        ]}
                        scale={0.25}
                    >
                        <sphereGeometry args={[1, 8, 6]} />
                        <meshBasicMaterial color="#4169E1" transparent opacity={0.8} />
                    </mesh>
                ))}
            </group>
        </group>
    );
};

/**
 * Stage 12 Boss: Giant blue torus with white spikes and central energy ball
 */
export const Stage12Boss = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const ringMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const coreMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const spikeRefs = useRef<(THREE.Mesh | null)[]>([]);

    const spikes = useMemo(() =>
        Array.from({ length: 12 }, (_, i) => ({
            angle: (i / 12) * Math.PI * 2,
            phase: Math.random() * Math.PI * 2
        })), []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.rotation.z += delta * 0.3;
        ref.current.scale.setScalar(ease * 15);

        if (ringMatRef.current) {
            ringMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            ringMatRef.current.opacity = ease * 0.8;
        }

        // Core pulses intensely
        if (coreMatRef.current) {
            coreMatRef.current.opacity = 0.7 + Math.sin(t * 5) * 0.3;
        }

        // Spikes crackle with lightning
        spikeRefs.current.forEach((spike, i) => {
            if (!spike || !(spike.material instanceof THREE.MeshBasicMaterial)) return;
            const crackle = Math.random() > 0.92 ? 1.2 : 1;
            spike.material.opacity = 0.7 * crackle;
            spike.scale.setScalar(0.5 * crackle);
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Giant torus ring */}
            <mesh rotation={[Math.PI / 2, 0, 0]}>
                <torusGeometry args={[3, 0.6, 16, 32]} />
                <meshBasicMaterial ref={ringMatRef} color="#4169E1" transparent opacity={0.8} />
            </mesh>
            {/* White spikes on ring */}
            {spikes.map((s, i) => (
                <mesh
                    key={i}
                    ref={el => spikeRefs.current[i] = el}
                    position={[
                        Math.cos(s.angle) * 3,
                        0,
                        Math.sin(s.angle) * 3
                    ]}
                    rotation={[0, 0, s.angle + Math.PI / 2]}
                    scale={0.5}
                >
                    <coneGeometry args={[0.3, 1.5, 4]} />
                    <meshBasicMaterial color="#FFFFFF" transparent opacity={0.8} />
                </mesh>
            ))}
            {/* Central energy ball */}
            <mesh scale={1.5}>
                <sphereGeometry args={[1, 16, 12]} />
                <meshBasicMaterial ref={coreMatRef} color="#FFFFFF" transparent opacity={0.8} />
            </mesh>
            <mesh scale={1.2}>
                <icosahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#00BFFF" wireframe transparent opacity={0.6} />
            </mesh>
        </group>
    );
};
