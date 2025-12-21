import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Enemy, getSpawnEase } from '../systems/EnemySystem';

// Stage 9: Mechanical/Steampunk themed - #C97A2B, #5A3A24, #E1B67A
const getHealthColor = (hp: number, maxHp: number) => {
    const healthPct = hp / maxHp;
    if (healthPct > 0.5) return '#C97A2B'; // Copper
    if (healthPct > 0.25) return '#E1B67A'; // Brass
    return '#5A3A24'; // Dark bronze
};

/**
 * Stage 9 Asteroid: Chunk of machinery with gear teeth and pipes
 */
export const Stage9Asteroid = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const mainMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const gearRef = useRef<THREE.Mesh>(null);

    const rotSpeed = useMemo(() => ({
        x: 0.1 + Math.random() * 0.12,
        y: 0.08 + Math.random() * 0.1,
        z: 0.06 + Math.random() * 0.08
    }), []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.rotation.x += rotSpeed.x * delta;
        ref.current.rotation.y += rotSpeed.y * delta;
        ref.current.rotation.z += rotSpeed.z * delta;
        ref.current.scale.setScalar(ease * 36);

        if (mainMatRef.current) {
            mainMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            mainMatRef.current.opacity = ease * 0.9;
        }

        // Embedded gear rotates
        if (gearRef.current) {
            gearRef.current.rotation.z += delta * 2;
        }
    });

    return (
        <group ref={ref} scale={0}>
            {/* Main machinery chunk */}
            <mesh scale={[1.1, 0.9, 1]}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial ref={mainMatRef} color="#C97A2B" wireframe transparent opacity={0} />
            </mesh>
            {/* Gear teeth ring */}
            <mesh ref={gearRef} rotation={[Math.PI / 2, 0, 0]} scale={0.8}>
                <torusGeometry args={[1, 0.15, 4, 12]} />
                <meshBasicMaterial color="#E1B67A" wireframe transparent opacity={0.7} />
            </mesh>
            {/* Pipe cutouts */}
            {[[0.5, 0, 0.5], [-0.5, 0.3, 0.4], [0.3, -0.4, -0.5]].map((pos, i) => (
                <mesh key={i} position={pos as [number, number, number]} rotation={[Math.random(), Math.random(), 0]} scale={[0.15, 0.15, 0.5]}>
                    <cylinderGeometry args={[1, 1, 1, 6]} />
                    <meshBasicMaterial color="#5A3A24" wireframe transparent opacity={0.6} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 9 Drone: Pyramid with exposed truss edges and turbine
 */
export const Stage9Drone = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const turbineRef = useRef<THREE.Mesh>(null);
    const indicatorRefs = useRef<(THREE.Mesh | null)[]>([]);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.lookAt(0, 0, 0);
        ref.current.scale.setScalar(ease * 18);

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease * 0.9;
        }

        // Turbine spins rapidly
        if (turbineRef.current) {
            turbineRef.current.rotation.z += delta * 15;
        }

        // Edge lights blink like indicators
        indicatorRefs.current.forEach((ind, i) => {
            if (!ind || !(ind.material instanceof THREE.MeshBasicMaterial)) return;
            const blink = Math.sin(t * 8 + i * 2) > 0 ? 0.9 : 0.3;
            ind.material.opacity = blink;
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Main pyramid with truss */}
            <mesh rotation={[Math.PI, 0, 0]}>
                <coneGeometry args={[1, 2, 4]} />
                <meshBasicMaterial ref={bodyMatRef} color="#C97A2B" wireframe transparent opacity={0} />
            </mesh>
            {/* Exposed truss edges */}
            {[0, 1, 2, 3].map(i => {
                const angle = (i / 4) * Math.PI * 2 + Math.PI / 4;
                return (
                    <mesh
                        key={i}
                        ref={el => indicatorRefs.current[i] = el}
                        position={[Math.cos(angle) * 0.7, 0.5, Math.sin(angle) * 0.7]}
                        scale={[0.08, 0.08, 1.5]}
                    >
                        <boxGeometry args={[1, 1, 1]} />
                        <meshBasicMaterial color="#E1B67A" transparent opacity={0.3} />
                    </mesh>
                );
            })}
            {/* Turbine disk */}
            <mesh ref={turbineRef} position={[0, 1, 0]} rotation={[0, 0, 0]} scale={0.6}>
                <ringGeometry args={[0.3, 1, 6]} />
                <meshBasicMaterial color="#5A3A24" wireframe transparent opacity={0.7} side={THREE.DoubleSide} />
            </mesh>
        </group>
    );
};

/**
 * Stage 9 Fighter: Double-pyramid with hinged wing plates and axle
 */
export const Stage9Fighter = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const wingLeftRef = useRef<THREE.Mesh>(null);
    const wingRightRef = useRef<THREE.Mesh>(null);
    const axleRef = useRef<THREE.Mesh>(null);

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

        // Wings flap in short strokes
        const wingFlap = Math.sin(t * 4 + phase) * 0.2;
        if (wingLeftRef.current) wingLeftRef.current.rotation.z = -0.3 + wingFlap;
        if (wingRightRef.current) wingRightRef.current.rotation.z = 0.3 - wingFlap;

        // Axle rotates steadily
        if (axleRef.current) {
            axleRef.current.rotation.x += delta * 3;
        }
    });

    return (
        <group ref={ref} scale={0}>
            {/* Double-pyramid body */}
            <mesh rotation={[Math.PI / 2, 0, 0]} scale={[0.5, 1.4, 0.5]}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={bodyMatRef} color="#C97A2B" wireframe transparent opacity={0} />
            </mesh>
            {/* Hinged wing plates */}
            <mesh ref={wingLeftRef} position={[-1, 0, 0]} rotation={[0, 0, -0.3]} scale={[1, 0.1, 0.7]}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial color="#E1B67A" wireframe transparent opacity={0.7} />
            </mesh>
            <mesh ref={wingRightRef} position={[1, 0, 0]} rotation={[0, 0, 0.3]} scale={[1, 0.1, 0.7]}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial color="#E1B67A" wireframe transparent opacity={0.7} />
            </mesh>
            {/* Central axle */}
            <mesh ref={axleRef} rotation={[0, 0, Math.PI / 2]} scale={[0.15, 2.5, 0.15]}>
                <cylinderGeometry args={[1, 1, 1, 8]} />
                <meshBasicMaterial color="#5A3A24" wireframe transparent opacity={0.6} />
            </mesh>
            {/* Hinge joints */}
            <mesh position={[-0.5, 0, 0]} scale={0.2}>
                <sphereGeometry args={[1, 6, 6]} />
                <meshBasicMaterial color="#E1B67A" transparent opacity={0.8} />
            </mesh>
            <mesh position={[0.5, 0, 0]} scale={0.2}>
                <sphereGeometry args={[1, 6, 6]} />
                <meshBasicMaterial color="#E1B67A" transparent opacity={0.8} />
            </mesh>
        </group>
    );
};

