import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Enemy, getSpawnEase } from '../systems/EnemySystem';

// Stage 11: Toxic/Radiation themed - #7CFC00, #FFFF00, #00FF00
const getHealthColor = (hp: number, maxHp: number) => {
    const healthPct = hp / maxHp;
    if (healthPct > 0.5) return '#7CFC00'; // LawnGreen
    if (healthPct > 0.25) return '#FFFF00'; // Yellow
    return '#00FF00'; // Lime
};

/**
 * Stage 11 Asteroid: Lumpy icosahedron with pulsing green glow and yellow crystal protrusions
 */
export const Stage11Asteroid = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const mainMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const crystalRefs = useRef<(THREE.Mesh | null)[]>([]);

    const rotSpeed = useMemo(() => ({
        x: 0.06 + Math.random() * 0.08,
        y: 0.08 + Math.random() * 0.1,
        z: 0.05 + Math.random() * 0.07
    }), []);

    const crystals = useMemo(() =>
        Array.from({ length: 6 }, () => ({
            pos: new THREE.Vector3(
                (Math.random() - 0.5) * 1.5,
                (Math.random() - 0.5) * 1.5,
                (Math.random() - 0.5) * 1.5
            ).normalize().multiplyScalar(0.9),
            rot: new THREE.Euler(Math.random() * Math.PI, Math.random() * Math.PI, 0),
            scale: 0.15 + Math.random() * 0.15
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
                mainMatRef.current.color.set(['#7CFC00', '#FFFF00', '#00FF00'][Math.floor(Math.random() * 3)]);
            } else {
                mainMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            }
            // Unstable pulsing glow
            mainMatRef.current.opacity = ease * (glitch ? 0.5 : (0.6 + Math.sin(t * 4) * 0.25));
        }

        // Crystals glow independently and jitter
        crystalRefs.current.forEach((crystal, i) => {
            if (!crystal || !(crystal.material instanceof THREE.MeshBasicMaterial)) return;
            crystal.material.opacity = 0.7 + Math.sin(t * 3 + i) * 0.3;
            // Random jitter
            if (Math.random() > 0.95) {
                crystal.position.x = crystals[i].pos.x + (Math.random() - 0.5) * 0.2;
                crystal.position.y = crystals[i].pos.y + (Math.random() - 0.5) * 0.2;
                crystal.position.z = crystals[i].pos.z + (Math.random() - 0.5) * 0.2;
            } else {
                crystal.position.copy(crystals[i].pos);
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Lumpy radioactive core */}
            <mesh>
                <icosahedronGeometry args={[1, 1]} />
                <meshBasicMaterial ref={mainMatRef} color="#7CFC00" wireframe transparent opacity={0} />
            </mesh>
            {/* Yellow crystal protrusions */}
            {crystals.map((c, i) => (
                <mesh
                    key={i}
                    ref={el => crystalRefs.current[i] = el}
                    position={c.pos.toArray()}
                    rotation={c.rot}
                    scale={c.scale}
                >
                    <coneGeometry args={[0.3, 1, 4]} />
                    <meshBasicMaterial color="#FFFF00" transparent opacity={0.8} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 11 Drone: Yellow sphere core with two rotating green torus rings
 */
export const Stage11Drone = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const ring1Ref = useRef<THREE.Mesh>(null);
    const ring2Ref = useRef<THREE.Mesh>(null);
    const trailRefs = useRef<(THREE.Mesh | null)[]>([]);
    const trailPositions = useRef<THREE.Vector3[]>([]);

    useMemo(() => {
        trailPositions.current = Array.from({ length: 5 }, () => new THREE.Vector3());
    }, []);

    useFrame((state, delta) => {
        if (!ref.current) return;
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

        // Rings rotate on different axes
        if (ring1Ref.current) ring1Ref.current.rotation.z += delta * 3;
        if (ring2Ref.current) ring2Ref.current.rotation.x += delta * 2.5;

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
            {/* Yellow core */}
            <mesh>
                <sphereGeometry args={[0.6, 12, 8]} />
                <meshBasicMaterial ref={bodyMatRef} color="#FFFF00" transparent opacity={0} />
            </mesh>
            {/* Green rotating rings */}
            <mesh ref={ring1Ref} rotation={[Math.PI / 2, 0, 0]}>
                <torusGeometry args={[1, 0.06, 8, 24]} />
                <meshBasicMaterial color="#7CFC00" transparent opacity={0.8} />
            </mesh>
            <mesh ref={ring2Ref} rotation={[0, Math.PI / 2, 0]}>
                <torusGeometry args={[1.2, 0.05, 8, 24]} />
                <meshBasicMaterial color="#00FF00" transparent opacity={0.7} />
            </mesh>
            {/* Ghost trail */}
            {[0, 1, 2, 3, 4].map(i => (
                <mesh
                    key={`trail-${i}`}
                    ref={el => trailRefs.current[i] = el}
                    scale={0.4 - i * 0.05}
                >
                    <sphereGeometry args={[0.6, 10, 6]} />
                    <meshBasicMaterial color="#7CFC00" transparent opacity={0.3} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 11 Fighter: Pointed cone body with yellow cockpit, flickering glow, pivoting wings
 */
export const Stage11Fighter = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const wingLeftRef = useRef<THREE.Mesh>(null);
    const wingRightRef = useRef<THREE.Mesh>(null);
    const cockpitMatRef = useRef<THREE.MeshBasicMaterial>(null);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const phase = data.seed * Math.PI * 2;
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.lookAt(0, 0, 0);
        ref.current.scale.setScalar(ease * 24);

        // Flicker in and out
        const visible = Math.sin(t * 18) > -0.8;
        ref.current.visible = visible;

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            // Flickering radiation glow
            const flicker = Math.random() > 0.9 ? 0.4 : 1;
            bodyMatRef.current.opacity = ease * 0.85 * flicker;
        }

        if (cockpitMatRef.current) {
            cockpitMatRef.current.opacity = 0.7 + Math.sin(t * 5) * 0.3;
        }

        // Wings pivot up and down
        const wingPivot = Math.sin(t * 1.5 + phase) * 0.2;
        if (wingLeftRef.current) wingLeftRef.current.rotation.z = wingPivot;
        if (wingRightRef.current) wingRightRef.current.rotation.z = -wingPivot;
    });

    return (
        <group ref={ref} scale={0}>
            {/* Pointed cone body */}
            <mesh rotation={[Math.PI, 0, 0]}>
                <coneGeometry args={[0.6, 2.5, 6]} />
                <meshBasicMaterial ref={bodyMatRef} color="#7CFC00" wireframe transparent opacity={0} />
            </mesh>
            {/* Yellow cockpit sphere */}
            <mesh position={[0, 0.5, 0]}>
                <sphereGeometry args={[0.35, 8, 6]} />
                <meshBasicMaterial ref={cockpitMatRef} color="#FFFF00" transparent opacity={0.7} />
            </mesh>
            {/* Pivoting wings */}
            <mesh ref={wingLeftRef} position={[-0.8, 0, 0]} rotation={[0, 0, 0.3]}>
                <planeGeometry args={[1.2, 0.4]} />
                <meshBasicMaterial color="#00FF00" transparent opacity={0.6} side={THREE.DoubleSide} />
            </mesh>
            <mesh ref={wingRightRef} position={[0.8, 0, 0]} rotation={[0, 0, -0.3]}>
                <planeGeometry args={[1.2, 0.4]} />
                <meshBasicMaterial color="#00FF00" transparent opacity={0.6} side={THREE.DoubleSide} />
            </mesh>
        </group>
    );
};

/**
 * Stage 11 Elite: Octahedron cycling green/yellow, surrounded by spinning tetrahedron shards
 */
export const Stage11Elite = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const shardRefs = useRef<(THREE.Mesh | null)[]>([]);
    const shardGroupRef = useRef<THREE.Group>(null);

    const shards = useMemo(() =>
        Array.from({ length: 8 }, (_, i) => ({
            angle: (i / 8) * Math.PI * 2,
            dist: 1.8,
            phase: Math.random() * Math.PI * 2
        })), []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.rotation.y += delta * 0.5;
        ref.current.scale.setScalar(ease * 36);

        if (bodyMatRef.current) {
            // Cycle between green and yellow
            const cycle = Math.sin(t * 2) > 0 ? '#7CFC00' : '#FFFF00';
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease * 0.8;
        }

        // Shards spin rapidly around the core
        if (shardGroupRef.current) {
            shardGroupRef.current.rotation.y += delta * 4;
            shardGroupRef.current.rotation.x += delta * 1.5;
        }

        shardRefs.current.forEach((shard, i) => {
            if (!shard) return;
            shard.rotation.x += delta * 3;
            shard.rotation.z += delta * 2;
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Central octahedron */}
            <mesh>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={bodyMatRef} color="#7CFC00" wireframe transparent opacity={0} />
            </mesh>
            <mesh scale={0.6}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#FFFF00" transparent opacity={0.5} />
            </mesh>
            {/* Spinning shard shield */}
            <group ref={shardGroupRef}>
                {shards.map((s, i) => (
                    <mesh
                        key={i}
                        ref={el => shardRefs.current[i] = el}
                        position={[
                            Math.cos(s.angle) * s.dist,
                            Math.sin(s.phase) * 0.5,
                            Math.sin(s.angle) * s.dist
                        ]}
                        scale={0.3}
                    >
                        <tetrahedronGeometry args={[1, 0]} />
                        <meshBasicMaterial color="#00FF00" transparent opacity={0.7} />
                    </mesh>
                ))}
            </group>
        </group>
    );
};

/**
 * Stage 11 Boss: Massive bubbling sphere with rotating cylinder vents and pincer arms
 */
export const Stage11Boss = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const ventRefs = useRef<(THREE.Mesh | null)[]>([]);
    const pincerLeftRef = useRef<THREE.Group>(null);
    const pincerRightRef = useRef<THREE.Group>(null);

    const vents = useMemo(() => [
        { pos: [0, 1.5, 0], rot: [0, 0, 0] },
        { pos: [1.3, 0, 0.8], rot: [0, 0, Math.PI / 4] },
        { pos: [-1.3, 0, 0.8], rot: [0, 0, -Math.PI / 4] }
    ], []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.scale.setScalar(ease * 15);

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            // Bubbling effect
            bodyMatRef.current.opacity = ease * (0.6 + Math.sin(t * 6) * 0.15);
        }

        // Vents rotate
        ventRefs.current.forEach((vent, i) => {
            if (!vent) return;
            vent.rotation.y += delta * (2 + i * 0.5);
        });

        // Pincers open and close
        const pincerAngle = Math.sin(t * 1.5) * 0.3;
        if (pincerLeftRef.current) pincerLeftRef.current.rotation.z = -0.5 + pincerAngle;
        if (pincerRightRef.current) pincerRightRef.current.rotation.z = 0.5 - pincerAngle;
    });

    return (
        <group ref={ref} scale={0}>
            {/* Massive bubbling core */}
            <mesh scale={3}>
                <sphereGeometry args={[1, 16, 12]} />
                <meshBasicMaterial ref={bodyMatRef} color="#7CFC00" wireframe transparent opacity={0.6} />
            </mesh>
            <mesh scale={2.5}>
                <icosahedronGeometry args={[1, 1]} />
                <meshBasicMaterial color="#FFFF00" wireframe transparent opacity={0.4} />
            </mesh>
            {/* Rotating vents */}
            {vents.map((v, i) => (
                <mesh
                    key={i}
                    ref={el => ventRefs.current[i] = el}
                    position={v.pos as [number, number, number]}
                    rotation={v.rot as [number, number, number]}
                    scale={0.8}
                >
                    <cylinderGeometry args={[0.4, 0.6, 1.2, 8]} />
                    <meshBasicMaterial color="#00FF00" transparent opacity={0.7} />
                </mesh>
            ))}
            {/* Pincer arms */}
            <group ref={pincerLeftRef} position={[-2.5, -0.5, 0]}>
                {[0, 1, 2].map(i => (
                    <mesh key={i} position={[-i * 0.6, 0, 0]} scale={[0.5, 0.3, 0.3]}>
                        <boxGeometry args={[1, 1, 1]} />
                        <meshBasicMaterial color="#FFFF00" transparent opacity={0.7} />
                    </mesh>
                ))}
            </group>
            <group ref={pincerRightRef} position={[2.5, -0.5, 0]}>
                {[0, 1, 2].map(i => (
                    <mesh key={i} position={[i * 0.6, 0, 0]} scale={[0.5, 0.3, 0.3]}>
                        <boxGeometry args={[1, 1, 1]} />
                        <meshBasicMaterial color="#FFFF00" transparent opacity={0.7} />
                    </mesh>
                ))}
            </group>
        </group>
    );
};
