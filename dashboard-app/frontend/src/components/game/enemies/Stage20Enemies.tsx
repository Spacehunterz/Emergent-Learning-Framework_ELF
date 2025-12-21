import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Enemy, getSpawnEase } from '../systems/EnemySystem';

// Stage 20: Demonic/Hellfire themed - #FF0000, #000000, #FFA500
const getHealthColor = (hp: number, maxHp: number) => {
    const healthPct = hp / maxHp;
    if (healthPct > 0.5) return '#FF0000'; // Red
    if (healthPct > 0.25) return '#FFA500'; // Orange
    return '#FF4500'; // OrangeRed (dying flames)
};

/**
 * Stage 20 Asteroid: Violent charred rock with hellfire color cycling and explosive ember fragments
 */
export const Stage20Asteroid = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const rockMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const crackMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const emberRefs = useRef<(THREE.Mesh | null)[]>([]);

    const rotSpeed = useMemo(() => ({
        x: 0.06 + Math.random() * 0.08,
        y: 0.07 + Math.random() * 0.09,
        z: 0.05 + Math.random() * 0.07
    }), []);

    const embers = useMemo(() =>
        Array.from({ length: 12 }, () => ({
            basePos: new THREE.Vector3(
                (Math.random() - 0.5) * 2,
                (Math.random() - 0.5) * 2,
                (Math.random() - 0.5) * 2
            ).normalize().multiplyScalar(1.2),
            speed: 0.8 + Math.random() * 0.7,
            phase: Math.random() * Math.PI * 2
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

        // INTENSE screen-shake position jitter
        if (Math.random() > 0.92) {
            ref.current.position.x += (Math.random() - 0.5) * 8;
            ref.current.position.y += (Math.random() - 0.5) * 8;
        }

        // INFERNAL SHAKE - violent scale spikes for explosion effect
        const rageScale = Math.random() > 0.95 ? 1.3 : 1.0;
        ref.current.scale.multiplyScalar(rageScale);

        if (rockMatRef.current) {
            // Hellfire color cycling
            const glitch = Math.random() > 0.88;
            if (glitch) {
                rockMatRef.current.color.set(['#FF0000', '#000000', '#FFA500'][Math.floor(Math.random() * 3)]);
            } else {
                rockMatRef.current.color.set('#000000');
            }
            // Demonic flicker - violent opacity pulse
            rockMatRef.current.opacity = ease * (glitch ? 0.3 : 0.95);
        }

        // Cracks glow with pulsing hellfire
        if (crackMatRef.current) {
            const glitch = Math.random() > 0.88;
            if (glitch) {
                crackMatRef.current.color.set(['#FF0000', '#FFA500', '#000000'][Math.floor(Math.random() * 3)]);
            } else {
                crackMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            }
            crackMatRef.current.opacity = 0.5 + Math.sin(t * 8) * 0.4;
        }

        // Fragment jitter - flame fragments crackle violently
        emberRefs.current.forEach((ember, i) => {
            if (!ember) return;
            const e = embers[i];
            ember.position.copy(e.basePos);
            ember.position.y += ((t * e.speed + e.phase) % 2) * 0.5;

            // VIOLENT JITTER
            if (Math.random() > 0.85) {
                ember.position.x += (Math.random() - 0.5) * 0.4;
                ember.position.y += (Math.random() - 0.5) * 0.4;
                ember.position.z += (Math.random() - 0.5) * 0.4;
            }

            if (ember.material instanceof THREE.MeshBasicMaterial) {
                ember.material.opacity = 0.9 - ((t * e.speed + e.phase) % 2) * 0.5;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Charred black rock */}
            <mesh>
                <icosahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={rockMatRef} color="#000000" transparent opacity={0} />
            </mesh>
            {/* Glowing red cracks */}
            <mesh scale={0.95}>
                <icosahedronGeometry args={[1, 1]} />
                <meshBasicMaterial ref={crackMatRef} color="#FF0000" wireframe transparent opacity={0.5} />
            </mesh>
            {/* Explosive drifting embers */}
            {embers.map((e, i) => (
                <mesh
                    key={i}
                    ref={el => emberRefs.current[i] = el}
                    position={e.basePos.toArray()}
                    scale={0.06}
                >
                    <sphereGeometry args={[1, 4, 4]} />
                    <meshBasicMaterial color="#FFA500" transparent opacity={0.8} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 20 Drone: Demonic sphere with hellfire glitch effects and violent eye pulsing
 */
export const Stage20Drone = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const eyeMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const hornRefs = useRef<(THREE.Mesh | null)[]>([]);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.lookAt(0, 0, 0);
        ref.current.scale.setScalar(ease * 18);

        // AGGRESSIVE jerky movement
        if (Math.random() > 0.90) {
            ref.current.position.x += (Math.random() - 0.5) * 5;
            ref.current.position.y += (Math.random() - 0.5) * 5;
        }

        // INFERNAL SHAKE
        const rageScale = Math.random() > 0.93 ? 1.4 : 1.0;
        ref.current.scale.multiplyScalar(rageScale);

        if (bodyMatRef.current) {
            // Hellfire color cycling
            const glitch = Math.random() > 0.88;
            if (glitch) {
                bodyMatRef.current.color.set(['#FF0000', '#000000', '#FFA500'][Math.floor(Math.random() * 3)]);
            } else {
                bodyMatRef.current.color.set('#000000');
            }
            // Demonic flicker
            bodyMatRef.current.opacity = ease * (glitch ? 0.2 : 0.95);
        }

        // Eye VIOLENTLY blinks and pulses with rage
        if (eyeMatRef.current) {
            const glitch = Math.random() > 0.88;
            const blink = Math.sin(t * 1.2) > 0.92 ? 0.1 : 1;
            if (glitch) {
                eyeMatRef.current.color.set(['#FF0000', '#000000', '#FFA500'][Math.floor(Math.random() * 3)]);
            } else {
                eyeMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            }
            eyeMatRef.current.opacity = (glitch ? 0.3 : 0.95) * blink;
        }

        // Horns jitter with infernal energy
        hornRefs.current.forEach((horn) => {
            if (!horn) return;
            if (Math.random() > 0.88) {
                horn.position.x += (Math.random() - 0.5) * 0.15;
                horn.position.y += (Math.random() - 0.5) * 0.15;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Black demonic sphere */}
            <mesh>
                <sphereGeometry args={[0.6, 10, 8]} />
                <meshBasicMaterial ref={bodyMatRef} color="#000000" transparent opacity={0} />
            </mesh>
            {/* Red horns */}
            <mesh ref={el => hornRefs.current[0] = el} position={[-0.3, 0.5, 0]} rotation={[0, 0, 0.3]}>
                <coneGeometry args={[0.1, 0.5, 6]} />
                <meshBasicMaterial color="#FF0000" transparent opacity={0.9} />
            </mesh>
            <mesh ref={el => hornRefs.current[1] = el} position={[0.3, 0.5, 0]} rotation={[0, 0, -0.3]}>
                <coneGeometry args={[0.1, 0.5, 6]} />
                <meshBasicMaterial color="#FF0000" transparent opacity={0.9} />
            </mesh>
            {/* Single glowing eye */}
            <mesh position={[0, 0, 0.5]} scale={0.2}>
                <sphereGeometry args={[1, 8, 6]} />
                <meshBasicMaterial ref={eyeMatRef} color="#FF0000" transparent opacity={0.9} />
            </mesh>
        </group>
    );
};

/**
 * Stage 20 Fighter: Hellfire bat with violent glitching wings and explosive ember trail
 */
export const Stage20Fighter = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const wingLeftRef = useRef<THREE.Mesh>(null);
    const wingRightRef = useRef<THREE.Mesh>(null);
    const emberRefs = useRef<(THREE.Mesh | null)[]>([]);
    const veinRefs = useRef<(THREE.Mesh | null)[]>([]);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const phase = data.seed * Math.PI * 2;
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.lookAt(0, 0, 0);
        ref.current.scale.setScalar(ease * 24);

        // AGGRESSIVE flicker - more visible but unstable
        const visible = Math.sin(t * 25) > -0.9;
        ref.current.visible = visible;

        // VIOLENT position shake
        if (Math.random() > 0.90) {
            ref.current.position.x += (Math.random() - 0.5) * 6;
            ref.current.position.y += (Math.random() - 0.5) * 6;
        }

        // INFERNAL SHAKE
        const rageScale = Math.random() > 0.93 ? 1.35 : 1.0;
        ref.current.scale.multiplyScalar(rageScale);

        if (bodyMatRef.current) {
            // Hellfire color cycling
            const glitch = Math.random() > 0.88;
            if (glitch) {
                bodyMatRef.current.color.set(['#FF0000', '#000000', '#FFA500'][Math.floor(Math.random() * 3)]);
            } else {
                bodyMatRef.current.color.set('#000000');
            }
            bodyMatRef.current.opacity = ease * (glitch ? 0.3 : 0.95);
        }

        // VIOLENT wing flapping with glitch
        const flapAngle = Math.sin(t * 8 + phase) * 0.7;
        const wingGlitch = Math.random() > 0.88 ? (Math.random() - 0.5) * 0.5 : 0;
        if (wingLeftRef.current) wingLeftRef.current.rotation.z = 0.3 + flapAngle + wingGlitch;
        if (wingRightRef.current) wingRightRef.current.rotation.z = -0.3 - flapAngle - wingGlitch;

        // Veins pulse with hellfire
        veinRefs.current.forEach((vein) => {
            if (!vein) return;
            if (vein.material instanceof THREE.MeshBasicMaterial) {
                const glitch = Math.random() > 0.88;
                if (glitch) {
                    vein.material.color.set(['#FF0000', '#FFA500'][Math.floor(Math.random() * 2)]);
                }
                vein.material.opacity = 0.7 + Math.sin(t * 10) * 0.3;
            }
        });

        // Explosive ember trail with violent jitter
        emberRefs.current.forEach((ember, i) => {
            if (!ember) return;
            ember.position.z = 0.5 + i * 0.3;
            ember.position.x = Math.sin(t * 5 + i) * 0.2;

            // VIOLENT JITTER
            if (Math.random() > 0.85) {
                ember.position.x += (Math.random() - 0.5) * 0.3;
                ember.position.y += (Math.random() - 0.5) * 0.3;
            }

            if (ember.material instanceof THREE.MeshBasicMaterial) {
                ember.material.opacity = 0.8 - i * 0.15;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Angular black bat body */}
            <mesh scale={[0.5, 0.3, 0.8]}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={bodyMatRef} color="#000000" transparent opacity={0} />
            </mesh>
            {/* Leathery wings with red veins */}
            <mesh ref={wingLeftRef} position={[-0.6, 0, 0]} rotation={[0, 0, 0.3]}>
                <planeGeometry args={[1.5, 0.8]} />
                <meshBasicMaterial color="#1a0000" transparent opacity={0.9} side={THREE.DoubleSide} />
            </mesh>
            <mesh ref={wingRightRef} position={[0.6, 0, 0]} rotation={[0, 0, -0.3]}>
                <planeGeometry args={[1.5, 0.8]} />
                <meshBasicMaterial color="#1a0000" transparent opacity={0.9} side={THREE.DoubleSide} />
            </mesh>
            {/* Red vein lines on wings */}
            <mesh ref={el => veinRefs.current[0] = el} position={[-0.8, 0, 0.01]} rotation={[0, 0, 0.3]} scale={[1.3, 0.02, 1]}>
                <planeGeometry args={[1, 1]} />
                <meshBasicMaterial color="#FF0000" transparent opacity={0.7} side={THREE.DoubleSide} />
            </mesh>
            <mesh ref={el => veinRefs.current[1] = el} position={[0.8, 0, 0.01]} rotation={[0, 0, -0.3]} scale={[1.3, 0.02, 1]}>
                <planeGeometry args={[1, 1]} />
                <meshBasicMaterial color="#FF0000" transparent opacity={0.7} side={THREE.DoubleSide} />
            </mesh>
            {/* Explosive ember trail */}
            {[0, 1, 2, 3, 4].map(i => (
                <mesh key={i} ref={el => emberRefs.current[i] = el} position={[0, 0, 0.5 + i * 0.3]} scale={0.1}>
                    <sphereGeometry args={[1, 4, 4]} />
                    <meshBasicMaterial color="#FFA500" transparent opacity={0.6} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 20 Elite: Demon skull with violent hellfire glitches and raging eye streams
 */
export const Stage20Elite = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const skullMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const eyeFireRefs = useRef<(THREE.Mesh | null)[]>([]);
    const hornMatRefs = useRef<(THREE.MeshBasicMaterial | null)[]>([]);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.rotation.y = Math.sin(t * 0.8) * 0.3; // Aggressive swaying
        ref.current.scale.setScalar(ease * 36);

        // VIOLENT teleport
        if (Math.random() > 0.94) {
            ref.current.position.x += (Math.random() - 0.5) * 10;
            ref.current.position.y += (Math.random() - 0.5) * 10;
        }

        // INFERNAL SHAKE
        const rageScale = Math.random() > 0.92 ? 1.45 : 1.0;
        ref.current.scale.multiplyScalar(rageScale);

        if (skullMatRef.current) {
            // Rapid hellfire color cycling
            const glitch = Math.random() > 0.88;
            if (glitch) {
                skullMatRef.current.color.set(['#FF0000', '#000000', '#FFA500'][Math.floor(Math.random() * 3)]);
            } else {
                const phase = Math.floor(t * 10) % 3;
                skullMatRef.current.color.set(['#000000', '#1a0000', '#0a0000'][phase]);
            }
            // VIOLENT opacity flicker
            skullMatRef.current.opacity = ease * (glitch ? 0.2 : 0.95);
        }

        // Horns pulse with violent infernal energy
        hornMatRefs.current.forEach((mat) => {
            if (!mat) return;
            const glitch = Math.random() > 0.88;
            if (glitch) {
                mat.color.set(['#FF0000', '#FFA500', '#000000'][Math.floor(Math.random() * 3)]);
            } else {
                mat.color.set(getHealthColor(data.hp, data.maxHp));
            }
            mat.opacity = 0.6 + Math.sin(t * 6) * 0.35;
        });

        // RAGING fire streams from eye sockets
        eyeFireRefs.current.forEach((fire, i) => {
            if (!fire) return;
            fire.scale.y = 0.5 + Math.sin(t * 12 + i) * 0.4;

            // VIOLENT JITTER
            if (Math.random() > 0.85) {
                fire.position.x += (Math.random() - 0.5) * 0.2;
                fire.position.y += (Math.random() - 0.5) * 0.2;
            }

            if (fire.material instanceof THREE.MeshBasicMaterial) {
                const glitch = Math.random() > 0.88;
                if (glitch) {
                    fire.material.color.set(['#FF0000', '#FFA500'][Math.floor(Math.random() * 2)]);
                }
                fire.material.opacity = 0.7 + Math.sin(t * 10 + i) * 0.3;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Black skull (approximated with modified sphere) */}
            <mesh scale={[1, 1.2, 0.8]}>
                <sphereGeometry args={[1, 10, 8]} />
                <meshBasicMaterial ref={skullMatRef} color="#000000" transparent opacity={0} />
            </mesh>
            {/* Jaw */}
            <mesh position={[0, -0.7, 0.3]} scale={[0.6, 0.3, 0.4]}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial color="#0a0a0a" transparent opacity={0.9} />
            </mesh>
            {/* Eye sockets (dark) */}
            <mesh position={[-0.35, 0.2, 0.7]} scale={0.25}>
                <sphereGeometry args={[1, 6, 4]} />
                <meshBasicMaterial color="#1a0000" transparent opacity={0.95} />
            </mesh>
            <mesh position={[0.35, 0.2, 0.7]} scale={0.25}>
                <sphereGeometry args={[1, 6, 4]} />
                <meshBasicMaterial color="#1a0000" transparent opacity={0.95} />
            </mesh>
            {/* RAGING fire streaming from eyes */}
            <mesh ref={el => eyeFireRefs.current[0] = el} position={[-0.35, 0.2, 0.85]} scale={[0.15, 0.6, 0.1]}>
                <coneGeometry args={[1, 1, 6]} />
                <meshBasicMaterial color="#FF0000" transparent opacity={0.8} />
            </mesh>
            <mesh ref={el => eyeFireRefs.current[1] = el} position={[0.35, 0.2, 0.85]} scale={[0.15, 0.6, 0.1]}>
                <coneGeometry args={[1, 1, 6]} />
                <meshBasicMaterial color="#FF0000" transparent opacity={0.8} />
            </mesh>
            {/* Large twisted horns */}
            <mesh position={[-0.6, 0.8, 0]} rotation={[0, 0, 0.4]}>
                <coneGeometry args={[0.15, 1.2, 6]} />
                <meshBasicMaterial ref={el => hornMatRefs.current[0] = el} color="#FF0000" transparent opacity={0.8} />
            </mesh>
            <mesh position={[0.6, 0.8, 0]} rotation={[0, 0, -0.4]}>
                <coneGeometry args={[0.15, 1.2, 6]} />
                <meshBasicMaterial ref={el => hornMatRefs.current[1] = el} color="#FF0000" transparent opacity={0.8} />
            </mesh>
        </group>
    );
};

/**
 * Stage 20 Boss: TERRIFYING demon lord with apocalyptic hellfire glitch effects
 */
export const Stage20Boss = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const axeRef = useRef<THREE.Group>(null);
    const flameRefs = useRef<(THREE.Mesh | null)[]>([]);
    const bodyPartRefs = useRef<(THREE.Mesh | null)[]>([]);

    const flames = useMemo(() =>
        Array.from({ length: 20 }, () => ({
            basePos: new THREE.Vector3(
                (Math.random() - 0.5) * 8,
                -3 + Math.random() * 8,
                (Math.random() - 0.5) * 5
            ),
            speed: 1.5 + Math.random() * 2.5,
            phase: Math.random() * Math.PI * 2
        })), []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.scale.setScalar(ease * 15);

        // APOCALYPTIC teleport
        if (Math.random() > 0.95) {
            ref.current.position.x += (Math.random() - 0.5) * 15;
            ref.current.position.y += (Math.random() - 0.5) * 15;
        }

        // MASSIVE INFERNAL SHAKE
        const rageScale = Math.random() > 0.90 ? 1.5 : 1.0;
        ref.current.scale.multiplyScalar(rageScale);

        if (bodyMatRef.current) {
            // Violent hellfire cycling
            const glitch = Math.random() > 0.85;
            if (glitch) {
                bodyMatRef.current.color.set(['#FF0000', '#000000', '#FFA500'][Math.floor(Math.random() * 3)]);
            } else {
                bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            }
            bodyMatRef.current.opacity = ease * (glitch ? 0.3 : 0.95);
        }

        // Body parts glitch violently
        bodyPartRefs.current.forEach((part) => {
            if (!part) return;
            if (Math.random() > 0.87) {
                part.position.x += (Math.random() - 0.5) * 0.6;
                part.position.y += (Math.random() - 0.5) * 0.6;
            }
            if (part.material instanceof THREE.MeshBasicMaterial) {
                const glitch = Math.random() > 0.87;
                if (glitch) {
                    part.material.color.set(['#FF0000', '#8B0000', '#FFA500'][Math.floor(Math.random() * 3)]);
                    part.material.opacity = 0.3;
                } else {
                    part.material.opacity = 0.95;
                }
            }
        });

        // Axe swings with VIOLENT glitch
        if (axeRef.current) {
            axeRef.current.rotation.z = Math.sin(t * 1.5) * 0.5;
            if (Math.random() > 0.90) {
                axeRef.current.rotation.z += (Math.random() - 0.5) * 0.8;
            }
        }

        // APOCALYPTIC flames wreath the demon
        flameRefs.current.forEach((flame, i) => {
            if (!flame) return;
            const f = flames[i];
            flame.position.y = f.basePos.y + ((t * f.speed + f.phase) % 4);
            flame.position.x = f.basePos.x + Math.sin(t * 2 + f.phase) * 0.5;

            // VIOLENT JITTER
            if (Math.random() > 0.82) {
                flame.position.x += (Math.random() - 0.5) * 0.5;
                flame.position.y += (Math.random() - 0.5) * 0.5;
                flame.position.z += (Math.random() - 0.5) * 0.5;
            }

            if (flame.material instanceof THREE.MeshBasicMaterial) {
                const cycle = ((t * f.speed + f.phase) % 4) / 4;
                const glitch = Math.random() > 0.87;
                if (glitch) {
                    flame.material.color.set(['#FF0000', '#FFA500'][Math.floor(Math.random() * 2)]);
                }
                flame.material.opacity = 0.9 - cycle * 0.7;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Massive muscular torso */}
            <mesh ref={el => bodyPartRefs.current[0] = el} scale={[2, 2.5, 1.5]}>
                <sphereGeometry args={[1, 10, 8]} />
                <meshBasicMaterial ref={bodyMatRef} color="#FF0000" transparent opacity={0} />
            </mesh>
            {/* Head */}
            <mesh ref={el => bodyPartRefs.current[1] = el} position={[0, 2.5, 0]} scale={0.8}>
                <sphereGeometry args={[1, 8, 6]} />
                <meshBasicMaterial color="#8B0000" transparent opacity={0.95} />
            </mesh>
            {/* Large obsidian horns */}
            <mesh ref={el => bodyPartRefs.current[2] = el} position={[-0.6, 3, 0]} rotation={[0, 0, 0.5]}>
                <coneGeometry args={[0.2, 1.5, 6]} />
                <meshBasicMaterial color="#000000" transparent opacity={0.95} />
            </mesh>
            <mesh ref={el => bodyPartRefs.current[3] = el} position={[0.6, 3, 0]} rotation={[0, 0, -0.5]}>
                <coneGeometry args={[0.2, 1.5, 6]} />
                <meshBasicMaterial color="#000000" transparent opacity={0.95} />
            </mesh>
            {/* Glowing eyes */}
            <mesh position={[-0.3, 2.6, 0.6]} scale={0.15}>
                <sphereGeometry args={[1, 6, 4]} />
                <meshBasicMaterial color="#FFA500" transparent opacity={0.9} />
            </mesh>
            <mesh position={[0.3, 2.6, 0.6]} scale={0.15}>
                <sphereGeometry args={[1, 6, 4]} />
                <meshBasicMaterial color="#FFA500" transparent opacity={0.9} />
            </mesh>
            {/* Arms */}
            <mesh ref={el => bodyPartRefs.current[4] = el} position={[-2.2, 1, 0]} rotation={[0, 0, 0.5]} scale={[0.5, 2, 0.5]}>
                <capsuleGeometry args={[1, 1, 4, 8]} />
                <meshBasicMaterial color="#8B0000" transparent opacity={0.9} />
            </mesh>
            <mesh ref={el => bodyPartRefs.current[5] = el} position={[2.2, 1, 0]} rotation={[0, 0, -0.5]} scale={[0.5, 2, 0.5]}>
                <capsuleGeometry args={[1, 1, 4, 8]} />
                <meshBasicMaterial color="#8B0000" transparent opacity={0.9} />
            </mesh>
            {/* Flaming axe in right hand */}
            <group ref={axeRef} position={[3, 0, 0]}>
                {/* Axe handle */}
                <mesh rotation={[0, 0, Math.PI / 4]} scale={[0.15, 2.5, 0.15]}>
                    <cylinderGeometry args={[1, 1, 1, 6]} />
                    <meshBasicMaterial color="#3d2817" transparent opacity={0.9} />
                </mesh>
                {/* Axe blade */}
                <mesh position={[0.8, 1.2, 0]} rotation={[0, 0, Math.PI / 4]} scale={[1.2, 0.8, 0.1]}>
                    <boxGeometry args={[1, 1, 1]} />
                    <meshBasicMaterial color="#FFA500" transparent opacity={0.85} />
                </mesh>
                {/* Flame on blade */}
                <mesh position={[1.2, 1.5, 0]} scale={[0.3, 0.8, 0.2]}>
                    <coneGeometry args={[1, 1, 6]} />
                    <meshBasicMaterial color="#FF4500" transparent opacity={0.7} />
                </mesh>
            </group>
            {/* APOCALYPTIC wreathing flames */}
            {flames.map((f, i) => (
                <mesh
                    key={i}
                    ref={el => flameRefs.current[i] = el}
                    position={f.basePos.toArray()}
                    scale={0.25}
                >
                    <coneGeometry args={[0.5, 1, 6]} />
                    <meshBasicMaterial color={i % 2 === 0 ? '#FF0000' : '#FFA500'} transparent opacity={0.7} />
                </mesh>
            ))}
        </group>
    );
};
