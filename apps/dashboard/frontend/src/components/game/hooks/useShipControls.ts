import { useEffect, useRef } from 'react'
// import { useGameSettings } from '../systems/GameSettings'

export const useShipControls = (isPaused: boolean, setPaused: (paused: boolean) => void) => {
    const moveState = useRef({
        mouseX: 0,
        mouseY: 0,
        firing: false,
    })

    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (isPaused) return
            // Standard Screen Mapping: -1 to 1
            moveState.current.mouseX = (e.clientX / window.innerWidth) * 2 - 1
            moveState.current.mouseY = -(e.clientY / window.innerHeight) * 2 + 1
        }
        const handleMouseDown = (e: MouseEvent) => {
            if (isPaused) return
            if (e.button === 0) moveState.current.firing = true
        }
        const handleMouseUp = (e: MouseEvent) => {
            if (e.button === 0) moveState.current.firing = false
        }
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                setPaused(!isPaused)
            }
        }

        window.addEventListener('mousemove', handleMouseMove)
        window.addEventListener('mousedown', handleMouseDown)
        window.addEventListener('mouseup', handleMouseUp)
        window.addEventListener('keydown', handleKeyDown)

        return () => {
            window.removeEventListener('mousemove', handleMouseMove)
            window.removeEventListener('mousedown', handleMouseDown)
            window.removeEventListener('mouseup', handleMouseUp)
            window.removeEventListener('keydown', handleKeyDown)
        }
    }, [isPaused, setPaused])

    return moveState
}
