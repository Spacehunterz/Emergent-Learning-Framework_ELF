import { useState } from 'react'
import { Settings, X, Moon, Sun, Sparkles, Leaf, Zap, Flame, Droplets, Heart, Circle, CircleDot } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { useTheme, Theme } from '../context/ThemeContext'

export function SettingsPanel() {
  const [isOpen, setIsOpen] = useState(false)
  const { theme, setTheme, particleCount, setParticleCount, glassOpacity, setGlassOpacity } = useTheme()

  const themes: { id: Theme; name: string; icon: any; color: string; description: string }[] = [
    { id: 'black-hole', name: 'Black Hole', icon: Circle, color: 'text-orange-400', description: 'Dark mode' },
    { id: 'white-dwarf', name: 'White Dwarf', icon: CircleDot, color: 'text-sky-400', description: 'Light mode' },
    { id: 'deep-space', name: 'Deep Space', icon: Moon, color: 'text-blue-400', description: 'Blue' },
    { id: 'nebula', name: 'Nebula', icon: Sparkles, color: 'text-purple-400', description: 'Purple' },
    { id: 'supernova', name: 'Supernova', icon: Sun, color: 'text-orange-500', description: 'Orange' },
    { id: 'aurora', name: 'Aurora', icon: Leaf, color: 'text-green-400', description: 'Green' },
    { id: 'solar', name: 'Solar', icon: Zap, color: 'text-yellow-400', description: 'Yellow' },
    { id: 'crimson', name: 'Crimson', icon: Flame, color: 'text-red-400', description: 'Red' },
    { id: 'cyan', name: 'Cyan', icon: Droplets, color: 'text-cyan-400', description: 'Teal' },
    { id: 'rose', name: 'Rose', icon: Heart, color: 'text-pink-400', description: 'Pink' },
  ]

  return (
    <>
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setIsOpen(true)}
        className="fixed top-4 right-4 z-50 p-2 rounded-full shadow-lg transition-colors glass-panel hover:opacity-80"
        style={{ color: 'var(--theme-text-primary)' }}
      >
        <Settings className="w-6 h-6" />
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpen(false)}
              className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50"
            />
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'tween', duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
              className="fixed inset-y-0 right-0 z-50 w-80 glass-panel shadow-2xl p-6 overflow-y-auto"
              style={{ backgroundColor: 'var(--theme-bg-secondary)' }}
            >
              <div className="flex items-center justify-between mb-8">
                <h2 className="text-xl font-bold flex items-center gap-2" style={{ color: 'var(--theme-text-primary)' }}>
                  <Sparkles className="w-5 h-5" style={{ color: 'var(--theme-accent)' }} />
                  Cosmic Config
                </h2>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-1 transition-colors hover:opacity-70"
                  style={{ color: 'var(--theme-text-secondary)' }}
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              <div className="space-y-8">
                <div>
                  <label className="block text-sm font-medium mb-3" style={{ color: 'var(--theme-text-secondary)' }}>
                    Theme Preset
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {themes.map((t) => (
                      <button
                        key={t.id}
                        onClick={() => setTheme(t.id)}
                        className={
                          'flex items-center gap-2 p-3 rounded-lg border transition-all ' +
                          (theme === t.id
                            ? 'border-2 shadow-lg'
                            : 'border-transparent hover:border-slate-600')
                        }
                        style={{
                          backgroundColor: theme === t.id ? 'var(--theme-bg-card)' : 'rgba(128, 128, 128, 0.1)',
                          borderColor: theme === t.id ? 'var(--theme-accent)' : undefined,
                          boxShadow: theme === t.id ? '0 0 15px var(--theme-accent-glow)' : undefined,
                        }}
                      >
                        <t.icon className={'w-4 h-4 ' + t.color} />
                        <div className="text-left">
                          <span className="text-sm font-medium block" style={{ color: 'var(--theme-text-primary)' }}>
                            {t.name}
                          </span>
                          <span className="text-xs" style={{ color: 'var(--theme-text-secondary)' }}>
                            {t.description}
                          </span>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-3" style={{ color: 'var(--theme-text-secondary)' }}>
                    Particle Density: {particleCount}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="300"
                    value={particleCount}
                    onChange={(e) => setParticleCount(Number(e.target.value))}
                    className="w-full h-2 rounded-lg appearance-none cursor-pointer"
                    style={{
                      background: `linear-gradient(to right, var(--theme-accent) 0%, var(--theme-accent) ${(particleCount / 300) * 100}%, rgba(128,128,128,0.3) ${(particleCount / 300) * 100}%, rgba(128,128,128,0.3) 100%)`,
                    }}
                  />
                  <div className="flex justify-between text-xs mt-1" style={{ color: 'var(--theme-text-secondary)' }}>
                    <span>None</span>
                    <span>Dense</span>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-3" style={{ color: 'var(--theme-text-secondary)' }}>
                    Glass Opacity: {Math.round(glassOpacity * 100)}%
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={glassOpacity}
                    onChange={(e) => setGlassOpacity(Number(e.target.value))}
                    className="w-full h-2 rounded-lg appearance-none cursor-pointer"
                    style={{
                      background: `linear-gradient(to right, var(--theme-accent) 0%, var(--theme-accent) ${glassOpacity * 100}%, rgba(128,128,128,0.3) ${glassOpacity * 100}%, rgba(128,128,128,0.3) 100%)`,
                    }}
                  />
                  <div className="flex justify-between text-xs mt-1" style={{ color: 'var(--theme-text-secondary)' }}>
                    <span>Transparent</span>
                    <span>Solid</span>
                  </div>
                </div>

                <div className="pt-4 border-t" style={{ borderColor: 'var(--theme-bg-card)' }}>
                  <p className="text-xs" style={{ color: 'var(--theme-text-secondary)' }}>
                    Settings are saved automatically and will persist across sessions.
                  </p>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
