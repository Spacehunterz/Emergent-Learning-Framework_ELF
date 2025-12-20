import { create } from 'zustand'
import { useFrame } from '@react-three/fiber'
import { useRef } from 'react'
import { Vector3 } from 'three'
import { Text } from '@react-three/drei'

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
    removeText: (id: string) => void
}

export const useFloatingTextStore = create<FloatingTextStore>((set) => ({
    texts: [],
    spawnText: (position, text, color = '#ffffff', scale = 1) => set((state) => ({
        texts: [...state.texts, {
            id: Math.random().toString(),
            position: position.clone(),
            text,
            color,
            scale,
            createdAt: Date.now()
        }]
    })),
    removeText: (id) => set((state) => ({
        texts: state.texts.filter(t => t.id !== id)
    }))
}))

const FloatingTextElement = ({ data }: { data: FloatingText }) => {
    const ref = useRef<any>()
    const initialY = useRef(data.position.y)

    useFrame((_, delta) => {
        if (ref.current) {
            // Float upward
            ref.current.position.y += delta * 2
            // Fade out
            ref.current.fillOpacity = Math.max(0, ref.current.fillOpacity - delta * 1.5)
        }
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
    const { texts, removeText } = useFloatingTextStore()

    // Cleanup old texts
    useFrame(() => {
        const now = Date.now()
        texts.forEach(t => {
            if (now - t.createdAt > 1500) {
                removeText(t.id)
            }
        })
    })

    return (
        <group>
            {texts.map(t => (
                <FloatingTextElement key={t.id} data={t} />
            ))}
        </group>
    )
}
