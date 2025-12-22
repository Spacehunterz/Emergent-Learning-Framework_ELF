import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Lock, Check, Zap, Target, Battery, ChevronUp, ShoppingCart, Shield, Heart } from 'lucide-react'
import { WEAPON_TYPES, WeaponType, getAllWeapons } from '../systems/WeaponTypes'
import { usePlayerWeaponStore } from '../systems/PlayerWeaponStore'
import { useSound } from '../systems/SoundManager'

interface WeaponShopProps {
    isOpen: boolean
    onClose: () => void
}

export const WeaponShop: React.FC<WeaponShopProps> = ({ isOpen, onClose }) => {
    const sound = useSound()
    const {
        credits,
        equippedWeaponId,
        unlockedWeapons,
        equipWeapon,
        unlockWeapon,
        upgradeWeapon,
        getEffectiveStats,
        getUpgradeCost,
        getUpgradeLevel
    } = usePlayerWeaponStore()

    const [activeCategory, setActiveCategory] = useState<'weapons' | 'ship'>('weapons')

    // Weapon Selection State
    const [selectedWeaponId, setSelectedWeaponId] = useState<string>(equippedWeaponId)
    const selectedWeapon = WEAPON_TYPES[selectedWeaponId]
    const isUnlocked = unlockedWeapons.includes(selectedWeaponId)
    const isEquipped = equippedWeaponId === selectedWeaponId

    const handleSelectWeapon = (weaponId: string) => {
        sound.playUiClick()
        setSelectedWeaponId(weaponId)
    }

    const handleUnlock = () => {
        if (unlockWeapon(selectedWeaponId)) {
            sound.playLevelUp()
        } else {
            sound.playHit()
        }
    }

    const handleEquip = () => {
        equipWeapon(selectedWeaponId)
        sound.playUiClick()
    }

    const handleUpgrade = (type: 'damage' | 'fireRate' | 'energy') => {
        if (upgradeWeapon(selectedWeaponId, type)) {
            sound.playLevelUp()
        } else {
            sound.playHit()
        }
    }

    const effectiveStats = isUnlocked ? getEffectiveStats(selectedWeaponId) : null
    const damageLevel = isUnlocked ? getUpgradeLevel(selectedWeaponId, 'damage') : 0
    const fireRateLevel = isUnlocked ? getUpgradeLevel(selectedWeaponId, 'fireRate') : 0
    const energyLevel = isUnlocked ? getUpgradeLevel(selectedWeaponId, 'energy') : 0

    const damageCost = isUnlocked ? getUpgradeCost(selectedWeaponId, 'damage') : -1
    const fireRateCost = isUnlocked ? getUpgradeCost(selectedWeaponId, 'fireRate') : -1
    const energyCost = isUnlocked ? getUpgradeCost(selectedWeaponId, 'energy') : -1

    // Ship Upgrades
    const shipUpgrades = usePlayerWeaponStore(s => s.shipUpgrades)
    const upgradeShipSystem = usePlayerWeaponStore(s => s.upgradeShipSystem)
    const getShipUpgradeCost = usePlayerWeaponStore(s => s.getShipUpgradeCost)

    const handleShipUpgrade = (type: 'shield' | 'hull' | 'energy' | 'power') => {
        if (upgradeShipSystem(type)) {
            sound.playLevelUp()
        } else {
            sound.playHit()
        }
    }

    if (!isOpen) return null

    return (
        <AnimatePresence>
            <div
                className="fixed inset-0 z-[150000] flex items-center justify-center bg-black/90 backdrop-blur-sm"
                onClick={(e) => e.stopPropagation()} // Prevent clicks from bubbling
            >
                <motion.div
                    initial={{ opacity: 0, scale: 0.9, y: 20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.9, y: 20 }}
                    className="w-full max-w-5xl bg-gradient-to-b from-slate-900 to-slate-950 border border-cyan-500/30 rounded-2xl overflow-hidden shadow-[0_0_60px_rgba(6,182,212,0.3)] flex flex-col h-[600px]"
                    onClick={(e) => e.stopPropagation()}
                >
                    {/* Header */}
                    <div className="flex items-center justify-between p-6 border-b border-cyan-500/20 bg-cyan-950/20 shrink-0">
                        <div className="flex items-center gap-6">
                            <div className="flex items-center gap-3">
                                <ShoppingCart className="w-7 h-7 text-cyan-400" />
                                <h2 className="text-2xl font-black text-white tracking-widest uppercase">
                                    <span className="text-cyan-400">SHOP</span>
                                </h2>
                            </div>

                            {/* Category Tabs */}
                            <div className="flex bg-black/40 rounded-lg p-1 border border-white/10">
                                <button
                                    onClick={() => { setActiveCategory('weapons'); sound.playUiClick() }}
                                    className={`px-4 py-1.5 rounded text-sm font-bold transition-all ${activeCategory === 'weapons'
                                        ? 'bg-cyan-500 text-black shadow-lg'
                                        : 'text-slate-400 hover:text-white'
                                        }`}
                                >
                                    WEAPONS
                                </button>
                                <button
                                    onClick={() => { setActiveCategory('ship'); sound.playUiClick() }}
                                    className={`px-4 py-1.5 rounded text-sm font-bold transition-all ${activeCategory === 'ship'
                                        ? 'bg-cyan-500 text-black shadow-lg'
                                        : 'text-slate-400 hover:text-white'
                                        }`}
                                >
                                    SHIP SYSTEMS
                                </button>
                            </div>
                        </div>

                        <div className="flex items-center gap-6">
                            <div className="text-right">
                                <div className="text-xs text-slate-400 uppercase tracking-wider">Credits</div>
                                <div className="text-2xl font-black text-yellow-400 font-mono">
                                    {credits.toLocaleString()}
                                </div>
                            </div>
                            <button
                                onClick={onClose}
                                onMouseEnter={() => sound.playUiHover()}
                                className="p-2 hover:bg-white/10 rounded-full transition-colors"
                            >
                                <X className="w-6 h-6 text-slate-400 hover:text-white" />
                            </button>
                        </div>
                    </div>

                    {/* Content Area */}
                    <div className="flex-1 overflow-hidden min-h-0">
                        {activeCategory === 'weapons' ? (
                            <div className="grid grid-cols-[280px_1fr] h-full">
                                {/* Weapon List */}
                                <div className="p-4 border-r border-white/5 bg-black/30 overflow-y-auto h-full">
                                    <div className="space-y-2">
                                        {getAllWeapons().map((weapon) => {
                                            const weaponUnlocked = unlockedWeapons.includes(weapon.id)
                                            const weaponEquipped = equippedWeaponId === weapon.id
                                            const isSelected = selectedWeaponId === weapon.id

                                            return (
                                                <button
                                                    key={weapon.id}
                                                    onClick={() => handleSelectWeapon(weapon.id)}
                                                    onMouseEnter={() => sound.playUiHover()}
                                                    className={`w-full p-3 rounded-lg border transition-all text-left ${isSelected
                                                        ? 'bg-cyan-500/20 border-cyan-500 shadow-[0_0_15px_rgba(6,182,212,0.3)]'
                                                        : 'bg-white/5 border-white/10 hover:border-white/30'
                                                        }`}
                                                >
                                                    <div className="flex items-center justify-between">
                                                        <div className="flex items-center gap-2">
                                                            {!weaponUnlocked && (
                                                                <Lock className="w-4 h-4 text-slate-500" />
                                                            )}
                                                            <span
                                                                className={`font-bold text-sm ${weaponUnlocked ? 'text-white' : 'text-slate-500'
                                                                    }`}
                                                            >
                                                                {weapon.name}
                                                            </span>
                                                        </div>
                                                        {weaponEquipped && (
                                                            <span className="text-[10px] font-bold text-cyan-400 bg-cyan-400/20 px-2 py-0.5 rounded">
                                                                EQUIPPED
                                                            </span>
                                                        )}
                                                    </div>
                                                    {!weaponUnlocked && weapon.price > 0 && (
                                                        <div className="text-xs text-yellow-500/70 mt-1">
                                                            {weapon.price.toLocaleString()} credits
                                                        </div>
                                                    )}
                                                </button>
                                            )
                                        })}
                                    </div>
                                </div>

                                {/* Weapon Details */}
                                <div className="p-6 overflow-y-auto h-full">
                                    {selectedWeapon && (
                                        <div className="space-y-6">
                                            {/* Weapon Header */}
                                            <div className="flex items-start justify-between">
                                                <div>
                                                    <h3 className="text-3xl font-black text-white tracking-wider">
                                                        {selectedWeapon.name}
                                                    </h3>
                                                    <p className="text-slate-400 mt-1">{selectedWeapon.description}</p>
                                                </div>
                                                <div className="flex gap-2">
                                                    {selectedWeapon.colors.slice(0, 3).map((color, i) => (
                                                        <div
                                                            key={i}
                                                            className="w-6 h-6 rounded-full border-2 border-white/20"
                                                            style={{ backgroundColor: color }}
                                                        />
                                                    ))}
                                                </div>
                                            </div>

                                            {/* Base Stats */}
                                            <div className="grid grid-cols-4 gap-4 p-4 bg-white/5 rounded-lg">
                                                <div className="text-center">
                                                    <div className="text-xs text-slate-400 uppercase">Damage</div>
                                                    <div className="text-xl font-bold text-red-400">
                                                        {effectiveStats?.damage || selectedWeapon.damage}
                                                    </div>
                                                </div>
                                                <div className="text-center">
                                                    <div className="text-xs text-slate-400 uppercase">Fire Rate</div>
                                                    <div className="text-xl font-bold text-orange-400">
                                                        {(effectiveStats?.fireRate || selectedWeapon.fireRate).toFixed(1)}/s
                                                    </div>
                                                </div>
                                                <div className="text-center">
                                                    <div className="text-xs text-slate-400 uppercase">Energy</div>
                                                    <div className="text-xl font-bold text-yellow-400">
                                                        {effectiveStats?.energyCost || selectedWeapon.energyCost}
                                                    </div>
                                                </div>
                                                <div className="text-center">
                                                    <div className="text-xs text-slate-400 uppercase">Speed</div>
                                                    <div className="text-xl font-bold text-cyan-400">
                                                        {selectedWeapon.speed}
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Unlock / Equip Button */}
                                            {!isUnlocked ? (
                                                <button
                                                    onClick={handleUnlock}
                                                    onMouseEnter={() => sound.playUiHover()}
                                                    disabled={credits < selectedWeapon.price}
                                                    className={`w-full py-4 rounded-lg font-bold text-lg flex items-center justify-center gap-3 transition-all ${credits >= selectedWeapon.price
                                                        ? 'bg-gradient-to-r from-yellow-600 to-yellow-500 hover:from-yellow-500 hover:to-yellow-400 text-white shadow-[0_0_20px_rgba(234,179,8,0.3)]'
                                                        : 'bg-slate-800 text-slate-500 cursor-not-allowed'
                                                        }`}
                                                >
                                                    <Lock className="w-5 h-5" />
                                                    UNLOCK FOR {selectedWeapon.price.toLocaleString()} CREDITS
                                                </button>
                                            ) : !isEquipped ? (
                                                <button
                                                    onClick={handleEquip}
                                                    onMouseEnter={() => sound.playUiHover()}
                                                    className="w-full py-4 bg-gradient-to-r from-cyan-600 to-cyan-500 hover:from-cyan-500 hover:to-cyan-400 text-white rounded-lg font-bold text-lg flex items-center justify-center gap-3 shadow-[0_0_20px_rgba(6,182,212,0.3)] transition-all"
                                                >
                                                    <Check className="w-5 h-5" />
                                                    EQUIP WEAPON
                                                </button>
                                            ) : (
                                                <div className="w-full py-4 bg-cyan-500/20 border border-cyan-500 text-cyan-400 rounded-lg font-bold text-lg flex items-center justify-center gap-3">
                                                    <Check className="w-5 h-5" />
                                                    CURRENTLY EQUIPPED
                                                </div>
                                            )}

                                            {/* Upgrades Section */}
                                            {isUnlocked && (
                                                <div className="space-y-4">
                                                    <h4 className="text-lg font-bold text-white border-b border-white/10 pb-2">
                                                        UPGRADES
                                                    </h4>

                                                    <UpgradeRow
                                                        icon={<Target className="w-5 h-5 text-red-400" />}
                                                        label="Damage"
                                                        description="+15% damage per level"
                                                        level={damageLevel}
                                                        maxLevel={5}
                                                        cost={damageCost}
                                                        currentCredits={credits}
                                                        onUpgrade={() => handleUpgrade('damage')}
                                                        sound={sound}
                                                    />

                                                    <UpgradeRow
                                                        icon={<Zap className="w-5 h-5 text-orange-400" />}
                                                        label="Fire Rate"
                                                        description="+10% fire rate per level"
                                                        level={fireRateLevel}
                                                        maxLevel={5}
                                                        cost={fireRateCost}
                                                        currentCredits={credits}
                                                        onUpgrade={() => handleUpgrade('fireRate')}
                                                        sound={sound}
                                                    />

                                                    <UpgradeRow
                                                        icon={<Battery className="w-5 h-5 text-yellow-400" />}
                                                        label="Efficiency"
                                                        description="-8% energy cost per level"
                                                        level={energyLevel}
                                                        maxLevel={5}
                                                        cost={energyCost}
                                                        currentCredits={credits}
                                                        onUpgrade={() => handleUpgrade('energy')}
                                                        sound={sound}
                                                    />
                                                </div>
                                            )}

                                            {Object.keys(selectedWeapon.special).length > 0 && (
                                                <div className="p-4 bg-purple-500/10 border border-purple-500/30 rounded-lg">
                                                    <h4 className="text-sm font-bold text-purple-400 uppercase mb-2">
                                                        Special Properties
                                                    </h4>
                                                    <div className="grid grid-cols-2 gap-2 text-sm">
                                                        {Object.entries(selectedWeapon.special).map(([key, value]) => (
                                                            <div key={key} className="flex justify-between">
                                                                <span className="text-slate-400 capitalize">
                                                                    {key.replace(/([A-Z])/g, ' $1').trim()}
                                                                </span>
                                                                <span className="text-white font-mono">{value}</span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ) : (
                            /* SHIP SYSTEMS VIEW */
                            <div className="p-8 h-full overflow-y-auto">
                                <div className="grid grid-cols-2 gap-6 max-w-4xl mx-auto">
                                    <SystemCard
                                        icon={<Shield className="w-8 h-8 text-cyan-400" />}
                                        title="SHIELD GENERATOR V2"
                                        description="Upgrade max shield capacity."
                                        statLabel="Max Shields"
                                        currentVal={100 + (shipUpgrades.shield * 25)}
                                        nextVal={100 + ((shipUpgrades.shield + 1) * 25)}
                                        level={shipUpgrades.shield}
                                        maxLevel={5}
                                        cost={getShipUpgradeCost('shield')}
                                        credits={credits}
                                        onUpgrade={() => handleShipUpgrade('shield')}
                                        sound={sound}
                                    />
                                    <SystemCard
                                        icon={<Heart className="w-8 h-8 text-red-500" />}
                                        title="HULL INTEGRITY"
                                        description="Reinforce ship hull structure."
                                        statLabel="Max Hull"
                                        currentVal={100 + (shipUpgrades.hull * 25)}
                                        nextVal={100 + ((shipUpgrades.hull + 1) * 25)}
                                        level={shipUpgrades.hull}
                                        maxLevel={5}
                                        cost={getShipUpgradeCost('hull')}
                                        credits={credits}
                                        onUpgrade={() => handleShipUpgrade('hull')}
                                        sound={sound}
                                    />
                                    <SystemCard
                                        icon={<Battery className="w-8 h-8 text-yellow-500" />}
                                        title="ENERGY CORE"
                                        description="Increase weapon energy capacity."
                                        statLabel="Max Energy"
                                        currentVal={100 + (shipUpgrades.energy * 20)}
                                        nextVal={100 + ((shipUpgrades.energy + 1) * 20)}
                                        level={shipUpgrades.energy}
                                        maxLevel={5}
                                        cost={getShipUpgradeCost('energy')}
                                        credits={credits}
                                        onUpgrade={() => handleShipUpgrade('energy')}
                                        sound={sound}
                                    />
                                    <SystemCard
                                        icon={<Zap className="w-8 h-8 text-purple-500" />}
                                        title="OVERCHARGE CAPACITOR"
                                        description="Extend turbo boost duration."
                                        statLabel="Duration"
                                        currentVal={30 + (shipUpgrades.power * 10)}
                                        nextVal={30 + ((shipUpgrades.power + 1) * 10)}
                                        suffix="s"
                                        level={shipUpgrades.power}
                                        maxLevel={5}
                                        cost={getShipUpgradeCost('power')}
                                        credits={credits}
                                        onUpgrade={() => handleShipUpgrade('power')}
                                        sound={sound}
                                    />
                                </div>
                            </div>
                        )}
                    </div>
                </motion.div>
            </div>
        </AnimatePresence>
    )
}

// System Card Component
const SystemCard: React.FC<{
    icon: React.ReactNode
    title: string
    description: string
    statLabel: string
    currentVal: number
    nextVal: number
    suffix?: string
    level: number
    maxLevel: number
    cost: number
    credits: number
    onUpgrade: () => void
    sound: any
}> = ({ icon, title, description, statLabel, currentVal, nextVal, suffix = '', level, maxLevel, cost, credits, onUpgrade, sound }) => {
    const isMaxed = level >= maxLevel
    const canAfford = cost > 0 && credits >= cost

    return (
        <div className="bg-white/5 border border-white/10 rounded-xl p-6 flex flex-col gap-4 hover:border-white/20 transition-colors">
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-black/40 rounded-lg">
                        {icon}
                    </div>
                    <div>
                        <h3 className="text-xl font-bold text-white">{title}</h3>
                        <p className="text-sm text-slate-400">{description}</p>
                    </div>
                </div>
            </div>

            <div className="bg-black/20 rounded-lg p-4 grid grid-cols-2 gap-4">
                <div>
                    <div className="text-xs text-slate-500 uppercase font-bold">{statLabel}</div>
                    <div className="text-2xl font-mono font-bold text-white">{currentVal}{suffix}</div>
                </div>
                {!isMaxed && (
                    <div className="text-right">
                        <div className="text-xs text-cyan-500 uppercase font-bold">Next Level</div>
                        <div className="text-2xl font-mono font-bold text-cyan-400">{nextVal}{suffix}</div>
                    </div>
                )}
            </div>

            <div className="mt-auto pt-4 border-t border-white/5 space-y-4">
                {/* Level Indicator */}
                <div className="flex justify-between items-center text-xs text-slate-400">
                    <span>LEVEL {level} / {maxLevel}</span>
                    <div className="flex gap-1">
                        {Array.from({ length: maxLevel }).map((_, i) => (
                            <div
                                key={i}
                                className={`w-3 h-1.5 rounded-sm ${i < level ? 'bg-cyan-400' : 'bg-slate-700'
                                    }`}
                            />
                        ))}
                    </div>
                </div>

                {/* Button */}
                {isMaxed ? (
                    <button disabled className="w-full py-3 bg-slate-800 text-slate-500 font-bold rounded-lg cursor-not-allowed">
                        MAX LEVEL REACHED
                    </button>
                ) : (
                    <button
                        onClick={onUpgrade}
                        disabled={!canAfford}
                        onMouseEnter={() => sound.playUiHover()}
                        className={`w-full py-3 font-bold rounded-lg flex items-center justify-center gap-2 transition-all ${canAfford
                            ? 'bg-yellow-500 hover:bg-yellow-400 text-black shadow-lg shadow-yellow-500/20'
                            : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                            }`}
                    >
                        <ChevronUp className="w-4 h-4" />
                        UPGRADE ({cost.toLocaleString()})
                    </button>
                )}
            </div>
        </div>
    )
}

// Upgrade Row Component
const UpgradeRow: React.FC<{
    icon: React.ReactNode
    label: string
    description: string
    level: number
    maxLevel: number
    cost: number
    currentCredits: number
    onUpgrade: () => void
    sound: ReturnType<typeof useSound>
}> = ({ icon, label, description, level, maxLevel, cost, currentCredits, onUpgrade, sound }) => {
    const isMaxed = level >= maxLevel
    const canAfford = cost > 0 && currentCredits >= cost

    return (
        <div className="flex items-center justify-between p-3 bg-white/5 rounded-lg">
            <div className="flex items-center gap-3">
                {icon}
                <div>
                    <div className="font-bold text-white">{label}</div>
                    <div className="text-xs text-slate-400">{description}</div>
                </div>
            </div>

            <div className="flex items-center gap-4">
                {/* Level Indicator */}
                <div className="flex gap-1">
                    {Array.from({ length: maxLevel }).map((_, i) => (
                        <div
                            key={i}
                            className={`w-2 h-4 rounded-sm ${i < level ? 'bg-cyan-400' : 'bg-slate-700'
                                }`}
                        />
                    ))}
                </div>

                {/* Upgrade Button */}
                {isMaxed ? (
                    <div className="px-4 py-2 bg-slate-700 text-slate-400 rounded-lg text-sm font-bold">
                        MAXED
                    </div>
                ) : (
                    <button
                        onClick={onUpgrade}
                        onMouseEnter={() => sound.playUiHover()}
                        disabled={!canAfford}
                        className={`px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-2 transition-all ${canAfford
                            ? 'bg-yellow-500 hover:bg-yellow-400 text-black'
                            : 'bg-slate-700 text-slate-400 cursor-not-allowed'
                            }`}
                    >
                        <ChevronUp className="w-4 h-4" />
                        {cost.toLocaleString()}
                    </button>
                )}
            </div>
        </div>
    )
}