/**
 * Stage 9 Elite: Reactor core with orbiting cog rings and piston struts
 */
export const Stage9Elite = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const cog1Ref = useRef<THREE.Mesh>(null);
    const cog2Ref = useRef<THREE.Mesh>(null);
    const pistonRefs = useRef<(THREE.Mesh | null)[]>([]);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.rotation.y += delta * 0.2;
        ref.current.scale.setScalar(ease * 36);

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease;
        }

        // Cog rings counter-rotate
        if (cog1Ref.current) cog1Ref.current.rotation.z += delta * 1.5;
        if (cog2Ref.current) cog2Ref.current.rotation.z -= delta * 2;

        // Pistons pump in sync
        pistonRefs.current.forEach((piston, i) => {
            if (!piston) return;
            const pump = Math.sin(t * 4 + i * Math.PI) * 0.3;
            piston.scale.y = 1 + pump;
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Reactor core */}
            <mesh>
                <icosahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={bodyMatRef} color="#C97A2B" wireframe transparent opacity={0} />
            </mesh>
            <mesh scale={0.6}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#E1B67A" wireframe transparent opacity={0.7} />
            </mesh>
            {/* Orbiting cog rings */}
            <mesh ref={cog1Ref} position={[0, 1.5, 0]} rotation={[Math.PI / 2, 0, 0]} scale={0.8}>
                <torusGeometry args={[1, 0.12, 4, 12]} />
                <meshBasicMaterial color="#5A3A24" wireframe transparent opacity={0.7} />
            </mesh>
            <mesh ref={cog2Ref} position={[0, -1.5, 0]} rotation={[Math.PI / 2, 0, 0]} scale={0.6}>
                <torusGeometry args={[1, 0.12, 4, 10]} />
                <meshBasicMaterial color="#5A3A24" wireframe transparent opacity={0.7} />
            </mesh>
            {/* Piston struts */}
            {[0, 1, 2, 3].map(i => {
                const angle = (i / 4) * Math.PI * 2;
                return (
                    <mesh
                        key={i}
                        ref={el => pistonRefs.current[i] = el}
                        position={[Math.cos(angle) * 1.5, 0, Math.sin(angle) * 1.5]}
                        scale={[0.15, 0.8, 0.15]}
                    >
                        <cylinderGeometry args={[1, 0.7, 1, 6]} />
                        <meshBasicMaterial color="#E1B67A" wireframe transparent opacity={0.6} />
                    </mesh>
                );
            })}
        </group>
    );
};

