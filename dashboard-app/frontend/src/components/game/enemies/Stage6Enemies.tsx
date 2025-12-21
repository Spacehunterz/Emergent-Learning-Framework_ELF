import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Enemy, getSpawnEase } from '../systems/EnemySystem';

// Stage 6: Ice/Crystal themed - #6ECFFF, #B8F7FF, #7B9CFF
const getHealthColor = (hp: number, maxHp: number) => {
    const healthPct = hp / maxHp;
    if (healthPct > 0.5) return '#6ECFFF'; // Ice blue
    if (healthPct > 0.25) return '#B8F7FF'; // Light cyan
    return '#7B9CFF'; // Purple-blue
};

/**
 * Stage 6 Asteroid: Fractured crystal slab with shard outcroppings
 */
export const Stage6Asteroid = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const mainMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const latticeRef = useRef<THREE.Mesh>(null);

    const rotSpeed = useMemo(() => ({
        x: 0.15 + Math.random() * 0.2,
        y: 0.1 + Math.random() * 0.15,
        z: 0.08 + Math.random() * 0.1
    }), []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.rotation.x += rotSpeed.x * delta;
        ref.current.rotation.y += rotSpeed.y * delta;
        ref.current.rotation.z += rotSpeed.z * delta;
        ref.current.scale.setScalar(ease * 36);

        if (mainMatRef.current) {
            mainMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            mainMatRef.current.opacity = ease * 0.85;
        }

        // Lattice brightness ripples
        if (latticeRef.current && latticeRef.current.material instanceof THREE.MeshBasicMaterial) {
            latticeRef.current.material.opacity = 0.4 + Math.sin(t * 2 + data.seed) * 0.2;
        }
    });

    return (
        <group ref={ref} scale={0}>
            {/* Main crystal slab */}
            <mesh scale={[1.2, 0.8, 1]}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={mainMatRef} color="#6ECFFF" wireframe transparent opacity={0} />
            </mesh>
            {/* Shard outcroppings */}
            {[[-0.6, 0.5, 0.3], [0.7, -0.4, 0.2], [0.2, 0.6, -0.5], [-0.4, -0.5, -0.4]].map((pos, i) => (
                <mesh key={i} position={pos as [number, number, number]} rotation={[i * 0.5, i * 0.3, i * 0.4]} scale={0.4}>
                    <tetrahedronGeometry args={[1, 0]} />
                    <meshBasicMaterial color="#B8F7FF" wireframe transparent opacity={0.7} />
                </mesh>
            ))}
            {/* Internal lattice */}
            <mesh ref={latticeRef} scale={0.6}>
                <icosahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#7B9CFF" wireframe transparent opacity={0.4} />
            </mesh>
        </group>
    );
};

/**
 * Stage 6 Drone: Sharp pyramid with faceted edges
 */
export const Stage6Drone = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const keelRef = useRef<THREE.Mesh>(null);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.lookAt(0, 0, 0);
        ref.current.rotation.z += delta * 6; // Quick roll
        ref.current.scale.setScalar(ease * 18);

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease * 0.9;
        }

        // Keel shimmer wave
        if (keelRef.current && keelRef.current.material instanceof THREE.MeshBasicMaterial) {
            keelRef.current.material.opacity = 0.5 + Math.sin(t * 8 + data.seed) * 0.3;
        }
    });

    return (
        <group ref={ref} scale={0}>
            {/* Sharp pyramid */}
            <mesh rotation={[Math.PI, 0, 0]}>
                <coneGeometry args={[1, 2.5, 4]} />
                <meshBasicMaterial ref={bodyMatRef} color="#6ECFFF" wireframe transparent opacity={0} />
            </mesh>
            {/* Faceted edges */}
            <mesh scale={0.7}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#B8F7FF" wireframe transparent opacity={0.6} />
            </mesh>
            {/* Pointed keel */}
            <mesh ref={keelRef} position={[0, -1.5, 0]} rotation={[0, 0, 0]} scale={[0.15, 0.8, 0.15]}>
                <coneGeometry args={[1, 1, 4]} />
                <meshBasicMaterial color="#7B9CFF" wireframe transparent opacity={0.5} />
            </mesh>
        </group>
    );
};

/**
 * Stage 6 Fighter: Double-pyramid with thin icicle wings
 */
