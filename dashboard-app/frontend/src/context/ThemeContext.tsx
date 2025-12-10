import { createContext, useContext, useEffect, useState } from 'react'

export type Theme = 'black-hole' | 'white-dwarf' | 'deep-space' | 'nebula' | 'supernova' | 'aurora' | 'solar' | 'crimson' | 'cyan' | 'rose'

const STORAGE_KEY = 'dashboard-theme-settings'

interface StoredSettings {
  theme: Theme
  particleCount: number
  glassOpacity: number
}

interface ThemeContextType {
  theme: Theme
  setTheme: (theme: Theme) => void
  particleCount: number
  setParticleCount: (count: number) => void
  glassOpacity: number
  setGlassOpacity: (opacity: number) => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

function loadSettings(): StoredSettings {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      return {
        theme: parsed.theme || 'black-hole',
        particleCount: typeof parsed.particleCount === 'number' ? parsed.particleCount : 100,
        glassOpacity: typeof parsed.glassOpacity === 'number' ? parsed.glassOpacity : 0.2,
      }
    }
  } catch (e) {
    console.warn('Failed to load theme settings:', e)
  }
  return { theme: 'black-hole', particleCount: 100, glassOpacity: 0.2 }
}

function saveSettings(settings: StoredSettings): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
  } catch (e) {
    console.warn('Failed to save theme settings:', e)
  }
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [initialized, setInitialized] = useState(false)
  const [theme, setTheme] = useState<Theme>('black-hole')
  const [particleCount, setParticleCount] = useState(100)
  const [glassOpacity, setGlassOpacity] = useState(0.2)

  // Load settings from localStorage on mount
  useEffect(() => {
    const settings = loadSettings()
    setTheme(settings.theme)
    setParticleCount(settings.particleCount)
    setGlassOpacity(settings.glassOpacity)
    setInitialized(true)
  }, [])

  // Save settings to localStorage when they change
  useEffect(() => {
    if (initialized) {
      saveSettings({ theme, particleCount, glassOpacity })
    }
  }, [theme, particleCount, glassOpacity, initialized])

  // Apply theme to DOM
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    document.documentElement.style.setProperty('--glass-opacity', glassOpacity.toString())
  }, [theme, glassOpacity])

  return (
    <ThemeContext.Provider value={{
      theme,
      setTheme,
      particleCount,
      setParticleCount,
      glassOpacity,
      setGlassOpacity
    }}>
      {children}
    </ThemeContext.Provider>
  )
}

export const useTheme = () => {
  const context = useContext(ThemeContext)
  if (!context) throw new Error('useTheme must be used within a ThemeProvider')
  return context
}
