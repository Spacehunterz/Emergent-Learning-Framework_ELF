import React, { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { useEnemyStore } from '../systems/EnemySystem'

const TEMP_OBJ = new THREE.Object3D()
const TEMP_COLOR = new THREE.Color()

export const InstancedEnemyRenderer = () => {
    // Refs for Mesh
    const droneWireRef = useRef<THREE.InstancedMesh>(null)
    const coreRef = useRef<THREE.InstancedMesh>(null)
    const scoutRef = useRef<THREE.InstancedMesh>(null)

    // New Enemy Refs
    const heavyRef = useRef<THREE.InstancedMesh>(null)   // Box
    const speederRef = useRef<THREE.InstancedMesh>(null) // Tetrahedron
    const chargerRef = useRef<THREE.InstancedMesh>(null) // Icosahedron
    const sniperRef = useRef<THREE.InstancedMesh>(null)  // Cylinder
    const swarmerRef = useRef<THREE.InstancedMesh>(null) // Sphere (Tiny)
    const orbitRef = useRef<THREE.InstancedMesh>(null)   // Torus
    const titanRef = useRef<THREE.InstancedMesh>(null)   // Dodecahedron

    // Refs for Attributes
    const droneDeathAttr = useRef<THREE.InstancedBufferAttribute>(null)
    const coreDeathAttr = useRef<THREE.InstancedBufferAttribute>(null)
    const scoutDeathAttr = useRef<THREE.InstancedBufferAttribute>(null)

    // New Death Attrs
    const heavyDeathAttr = useRef<THREE.InstancedBufferAttribute>(null)
    const speederDeathAttr = useRef<THREE.InstancedBufferAttribute>(null)
    const chargerDeathAttr = useRef<THREE.InstancedBufferAttribute>(null)
    const sniperDeathAttr = useRef<THREE.InstancedBufferAttribute>(null)
    const swarmerDeathAttr = useRef<THREE.InstancedBufferAttribute>(null)
    const orbitDeathAttr = useRef<THREE.InstancedBufferAttribute>(null)
    const titanDeathAttr = useRef<THREE.InstancedBufferAttribute>(null)

    // --- CUSTOM MATERIALS ---
    // 1. Wireframe "Shatter" Material
    const wireMaterial = useMemo(() => {
        const mat = new THREE.MeshBasicMaterial({
            color: 0xffffff,
            wireframe: true,
            toneMapped: false
        })

        mat.onBeforeCompile = (shader) => {
            shader.vertexShader = `
                attribute float aDeath;
                varying float vDeath;
                ${shader.vertexShader}
            `.replace(
                '#include <begin_vertex>',
                `
                #include <begin_vertex>
                vDeath = aDeath;
                
                // Shatter / Explode Effect
                // Move vertex along normal based on death progress
                // Add some random noise based on position to make it jagged
                float noise = sin(position.x * 12.0) * cos(position.y * 15.0) * sin(position.z * 18.0);
                vec3 explosion = normal * (aDeath * 8.0) + vec3(noise) * (aDeath * 4.0);
                
                if (aDeath > 0.0) {
                   transformed += explosion;
                }
                `
            )

            shader.fragmentShader = `
                varying float vDeath;
                ${shader.fragmentShader}
            `.replace(
                '#include <dithering_fragment>',
                `
                #include <dithering_fragment>
                // Fade out
                // Wireframe doesn't dissolve well with noise, so just fade opacity
                if (vDeath > 0.0) {
                     gl_FragColor.a *= (1.0 - vDeath);
                     // If fully dead, discard to prevent z-fighting artifacts
                     if (vDeath >= 0.95) discard;
                }
                `
            )
        }
        // Enable transparency for fade
        mat.transparent = true
        return mat
    }, [])

    // 2. Core "Pixel Dissolve" Material
    const coreMaterial = useMemo(() => {
        const mat = new THREE.MeshBasicMaterial({
            color: 0xffffff,
            toneMapped: false,
            transparent: true,
            opacity: 0.6
        })

        mat.onBeforeCompile = (shader) => {
            shader.vertexShader = `
                attribute float aDeath;
                varying float vDeath;
                varying vec3 vPos;
                ${shader.vertexShader}
            `.replace(
                '#include <begin_vertex>',
                `
                #include <begin_vertex>
                vDeath = aDeath;
                vPos = position;
                // Slight expansion
                if (aDeath > 0.0) {
                    transformed *= (1.0 + aDeath * 2.0);
                }
                `
            )

            shader.fragmentShader = `
                varying float vDeath;
                varying vec3 vPos;
                
                // Simple pseudo-random hash
                float hash(vec2 p) {
                    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
                }

                ${shader.fragmentShader}
            `.replace(
                '#include <dithering_fragment>',
                `
                #include <dithering_fragment>
                
                if (vDeath > 0.0) {
                    // Pixel Dissolve
                    // Map world pos to "pixels"
                    float pixelSize = 0.2; // Size of "pixel" blocks
                    vec2 pixelUV = floor(vPos.xy / pixelSize);
                    float noise = hash(pixelUV);
                    
                    if (noise < vDeath) discard;
                    
                    // Flash white at start of death
                    if (vDeath < 0.2) {
                        gl_FragColor.rgb += vec3(0.5);
                    }
                }
                `
            )
        }
        return mat
    }, [])

    // 3. Scout Material (Re-use Wireframe for now, maybe custom later)
    const scoutMaterial = wireMaterial // Reuse shatter effect
    const genericMaterial = wireMaterial // Reuse for all logic

    useFrame((state) => {
        // ZUSTAND STORE ACCESS (Mutable state, no re-render)
        // Access via getState() to avoid React diffing every frame
        const enemies = useEnemyStore.getState().enemies
        const time = state.clock.getElapsedTime()

        let droneCount = 0
        let scoutCount = 0
        let heavyCount = 0
        let speederCount = 0
        let chargerCount = 0
        let sniperCount = 0
        let swarmerCount = 0
        let orbitCount = 0
        let titanCount = 0

        // We must update the attribute array directly
        const droneDeathArray = droneDeathAttr.current?.array as Float32Array
        const coreDeathArray = coreDeathAttr.current?.array as Float32Array
        const scoutDeathArray = scoutDeathAttr.current?.array as Float32Array

        const heavyDeathArray = heavyDeathAttr.current?.array as Float32Array
        const speederDeathArray = speederDeathAttr.current?.array as Float32Array
        const chargerDeathArray = chargerDeathAttr.current?.array as Float32Array
        const sniperDeathArray = sniperDeathAttr.current?.array as Float32Array
        const swarmerDeathArray = swarmerDeathAttr.current?.array as Float32Array
        const orbitDeathArray = orbitDeathAttr.current?.array as Float32Array
        const titanDeathArray = titanDeathAttr.current?.array as Float32Array

        // Helper to update generic mesh
        const updateMesh = (
            mesh: THREE.InstancedMesh | null,
            deathArray: Float32Array | undefined,
            idx: number,
            scaleMult: number,
            baseColor: string,
            entity: any,
            progress: number
        ) => {
            if (mesh) {
                // TEMP_OBJ.scale.copy(entity.scale).multiplyScalar(scaleMult) 
                // We don't have scale property in Enemy interface yet (it was in EntityState)
                // Assuming scale is 1 for now unless we add it to Enemy interface. 
                // For now, hardcode 1.
                TEMP_OBJ.scale.set(1, 1, 1).multiplyScalar(scaleMult)

                TEMP_OBJ.position.copy(entity.position)
                TEMP_OBJ.quaternion.copy(entity.rotation)
                TEMP_OBJ.updateMatrix()
                mesh.setMatrixAt(idx, TEMP_OBJ.matrix)

                let hex = "#00ff00"
                if (time - (entity.lastHitTime || 0) < 0.15) hex = "#ffff00"
                else if (entity.hp / entity.maxHp < 0.4) hex = "#ff0000"

                if (hex === "#00ff00") TEMP_COLOR.set(baseColor)
                else TEMP_COLOR.set(hex)

                mesh.setColorAt(idx, TEMP_COLOR)

                if (deathArray) deathArray[idx] = progress
            }
        }

        for (let i = 0; i < enemies.length; i++) {
            const e = enemies[i]
            // Render even if dying (animation)
            if (!e.position) continue // Safety

            // Death Progress (0 to 1)
            let deathProgress = 0
            if (e.isDead || e.hp <= 0) {
                // For now, if Dead, it's removed immediately by store.
                // So we won't see death animation if they are removed instantly.
                // To fix this, we need 'isDying' flag in store that delays removal.
                // But for this quick port, let's assume valid living enemies.
                // If we want death anim, we need store to keep them for 0.5s.
                // Let's assume living for now.
            }

            // Hack for death animation: use 'hp <= 0' check if we kept them in store
            // (Store implementation currently removes them instantly, so no anim for now. Functional first.)

            // Color Logic
            let colorHex = "#00ff00"
            // Use time prop from state if available, or just Date.now
            // e.lastHitTime is in seconds (from new EnemySystem)
            // time is also in seconds from state.clock

            // Note: EnemySystem sets lastHitTime = Date.now() / 1000

            if (e.type === 'drone' || e.type === 'fighter') {
                if (droneWireRef.current && coreRef.current) {

                    let baseColor = e.type === 'fighter' ? '#ff9900' : '#00ff00'

                    // Hit Blink
                    if (Date.now() / 1000 - e.lastHitTime < 0.1) baseColor = '#ffffff'

                    TEMP_COLOR.set(baseColor)

                    // 1. Wireframe Body
                    TEMP_OBJ.position.copy(e.position)
                    TEMP_OBJ.quaternion.copy(e.rotation)
                    TEMP_OBJ.scale.set(1, 1, 1).multiplyScalar(2)
                    TEMP_OBJ.updateMatrix()

                    droneWireRef.current.setMatrixAt(droneCount, TEMP_OBJ.matrix)
                    droneWireRef.current.setColorAt(droneCount, TEMP_COLOR)
                    // droneDeathArray[droneCount] = 0

                    // 2. Inner Core
                    TEMP_OBJ.scale.set(1, 1, 1).multiplyScalar(0.8)
                    TEMP_OBJ.updateMatrix()
                    coreRef.current.setMatrixAt(droneCount, TEMP_OBJ.matrix)

                    TEMP_COLOR.setHSL(TEMP_COLOR.getHSL({} as any).h, 1, 0.7)
                    coreRef.current.setColorAt(droneCount, TEMP_COLOR)
                    // coreDeathArray[droneCount] = 0

                    droneCount++
                }
            } else if (e.type === 'scout') {
                updateMesh(scoutRef.current, scoutDeathArray, scoutCount++, 1.5, "#00ffff", e, 0)
            } else if (e.type === 'heavy') {
                updateMesh(heavyRef.current, heavyDeathArray, heavyCount++, 2.5, "#555555", e, 0)
            } else if (e.type === 'speeder') {
                updateMesh(speederRef.current, speederDeathArray, speederCount++, 1.2, "#ffa500", e, 0)
            } else if (e.type === 'charger') {
                updateMesh(chargerRef.current, chargerDeathArray, chargerCount++, 1.8, "#ff00ff", e, 0)
            } else if (e.type === 'sniper') {
                updateMesh(sniperRef.current, sniperDeathArray, sniperCount++, 1.5, "#0000ff", e, 0)
            } else if (e.type === 'swarmer') {
                updateMesh(swarmerRef.current, swarmerDeathArray, swarmerCount++, 0.8, "#ffff00", e, 0)
            } else if (e.type === 'orbit') {
                updateMesh(orbitRef.current, orbitDeathArray, orbitCount++, 3.0, "#aa00ff", e, 0)
            } else if (e.type === 'titan') {
                updateMesh(titanRef.current, titanDeathArray, titanCount++, 5.0, "#ffffff", e, 0)
            }
        }

        // Helper to update instance counts
        const updateInstance = (ref: React.RefObject<THREE.InstancedMesh>, count: number, attrRef?: React.RefObject<THREE.InstancedBufferAttribute>) => {
            if (ref.current) {
                ref.current.count = count
                ref.current.instanceMatrix.needsUpdate = true
                if (ref.current.instanceColor) ref.current.instanceColor.needsUpdate = true
            }
            if (attrRef?.current) attrRef.current.needsUpdate = true
        }

        updateInstance(droneWireRef, droneCount, droneDeathAttr)
        updateInstance(coreRef, droneCount, coreDeathAttr)
        updateInstance(scoutRef, scoutCount, scoutDeathAttr)

        updateInstance(heavyRef, heavyCount, heavyDeathAttr)
        updateInstance(speederRef, speederCount, speederDeathAttr)
        updateInstance(chargerRef, chargerCount, chargerDeathAttr)
        updateInstance(sniperRef, sniperCount, sniperDeathAttr)
        updateInstance(swarmerRef, swarmerCount, swarmerDeathAttr)
        updateInstance(orbitRef, orbitCount, orbitDeathAttr)
        updateInstance(titanRef, titanCount, titanDeathAttr)
    })

    return (
        <group>
            {/* --- DRONES (Shattering Wireframe + Dissolving Core) --- */}
            {/* Body */}
            <instancedMesh ref={droneWireRef} args={[undefined, undefined, 200]} frustumCulled={false}>
                <coneGeometry args={[2, 4, 4]}>
                    <instancedBufferAttribute ref={droneDeathAttr} attach="attributes-aDeath" args={[new Float32Array(200), 1]} />
                </coneGeometry>
                <primitive object={wireMaterial} attach="material" />
            </instancedMesh>

            {/* Core */}
            <instancedMesh ref={coreRef} args={[undefined, undefined, 200]} frustumCulled={false}>
                <sphereGeometry args={[1, 8, 8]}>
                    <instancedBufferAttribute ref={coreDeathAttr} attach="attributes-aDeath" args={[new Float32Array(200), 1]} />
                </sphereGeometry>
                <primitive object={coreMaterial} attach="material" />
            </instancedMesh>

            {/* --- SCOUTS --- */}
            <instancedMesh ref={scoutRef} args={[undefined, undefined, 50]} frustumCulled={false}>
                <octahedronGeometry args={[2, 0]}>
                    <instancedBufferAttribute ref={scoutDeathAttr} attach="attributes-aDeath" args={[new Float32Array(50), 1]} />
                </octahedronGeometry>
                <primitive object={scoutMaterial} attach="material" />
            </instancedMesh>

            {/* --- NEW ENEMIES --- */}
            {/* Heavy (Box) */}
            <instancedMesh ref={heavyRef} args={[undefined, undefined, 50]} frustumCulled={false}>
                <boxGeometry args={[2, 2, 2]}>
                    <instancedBufferAttribute ref={heavyDeathAttr} attach="attributes-aDeath" args={[new Float32Array(50), 1]} />
                </boxGeometry>
                <primitive object={genericMaterial} attach="material" />
            </instancedMesh>

            {/* Speeder (Tetrahedron) */}
            <instancedMesh ref={speederRef} args={[undefined, undefined, 50]} frustumCulled={false}>
                <tetrahedronGeometry args={[2, 0]}>
                    <instancedBufferAttribute ref={speederDeathAttr} attach="attributes-aDeath" args={[new Float32Array(50), 1]} />
                </tetrahedronGeometry>
                <primitive object={genericMaterial} attach="material" />
            </instancedMesh>

            {/* Charger (Icosahedron) */}
            <instancedMesh ref={chargerRef} args={[undefined, undefined, 50]} frustumCulled={false}>
                <icosahedronGeometry args={[2, 0]}>
                    <instancedBufferAttribute ref={chargerDeathAttr} attach="attributes-aDeath" args={[new Float32Array(50), 1]} />
                </icosahedronGeometry>
                <primitive object={genericMaterial} attach="material" />
            </instancedMesh>

            {/* Sniper (Cylinder) */}
            <instancedMesh ref={sniperRef} args={[undefined, undefined, 50]} frustumCulled={false}>
                <cylinderGeometry args={[0.5, 0.5, 4, 8]}>
                    <instancedBufferAttribute ref={sniperDeathAttr} attach="attributes-aDeath" args={[new Float32Array(50), 1]} />
                </cylinderGeometry>
                <primitive object={genericMaterial} attach="material" />
            </instancedMesh>

            {/* Swarmer (Sphere) - small */}
            <instancedMesh ref={swarmerRef} args={[undefined, undefined, 100]} frustumCulled={false}>
                <sphereGeometry args={[1, 6, 6]}>
                    <instancedBufferAttribute ref={swarmerDeathAttr} attach="attributes-aDeath" args={[new Float32Array(100), 1]} />
                </sphereGeometry>
                <primitive object={genericMaterial} attach="material" />
            </instancedMesh>

            {/* Orbit (Torus) */}
            <instancedMesh ref={orbitRef} args={[undefined, undefined, 20]} frustumCulled={false}>
                <torusGeometry args={[3, 0.5, 8, 16]}>
                    <instancedBufferAttribute ref={orbitDeathAttr} attach="attributes-aDeath" args={[new Float32Array(20), 1]} />
                </torusGeometry>
                <primitive object={genericMaterial} attach="material" />
            </instancedMesh>

            {/* Titan (Dodecahedron) */}
            <instancedMesh ref={titanRef} args={[undefined, undefined, 10]} frustumCulled={false}>
                <dodecahedronGeometry args={[4, 0]}>
                    <instancedBufferAttribute ref={titanDeathAttr} attach="attributes-aDeath" args={[new Float32Array(10), 1]} />
                </dodecahedronGeometry>
                <primitive object={genericMaterial} attach="material" />
            </instancedMesh>
        </group>
    )
}
