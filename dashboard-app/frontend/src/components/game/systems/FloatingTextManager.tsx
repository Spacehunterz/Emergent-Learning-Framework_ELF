import { create } from 'zustand'
import { useFrame } from '@react-three/fiber'
import { useRef } from 'react'
import { Vector3 } from 'three'
import { Text } from '@react-three/drei'
import { useGameSettings } from './GameSettings'

interface FloatingText {
    id: string
    position: Vector3
    text: string
    color: string
    scale: number
    createdAt: number
}

interface FloatingTextStore {
    texts: FloatingText[]
    spawnText: (position: Vector3, text: string, color?: string, scale?: number) => void
}

// Simplified store - cleanup happens on spawn
export const useFloatingTextStore = create<FloatingTextStore>((set) => ({
    texts: [],
    spawnText: (position, text, color = '#ffffff', scale = 1) => set((state) => {
        // Clean up old texts when spawning new ones
        const now = Date.now()
        const activeTexts = state.texts.filter(t => now - t.createdAt < 1500)
        return {
            texts: [...activeTexts, {
                id: `txt-${now}-${Math.random()}`,
                position: position.clone(),
                text,
                color,
                scale,
                createdAt: now
            }]
        }
    })
}))

const FloatingTextElement = ({ data }: { data: FloatingText }) => {
    const ref = useRef<any>()
    const { isPaused } = useGameSettings()

    useFrame(() => {
        if (isPaused || !ref.current) return
        const age = (Date.now() - data.createdAt) / 1000
        // Float upward
        ref.current.position.y = data.position.y + age * 3
        // Fade out
        ref.current.fillOpacity = Math.max(0, 1 - age * 0.8)
    })

    return (
        <Text
            ref={ref}
            position={[data.position.x, data.position.y, data.position.z]}
            fontSize={data.scale * 0.5}
            color={data.color}
            anchorX="center"
            anchorY="middle"
            fillOpacity={1}
        >
            {data.text}
        </Text>
    )
}

export const FloatingTextRenderer = () => {
    const { texts } = useFloatingTextStore()

    // Filter active texts in render (no state updates)
    const now = Date.now()
    const activeTexts = texts.filter(t => now - t.createdAt < 1500)

    return (
        <group>
            {activeTexts.map(t => (
                <FloatingTextElement key={t.id} data={t} />
            ))}
        </group>
    )
}