export const Stage6Fighter = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const wingLeftRef = useRef<THREE.Mesh>(null);
    const wingRightRef = useRef<THREE.Mesh>(null);
    const tailMatRef = useRef<THREE.MeshBasicMaterial>(null);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const phase = data.seed * Math.PI * 2;
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.lookAt(0, 0, 0);
        ref.current.scale.setScalar(ease * 24);

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease;
        }

        // Wings flex slightly
        const wingFlex = Math.sin(t * 2 + phase) * 0.1;
        if (wingLeftRef.current) wingLeftRef.current.rotation.z = -0.4 + wingFlex;
        if (wingRightRef.current) wingRightRef.current.rotation.z = 0.4 - wingFlex;

        // Tail crack glow pulses
        if (tailMatRef.current) {
            tailMatRef.current.opacity = 0.5 + Math.sin(t * 4 + phase) * 0.3;
        }
    });

    return (
        <group ref={ref} scale={0}>
            {/* Double-pyramid body */}
            <mesh rotation={[Math.PI / 2, 0, 0]} scale={[0.5, 1.5, 0.5]}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={bodyMatRef} color="#6ECFFF" wireframe transparent opacity={0} />
            </mesh>
            {/* Thin icicle wings */}
            <mesh ref={wingLeftRef} position={[-1, 0, 0]} rotation={[0, 0, -0.4]} scale={[1.5, 0.08, 0.3]}>
                <coneGeometry args={[1, 1, 4]} />
                <meshBasicMaterial color="#B8F7FF" wireframe transparent opacity={0.7} />
            </mesh>
            <mesh ref={wingRightRef} position={[1, 0, 0]} rotation={[0, 0, 0.4]} scale={[1.5, 0.08, 0.3]}>
                <coneGeometry args={[1, 1, 4]} />
                <meshBasicMaterial color="#B8F7FF" wireframe transparent opacity={0.7} />
            </mesh>
            {/* Split tail */}
            <mesh position={[-0.3, 0, 1]} rotation={[Math.PI / 2, 0, -0.2]} scale={[0.1, 0.6, 0.1]}>
                <coneGeometry args={[1, 1, 4]} />
                <meshBasicMaterial ref={tailMatRef} color="#7B9CFF" wireframe transparent opacity={0.5} />
            </mesh>
            <mesh position={[0.3, 0, 1]} rotation={[Math.PI / 2, 0, 0.2]} scale={[0.1, 0.6, 0.1]}>
                <coneGeometry args={[1, 1, 4]} />
                <meshBasicMaterial color="#7B9CFF" wireframe transparent opacity={0.5} />
            </mesh>
        </group>
    );
};

/**
 * Stage 6 Elite: Crystalline core with three orbiting shard triangles
 */
export const Stage6Elite = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const shardRefs = useRef<(THREE.Mesh | null)[]>([]);

    const shardData = useMemo(() => [
        { radius: 2, speed: 1, yOffset: 0 },
        { radius: 2.5, speed: 0.7, yOffset: 0.5 },
        { radius: 1.8, speed: 1.3, yOffset: -0.5 }
    ], []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.scale.setScalar(ease * 36);

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            // Core flickers like refracted light
            bodyMatRef.current.opacity = 0.6 + Math.sin(t * 6 + data.seed) * 0.2 + Math.sin(t * 11) * 0.1;
        }

        // Shards orbit at staggered speeds
        shardRefs.current.forEach((shard, i) => {
            if (!shard) return;
            const d = shardData[i];
            const angle = t * d.speed + (i * Math.PI * 2 / 3);
            shard.position.set(
                Math.cos(angle) * d.radius,
                d.yOffset,
                Math.sin(angle) * d.radius
            );
            shard.rotation.y = angle;
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Crystalline core */}
            <mesh>
                <dodecahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={bodyMatRef} color="#6ECFFF" wireframe transparent opacity={0.6} />
            </mesh>
            <mesh scale={0.6}>
                <icosahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#B8F7FF" wireframe transparent opacity={0.8} />
            </mesh>
            {/* Orbiting shard triangles */}
            {shardData.map((_, i) => (
                <mesh key={i} ref={el => shardRefs.current[i] = el} scale={0.5}>
                    <tetrahedronGeometry args={[1, 0]} />
                    <meshBasicMaterial color="#7B9CFF" wireframe transparent opacity={0.7} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 6 Boss: Colossal geode frame with layered inner poly-shells
 */
export const Stage6Boss = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const outerMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const shell1Ref = useRef<THREE.Mesh>(null);
    const shell2Ref = useRef<THREE.Mesh>(null);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.scale.setScalar(ease * 15);

        if (outerMatRef.current) {
            outerMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            // Outer frame glints in pulses
            outerMatRef.current.opacity = 0.6 + Math.sin(t * 1.5) * 0.15;
        }

        // Inner shells rotate in opposite directions
        if (shell1Ref.current) {
            shell1Ref.current.rotation.x += delta * 0.4;
            shell1Ref.current.rotation.y += delta * 0.3;
        }
        if (shell2Ref.current) {
            shell2Ref.current.rotation.x -= delta * 0.3;
            shell2Ref.current.rotation.z += delta * 0.5;
        }
    });

    return (
        <group ref={ref} scale={0}>
            {/* Outer geode frame */}
            <mesh scale={3}>
                <icosahedronGeometry args={[1, 1]} />
                <meshBasicMaterial ref={outerMatRef} color="#6ECFFF" wireframe transparent opacity={0.6} />
            </mesh>
            {/* Layered inner shells */}
            <mesh ref={shell1Ref} scale={2}>
                <dodecahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#B8F7FF" wireframe transparent opacity={0.5} />
            </mesh>
            <mesh ref={shell2Ref} scale={1.2}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#7B9CFF" wireframe transparent opacity={0.7} />
            </mesh>
            {/* Crystal core */}
            <mesh scale={0.6}>
                <tetrahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#ffffff" wireframe transparent opacity={0.9} />
            </mesh>
            {/* Crystal spires */}
            {Array.from({ length: 6 }).map((_, i) => {
                const angle = (i / 6) * Math.PI * 2;
                return (
                    <mesh
                        key={i}
                        position={[Math.cos(angle) * 2.5, Math.sin(angle) * 2.5, 0]}
                        rotation={[0, 0, angle]}
                        scale={[0.2, 1.2, 0.2]}
                    >
                        <coneGeometry args={[1, 1, 4]} />
                        <meshBasicMaterial color="#B8F7FF" wireframe transparent opacity={0.6} />
                    </mesh>
                );
            })}
        </group>
    );
};
