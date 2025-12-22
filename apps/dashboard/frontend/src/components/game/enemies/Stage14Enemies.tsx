import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Enemy, getSpawnEase } from '../systems/EnemySystem';

// Stage 14: Mineral/Geode themed - #FF00FF, #00FFFF, #FFFF00
const getHealthColor = (hp: number, maxHp: number) => {
    const healthPct = hp / maxHp;
    if (healthPct > 0.5) return '#FF00FF'; // Magenta
    if (healthPct > 0.25) return '#00FFFF'; // Cyan
    return '#FFFF00'; // Yellow
};

/**
 * Stage 14 Asteroid: Rough rock with cracked interior revealing color-cycling crystals
 */
export const Stage14Asteroid = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const shellMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const crystalRefs = useRef<(THREE.Mesh | null)[]>([]);
    const colorPhase = useRef(0);

    const rotSpeed = useMemo(() => ({
        x: 0.05 + Math.random() * 0.06,
        y: 0.07 + Math.random() * 0.08,
        z: 0.04 + Math.random() * 0.05
    }), []);

    const crystals = useMemo(() =>
        Array.from({ length: 5 }, () => ({
            pos: new THREE.Vector3(
                (Math.random() - 0.5) * 0.8,
                (Math.random() - 0.5) * 0.8,
                (Math.random() - 0.5) * 0.8
            ),
            scale: 0.2 + Math.random() * 0.2,
            colorOffset: Math.random() * Math.PI * 2
        })), []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.rotation.x += rotSpeed.x * delta;
        ref.current.rotation.y += rotSpeed.y * delta;
        ref.current.rotation.z += rotSpeed.z * delta;
        ref.current.scale.setScalar(ease * 36);

        // Occasional teleport jitter
        if (Math.random() > 0.98) {
            ref.current.position.x += (Math.random() - 0.5) * 5;
            ref.current.position.y += (Math.random() - 0.5) * 5;
        }

        if (shellMatRef.current) {
            // Random color flashing
            const glitch = Math.random() > 0.9;
            if (glitch) {
                shellMatRef.current.color.set(['#FF00FF', '#00FFFF', '#FFFF00'][Math.floor(Math.random() * 3)]);
            } else {
                shellMatRef.current.color.set('#666666');
            }
            shellMatRef.current.opacity = ease * (glitch ? 0.8 : 0.6);
        }

        // Crystals cycle through colors with jitter
        colorPhase.current += delta * 2;
        crystalRefs.current.forEach((crystal, i) => {
            if (!crystal || !(crystal.material instanceof THREE.MeshBasicMaterial)) return;
            const phase = (colorPhase.current + crystals[i].colorOffset) % (Math.PI * 2);
            if (phase < Math.PI * 0.66) crystal.material.color.set('#FF00FF');
            else if (phase < Math.PI * 1.33) crystal.material.color.set('#00FFFF');
            else crystal.material.color.set('#FFFF00');
            crystal.material.opacity = 0.7 + Math.sin(t * 3 + i) * 0.2;

            // Jitter crystal positions
            if (Math.random() > 0.9) {
                crystal.position.x = crystals[i].pos.x + (Math.random() - 0.5) * 0.3;
                crystal.position.y = crystals[i].pos.y + (Math.random() - 0.5) * 0.3;
                crystal.position.z = crystals[i].pos.z + (Math.random() - 0.5) * 0.3;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Rough outer shell */}
            <mesh>
                <icosahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={shellMatRef} color="#666666" wireframe transparent opacity={0} />
            </mesh>
            {/* Interior crystals */}
            {crystals.map((c, i) => (
                <mesh
                    key={i}
                    ref={el => crystalRefs.current[i] = el}
                    position={c.pos.toArray()}
                    scale={c.scale}
                >
                    <boxGeometry args={[1, 2, 1]} />
                    <meshBasicMaterial color="#FF00FF" transparent opacity={0.8} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 14 Drone: Perfect cyan octahedron with orbiting magenta and yellow fragments
 */
export const Stage14Drone = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const orbitRef = useRef<THREE.Group>(null);
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
        ref.current.lookAt(0, 0, 0);
        ref.current.rotation.z += delta * 0.5;
        ref.current.scale.setScalar(ease * 18);

        // Jerky discrete movement
        if (Math.random() > 0.95) {
            ref.current.position.x += (Math.random() - 0.5) * 3;
        }

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease * 0.9;
        }

        // Orbiting fragments with jitter
        if (orbitRef.current) {
            orbitRef.current.rotation.y += delta * 2;
            orbitRef.current.rotation.x += delta * 0.5;

            // Jitter fragments
            orbitRef.current.children.forEach((frag) => {
                if (frag instanceof THREE.Mesh && Math.random() > 0.9) {
                    frag.position.x += (Math.random() - 0.5) * 0.2;
                    frag.position.y += (Math.random() - 0.5) * 0.2;
                }
            });
        }

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
            {/* Perfect cyan crystal core */}
            <mesh>
                <octahedronGeometry args={[0.6, 0]} />
                <meshBasicMaterial ref={bodyMatRef} color="#00FFFF" transparent opacity={0} />
            </mesh>
            {/* Ghost trail */}
            {[0, 1, 2, 3, 4].map(i => (
                <mesh
                    key={i}
                    ref={el => trailRefs.current[i] = el}
                    scale={0.4 - i * 0.05}
                >
                    <octahedronGeometry args={[0.6, 0]} />
                    <meshBasicMaterial color="#FF00FF" transparent opacity={0.3} />
                </mesh>
            ))}
            {/* Orbiting fragments */}
            <group ref={orbitRef}>
                <mesh position={[1, 0, 0]} scale={0.25}>
                    <tetrahedronGeometry args={[1, 0]} />
                    <meshBasicMaterial color="#FF00FF" transparent opacity={0.8} />
                </mesh>
                <mesh position={[-1, 0, 0]} scale={0.25}>
                    <tetrahedronGeometry args={[1, 0]} />
                    <meshBasicMaterial color="#FFFF00" transparent opacity={0.8} />
                </mesh>
            </group>
        </group>
    );
};

/**
 * Stage 14 Fighter: Cluster of long sharp crystals with internal pulsing light
 */
export const Stage14Fighter = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const crystalMatRefs = useRef<(THREE.MeshBasicMaterial | null)[]>([]);

    const crystals = useMemo(() => [
        { pos: [0, 0, 0], rot: [0, 0, 0], scale: [0.3, 1.5, 0.3], color: '#FF00FF' },
        { pos: [-0.5, -0.3, 0], rot: [0, 0, 0.3], scale: [0.2, 1, 0.2], color: '#00FFFF' },
        { pos: [0.5, -0.3, 0], rot: [0, 0, -0.3], scale: [0.2, 1, 0.2], color: '#FFFF00' },
        { pos: [0, -0.2, 0.4], rot: [0.3, 0, 0], scale: [0.15, 0.8, 0.15], color: '#00FFFF' },
        { pos: [0, -0.2, -0.4], rot: [-0.3, 0, 0], scale: [0.15, 0.8, 0.15], color: '#FFFF00' }
    ], []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.lookAt(0, 0, 0);
        ref.current.scale.setScalar(ease * 24);

        // Flicker in and out
        const visible = Math.sin(t * 20) > -0.8;
        ref.current.visible = visible;

        // Crystals pulse with internal light and random opacity flashes
        crystalMatRefs.current.forEach((mat, i) => {
            if (!mat) return;
            mat.opacity = ease * (0.6 + Math.sin(t * 4 + i * 0.5) * 0.3) * (Math.random() > 0.1 ? 1 : 0.3);
        });
    });

    return (
        <group ref={ref} scale={0}>
            {crystals.map((c, i) => (
                <mesh
                    key={i}
                    position={c.pos as [number, number, number]}
                    rotation={c.rot as [number, number, number]}
                    scale={c.scale as [number, number, number]}
                >
                    <cylinderGeometry args={[0.5, 1, 1, 6]} />
                    <meshBasicMaterial
                        ref={el => crystalMatRefs.current[i] = el}
                        color={c.color}
                        transparent
                        opacity={0.8}
                    />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 14 Elite: Symmetrical torus of interlocking crystalline facets, rotating and shimmering
 */
export const Stage14Elite = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const torusRef = useRef<THREE.Mesh>(null);
    const torusMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const facetRefs = useRef<(THREE.Mesh | null)[]>([]);

    const facets = useMemo(() =>
        Array.from({ length: 8 }, (_, i) => ({
            angle: (i / 8) * Math.PI * 2,
            color: ['#FF00FF', '#00FFFF', '#FFFF00'][i % 3]
        })), []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.scale.setScalar(ease * 36);

        if (torusRef.current) {
            torusRef.current.rotation.x += delta * 0.8;
            torusRef.current.rotation.y += delta * 0.5;
        }

        if (torusMatRef.current) {
            // Rapid color cycling
            const phase = Math.floor(t * 8) % 3;
            torusMatRef.current.color.set(['#FF00FF', '#00FFFF', '#FFFF00'][phase]);
            torusMatRef.current.opacity = ease * (Math.random() > 0.1 ? 0.7 : 0.3);
        }

        // Facets shimmer and jitter
        facetRefs.current.forEach((facet, i) => {
            if (!facet || !(facet.material instanceof THREE.MeshBasicMaterial)) return;
            facet.material.opacity = 0.5 + Math.sin(t * 5 + i) * 0.4;

            // Jitter facet positions
            if (Math.random() > 0.9) {
                const f = facets[i];
                facet.position.x = Math.cos(f.angle) * 1.5 + (Math.random() - 0.5) * 0.3;
                facet.position.z = Math.sin(f.angle) * 1.5 + (Math.random() - 0.5) * 0.3;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Main torus structure */}
            <mesh ref={torusRef} rotation={[Math.PI / 4, 0, 0]}>
                <torusGeometry args={[1.5, 0.4, 8, 16]} />
                <meshBasicMaterial ref={torusMatRef} color="#FF00FF" wireframe transparent opacity={0.7} />
            </mesh>
            {/* Crystalline facets */}
            {facets.map((f, i) => (
                <mesh
                    key={i}
                    ref={el => facetRefs.current[i] = el}
                    position={[
                        Math.cos(f.angle) * 1.5,
                        0,
                        Math.sin(f.angle) * 1.5
                    ]}
                    scale={0.35}
                >
                    <octahedronGeometry args={[1, 0]} />
                    <meshBasicMaterial color={f.color} transparent opacity={0.7} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 14 Boss: Giant hollow geode with dazzling crystal interior and floating center crystal
 */
export const Stage14Boss = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const shellMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const centerRef = useRef<THREE.Mesh>(null);
    const centerMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const crystalRefs = useRef<(THREE.Mesh | null)[]>([]);

    const crystals = useMemo(() =>
        Array.from({ length: 20 }, () => ({
            pos: new THREE.Vector3(
                (Math.random() - 0.5) * 4,
                (Math.random() - 0.5) * 4,
                (Math.random() - 0.5) * 4
            ).normalize().multiplyScalar(2 + Math.random()),
            scale: 0.2 + Math.random() * 0.3,
            color: ['#FF00FF', '#00FFFF', '#FFFF00'][Math.floor(Math.random() * 3)],
            phase: Math.random() * Math.PI * 2
        })), []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.rotation.y += delta * 0.2;
        ref.current.scale.setScalar(ease * 15);

        // Fast-forward teleport effect
        if (Math.random() > 0.98) {
            ref.current.position.x += (Math.random() - 0.5) * 10;
        }

        if (shellMatRef.current) {
            shellMatRef.current.opacity = ease * 0.4;
        }

        // Central crystal floats and pulses
        if (centerRef.current) {
            centerRef.current.rotation.y += delta * 1.5;
            centerRef.current.position.y = Math.sin(t) * 0.3;
        }

        if (centerMatRef.current) {
            centerMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            centerMatRef.current.opacity = 0.8 + Math.sin(t * 3) * 0.2;
        }

        // Interior crystals sparkle with random opacity
        crystalRefs.current.forEach((crystal, i) => {
            if (!crystal || !(crystal.material instanceof THREE.MeshBasicMaterial)) return;
            crystal.material.opacity = (0.5 + Math.sin(t * 4 + crystals[i].phase) * 0.4) * (Math.random() > 0.1 ? 1 : 0.4);
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Outer shell (partially transparent) */}
            <mesh scale={3.5}>
                <sphereGeometry args={[1, 8, 6]} />
                <meshBasicMaterial ref={shellMatRef} color="#555555" wireframe transparent opacity={0.4} />
            </mesh>
            {/* Central floating crystal */}
            <mesh ref={centerRef} scale={1.2}>
                <icosahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={centerMatRef} color="#FFFF00" transparent opacity={0.9} />
            </mesh>
            {/* Interior crystal formations */}
            {crystals.map((c, i) => (
                <mesh
                    key={i}
                    ref={el => crystalRefs.current[i] = el}
                    position={c.pos.toArray()}
                    scale={c.scale}
                    rotation={[Math.random() * Math.PI, Math.random() * Math.PI, 0]}
                >
                    <coneGeometry args={[0.3, 1, 5]} />
                    <meshBasicMaterial color={c.color} transparent opacity={0.7} />
                </mesh>
            ))}
        </group>
    );
};
