import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Enemy, getSpawnEase } from '../systems/EnemySystem';

// Stage 13: Shadow/Dark Matter themed - #000000, #480082, #8A2BE2
const getHealthColor = (hp: number, maxHp: number) => {
    const healthPct = hp / maxHp;
    if (healthPct > 0.5) return '#480082'; // Indigo
    if (healthPct > 0.25) return '#8A2BE2'; // BlueViolet
    return '#9400D3'; // DarkViolet
};

/**
 * Stage 13 Asteroid: Light-absorbing dodecahedron with shimmering violet edge
 */
export const Stage13Asteroid = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const mainMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const edgeMatRef = useRef<THREE.MeshBasicMaterial>(null);

    const rotSpeed = useMemo(() => ({
        x: 0.03 + Math.random() * 0.04,
        y: 0.04 + Math.random() * 0.05,
        z: 0.02 + Math.random() * 0.03
    }), []);

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
            // Random glitch flicker
            const glitch = Math.random() > 0.92;
            mainMatRef.current.opacity = ease * (glitch ? 0.5 : 0.95);
        }

        // Shimmering edge effect with color cycling
        if (edgeMatRef.current) {
            const glitch = Math.random() > 0.92;
            if (glitch) {
                edgeMatRef.current.color.set(['#480082', '#8A2BE2', '#9400D3'][Math.floor(Math.random() * 3)]);
            } else {
                edgeMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            }
            edgeMatRef.current.opacity = 0.3 + Math.sin(t * 2) * 0.2;
        }
    });

    return (
        <group ref={ref} scale={0}>
            {/* Dark core that absorbs light */}
            <mesh>
                <dodecahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={mainMatRef} color="#000000" transparent opacity={0} />
            </mesh>
            {/* Violet shimmer edge */}
            <mesh scale={1.05}>
                <dodecahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={edgeMatRef} color="#8A2BE2" wireframe transparent opacity={0.3} />
            </mesh>
        </group>
    );
};

/**
 * Stage 13 Drone: Pure black sphere surrounded by swirling violet particles
 */
