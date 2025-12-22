import { useState } from 'react'
import { createPortal } from 'react-dom'
import { Settings, X, Moon, Sun, Sparkles, Leaf, Zap, Flame, Droplets, Heart, Circle, CircleDot } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { useTheme, Theme, useCosmicSettings, useCosmicAudio } from '../context'

export function SettingsPanel() {
  const [isOpen, setIsOpen] = useState(false)
  const { theme, setTheme, particleCount, setParticleCount, glassOpacity, setGlassOpacity } = useTheme()
  const { trailsEnabled, setTrailsEnabled, audioEnabled, setAudioEnabled, performanceMode, setPerformanceMode } = useCosmicSettings()
  const { playToggle, playHover, playClick } = useCosmicAudio()

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
        onClick={() => {
          setIsOpen(true);
          playClick();
        }}
        onMouseEnter={() => playHover()}
        className="p-2 rounded-full glass-panel shadow-lg hover:bg-white/10 transition-colors border border-white/10"
        style={{ color: 'var(--theme-text-primary)' }}
        title="Settings"
      >
        <Settings className="w-5 h-5" />
      </motion.button>

      {createPortal(
        <AnimatePresence>
          {isOpen && (
            <>
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => setIsOpen(false)}
                className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[9999]"
              />
              <motion.div
                initial={{ x: '100%' }}
                animate={{ x: 0 }}
                exit={{ x: '100%' }}
                transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                className="fixed inset-y-0 right-0 z-[10002] w-96 p-6 overflow-y-auto border-l border-white/10 shadow-2xl"
                style={{ backgroundColor: 'rgb(10, 10, 20)' }}
              >
                <div className="flex items-center justify-between mb-8">
                  <h2 className="text-xl font-bold flex items-center gap-2" style={{ color: 'var(--theme-text-primary)' }}>
                    <Sparkles className="w-5 h-5" style={{ color: 'var(--theme-accent)' }} />
                    Cosmic Config
                  </h2>
                  <button
                    onClick={() => {
                      setIsOpen(false);
                      playClick();
                    }}
                    onMouseEnter={() => playHover()}
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
                          onClick={() => {
                            setTheme(t.id);
                            playClick();
                          }}
                          onMouseEnter={() => playHover()}
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

                  {/* Cosmic Settings */}
                  <div className="space-y-4 pt-4 border-t" style={{ borderColor: 'var(--theme-bg-card)' }}>
                    <h3 className="text-sm font-medium" style={{ color: 'var(--theme-text-primary)' }}>Experience</h3>

                    {/* Cursor Controls */}


                    <div className="flex items-center justify-between">
                      <span className="text-sm" style={{ color: 'var(--theme-text-secondary)' }}>Cursor Trails</span>
                      <button
                        onClick={() => {
                          setTrailsEnabled(!trailsEnabled);
                          playToggle(!trailsEnabled);
                        }}
                        onMouseEnter={() => playHover()}
                        className={`w-10 h-6 rounded-full transition-colors relative ${trailsEnabled ? 'bg-cyan-500' : 'bg-slate-700'}`}
                      >
                        <span className={`block w-4 h-4 bg-white rounded-full absolute top-1 transition-transform ${trailsEnabled ? 'left-5' : 'left-1'}`} />
                      </button>
                    </div>

                    {/* Audio Control */}
                    <div className="flex items-center justify-between">
                      <span className="text-sm" style={{ color: 'var(--theme-text-secondary)' }}>UI Sounds</span>
                      <button
                        onClick={() => {
                          const newState = !audioEnabled;
                          setAudioEnabled(newState);
                          playToggle(newState);
                        }}
                        onMouseEnter={() => playHover()}
                        className={`w-10 h-6 rounded-full transition-colors relative ${audioEnabled ? 'bg-cyan-500' : 'bg-slate-700'}`}
                      >
                        <span className={`block w-4 h-4 bg-white rounded-full absolute top-1 transition-transform ${audioEnabled ? 'left-5' : 'left-1'}`} />
                      </button>
                    </div>

                    {/* Performance Control */}
                    <div>
                      <label className="block text-sm mb-2" style={{ color: 'var(--theme-text-secondary)' }}>Performance Mode</label>
                      <div className="grid grid-cols-3 gap-2">
                        {['low', 'medium', 'high'].map((mode) => (
                          <button
                            key={mode}
                            onClick={() => {
                              setPerformanceMode(mode as any);
                              playClick();
                            }}
                            onMouseEnter={() => playHover()}
                            className={`px-2 py-1 text-xs rounded border transition-colors ${performanceMode === mode ? 'border-cyan-500 text-cyan-500' : 'border-slate-700 text-slate-400'}`}
                            style={{ backgroundColor: performanceMode === mode ? 'rgba(6, 182, 212, 0.1)' : 'transparent' }}
                          >
                            {mode.charAt(0).toUpperCase() + mode.slice(1)}
                          </button>
                        ))}
                      </div>
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
        </AnimatePresence>,
        document.body
      )}
    </>
  )
}