/**
 * Stage 9 Boss: Industrial cage with stacked gear halos and boiler core
 */
export const Stage9Boss = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const cageMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const gearRefs = useRef<(THREE.Mesh | null)[]>([]);
    const boilerMatRef = useRef<THREE.MeshBasicMaterial>(null);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.scale.setScalar(ease * 15);

        if (cageMatRef.current) {
            cageMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            cageMatRef.current.opacity = ease * 0.8;
        }

        // Gear halos rotate at varied speeds
        gearRefs.current.forEach((gear, i) => {
            if (!gear) return;
            gear.rotation.z += delta * (0.5 + i * 0.3) * (i % 2 === 0 ? 1 : -1);
        });

        // Boiler core pulses like pressure gauge
        if (boilerMatRef.current) {
            boilerMatRef.current.opacity = 0.5 + Math.sin(t * 3) * 0.3;
        }
    });

    return (
        <group ref={ref} scale={0}>
            {/* Industrial cage */}
            <mesh scale={[2.5, 3, 2.5]}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial ref={cageMatRef} color="#C97A2B" wireframe transparent opacity={0.8} />
            </mesh>
            {/* Stacked gear halos */}
            {[-1.5, 0, 1.5].map((y, i) => (
                <mesh
                    key={i}
                    ref={el => gearRefs.current[i] = el}
                    position={[0, y, 0]}
                    rotation={[Math.PI / 2, 0, 0]}
                    scale={2 - i * 0.3}
                >
                    <torusGeometry args={[1, 0.1, 4, 16]} />
                    <meshBasicMaterial color="#5A3A24" wireframe transparent opacity={0.7} />
                </mesh>
            ))}
            {/* Central boiler core */}
            <mesh scale={[1, 2, 1]}>
                <cylinderGeometry args={[1, 1, 1, 8]} />
                <meshBasicMaterial ref={boilerMatRef} color="#E1B67A" wireframe transparent opacity={0.5} />
            </mesh>
            {/* Pressure pipes */}
            {Array.from({ length: 4 }).map((_, i) => {
                const angle = (i / 4) * Math.PI * 2;
                return (
                    <mesh
                        key={i}
                        position={[Math.cos(angle) * 1.8, 0, Math.sin(angle) * 1.8]}
                        scale={[0.2, 2.5, 0.2]}
                    >
                        <cylinderGeometry args={[1, 1, 1, 6]} />
                        <meshBasicMaterial color="#5A3A24" wireframe transparent opacity={0.6} />
                    </mesh>
                );
            })}
            {/* Steam vents */}
            <mesh position={[0, 2, 0]} scale={0.5}>
                <coneGeometry args={[1, 0.5, 6]} />
                <meshBasicMaterial color="#E1B67A" transparent opacity={0.7} />
            </mesh>
        </group>
    );
};