export const Stage13Drone = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const particleGroupRef = useRef<THREE.Group>(null);
    const particleRefs = useRef<(THREE.Mesh | null)[]>([]);
    const trailRefs = useRef<(THREE.Mesh | null)[]>([]);
    const trailPositions = useRef<THREE.Vector3[]>([]);

    const particles = useMemo(() =>
        Array.from({ length: 12 }, () => ({
            dist: 0.8 + Math.random() * 0.4,
            speed: 1 + Math.random() * 2,
            offset: Math.random() * Math.PI * 2,
            yOffset: (Math.random() - 0.5) * 0.6
        })), []);

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
            bodyMatRef.current.opacity = ease * 0.98;
        }

        // Swirling particles
        if (particleGroupRef.current) {
            particleGroupRef.current.rotation.y += delta * 0.5;
        }

        particleRefs.current.forEach((p, i) => {
            if (!p) return;
            const angle = t * particles[i].speed + particles[i].offset;
            p.position.x = Math.cos(angle) * particles[i].dist;
            p.position.z = Math.sin(angle) * particles[i].dist;
            p.position.y = particles[i].yOffset + Math.sin(t * 2 + i) * 0.1;
            if (p.material instanceof THREE.MeshBasicMaterial) {
                p.material.opacity = 0.4 + Math.sin(t * 3 + i) * 0.3;
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
            {/* Pure black core */}
            <mesh>
                <sphereGeometry args={[0.5, 12, 8]} />
                <meshBasicMaterial ref={bodyMatRef} color="#000000" transparent opacity={0} />
            </mesh>
            {/* Swirling violet particles */}
            <group ref={particleGroupRef}>
                {particles.map((_, i) => (
                    <mesh
                        key={i}
                        ref={el => particleRefs.current[i] = el}
                        scale={0.06}
                    >
                        <sphereGeometry args={[1, 4, 4]} />
                        <meshBasicMaterial color="#8A2BE2" transparent opacity={0.5} />
                    </mesh>
                ))}
            </group>
            {/* Ghost trail */}
            {[0, 1, 2, 3, 4].map(i => (
                <mesh
                    key={`trail-${i}`}
                    ref={el => trailRefs.current[i] = el}
                    scale={0.3 - i * 0.04}
                >
                    <sphereGeometry args={[0.5, 10, 6]} />
                    <meshBasicMaterial color="#8A2BE2" transparent opacity={0.3} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 13 Fighter: Sharp intersecting black planes with glowing violet edges
 */
export const Stage13Fighter = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const planeRefs = useRef<(THREE.Mesh | null)[]>([]);

    const planes = useMemo(() => [
        { rot: [0, 0, 0], shift: 0 },
        { rot: [0, Math.PI / 3, 0], shift: 0.5 },
        { rot: [0, -Math.PI / 3, 0], shift: 1 }
    ], []);

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

        // Planes slowly shift and rearrange
        planeRefs.current.forEach((plane, i) => {
            if (!plane) return;
            plane.rotation.y = planes[i].rot[1] + Math.sin(t * 0.5 + planes[i].shift) * 0.2;
            if (plane.material instanceof THREE.MeshBasicMaterial) {
                plane.material.opacity = ease * (Math.random() > 0.1 ? 0.85 : 0.3);
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Intersecting shadow planes */}
            {planes.map((p, i) => (
                <mesh
                    key={i}
                    ref={el => planeRefs.current[i] = el}
                    rotation={p.rot as [number, number, number]}
                >
                    <planeGeometry args={[1.5, 2]} />
                    <meshBasicMaterial color="#000000" transparent opacity={0.9} side={THREE.DoubleSide} />
                </mesh>
            ))}
            {/* Violet edge glow */}
            <mesh scale={1.1}>
                <octahedronGeometry args={[0.8, 0]} />
                <meshBasicMaterial color="#8A2BE2" wireframe transparent opacity={0.4} />
            </mesh>
        </group>
    );
};

/**
 * Stage 13 Elite: Black sphere with rotating accretion disk pulling in light
 */
export const Stage13Elite = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const coreMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const diskRef = useRef<THREE.Mesh>(null);
    const diskMatRef = useRef<THREE.MeshBasicMaterial>(null);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.scale.setScalar(ease * 36);

        if (coreMatRef.current) {
            coreMatRef.current.opacity = ease * 0.98;
        }

        // Rotating accretion disk
        if (diskRef.current) {
            diskRef.current.rotation.z += delta * 1.5;
        }

        if (diskMatRef.current) {
            diskMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            diskMatRef.current.opacity = 0.5 + Math.sin(t * 2) * 0.2;
        }
    });

    return (
        <group ref={ref} scale={0}>
            {/* Central black hole */}
            <mesh>
                <sphereGeometry args={[0.8, 16, 12]} />
                <meshBasicMaterial ref={coreMatRef} color="#000000" transparent opacity={0} />
            </mesh>
            {/* Event horizon glow */}
            <mesh scale={0.85}>
                <sphereGeometry args={[1, 12, 8]} />
                <meshBasicMaterial color="#480082" transparent opacity={0.3} />
            </mesh>
            {/* Accretion disk */}
            <mesh ref={diskRef} rotation={[Math.PI / 2, 0, 0]}>
                <ringGeometry args={[1.2, 2.2, 32]} />
                <meshBasicMaterial ref={diskMatRef} color="#8A2BE2" transparent opacity={0.5} side={THREE.DoubleSide} />
            </mesh>
        </group>
    );
};

/**
 * Stage 13 Boss: Colossal amorphous shadow cloud with glowing violet eye and tendrils
 */
export const Stage13Boss = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const cloudMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const eyeMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const tendrilRefs = useRef<(THREE.Group | null)[]>([]);

    const tendrils = useMemo(() =>
        Array.from({ length: 6 }, (_, i) => ({
            angle: (i / 6) * Math.PI * 2,
            length: 3,
            segments: 4
        })), []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.scale.setScalar(ease * 15);

        if (cloudMatRef.current) {
            cloudMatRef.current.opacity = ease * 0.85;
        }

        // Eye blinks
        if (eyeMatRef.current) {
            const blink = Math.sin(t * 0.5) > 0.9 ? 0.2 : 1;
            eyeMatRef.current.opacity = 0.9 * blink;
        }

        // Tendrils lash out
        tendrilRefs.current.forEach((tendril, i) => {
            if (!tendril) return;
            tendril.rotation.x = Math.sin(t * 2 + i) * 0.3;
            tendril.rotation.z = Math.cos(t * 1.5 + i) * 0.2;
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Amorphous shadow cloud */}
            <mesh scale={3}>
                <icosahedronGeometry args={[1, 1]} />
                <meshBasicMaterial ref={cloudMatRef} color="#000000" transparent opacity={0.85} />
            </mesh>
            <mesh scale={2.8}>
                <dodecahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#480082" wireframe transparent opacity={0.3} />
            </mesh>
            {/* Glowing violet eye */}
            <mesh position={[0, 0, 2]} scale={0.8}>
                <sphereGeometry args={[1, 12, 8]} />
                <meshBasicMaterial ref={eyeMatRef} color="#8A2BE2" transparent opacity={0.9} />
            </mesh>
            <mesh position={[0, 0, 2.3]} scale={0.3}>
                <sphereGeometry args={[1, 8, 6]} />
                <meshBasicMaterial color="#000000" transparent opacity={0.95} />
            </mesh>
            {/* Shadow tendrils */}
            {tendrils.map((t, i) => (
                <group
                    key={i}
                    ref={el => tendrilRefs.current[i] = el}
                    position={[
                        Math.cos(t.angle) * 2,
                        Math.sin(t.angle) * 2,
                        -1
                    ]}
                    rotation={[0, 0, t.angle]}
                >
                    {Array.from({ length: t.segments }).map((_, j) => (
                        <mesh key={j} position={[0, 0, -j * 0.8]} scale={[0.3 - j * 0.05, 0.3 - j * 0.05, 0.8]}>
                            <cylinderGeometry args={[1, 0.7, 1, 6]} />
                            <meshBasicMaterial color="#480082" transparent opacity={0.7 - j * 0.1} />
                        </mesh>
                    ))}
                </group>
            ))}
        </group>
    );
};
