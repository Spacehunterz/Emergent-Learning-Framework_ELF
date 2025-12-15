import React from 'react'
import Header from '../components/Header'
import SettingsPanel from '../components/SettingsPanel'
import { ParticleBackground } from '../components/ParticleBackground'
import { CosmicCursorTrail } from '../components/CosmicCursorTrail'
import NotificationPanel from '../components/NotificationPanel'
import CommandPalette from '../components/CommandPalette'
import SolarSystemView from '../components/solar-system/SolarSystemView'
import { useNotificationContext } from '../context/NotificationContext'
import { useViewStore } from '../store/viewStore'

interface DashboardLayoutProps {
    children: React.ReactNode
    activeTab: string
    onTabChange: (tab: any) => void
    isConnected: boolean
    commandPaletteOpen: boolean
    setCommandPaletteOpen: (open: boolean) => void
    commands: any[]
    stats?: any
    onDomainSelect?: (domain: string) => void
}

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({
    children,
    activeTab,
    onTabChange,
    isConnected,
    commandPaletteOpen,
    setCommandPaletteOpen,
    commands,
    stats,
    onDomainSelect
}) => {
    const notifications = useNotificationContext()
    const viewMode = useViewStore(state => state.mode)

    return (
        <div className="min-h-screen relative overflow-hidden transition-colors duration-500" style={{ backgroundColor: "var(--theme-bg-primary)" }}>
            <ParticleBackground />
            <CosmicCursorTrail />
            <SettingsPanel />

            <CommandPalette
                isOpen={commandPaletteOpen}
                onClose={() => setCommandPaletteOpen(false)}
                commands={commands}
            />

            <NotificationPanel
                notifications={notifications.notifications}
                onDismiss={notifications.removeNotification}
                onClearAll={notifications.clearAll}
                soundEnabled={notifications.soundEnabled}
                onToggleSound={notifications.toggleSound}
            />

            <div className="relative z-10">
                <Header
                    isConnected={isConnected}
                    activeTab={activeTab}
                    onTabChange={onTabChange}
                    onOpenCommandPalette={() => setCommandPaletteOpen(true)}
                />

                <main className={viewMode === 'cosmic' && (activeTab === 'graph' || activeTab === 'analytics') ? "w-full h-screen pt-[64px] overflow-hidden" : "container mx-auto px-4 py-6"}>
                    {/* Cosmic View Background */}
                    <div className={`fixed inset-0 z-0 transition-opacity duration-1000 ${viewMode === 'cosmic' && (activeTab === 'overview') ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}>
                        <SolarSystemView onDomainSelect={onDomainSelect} />
                    </div>

                    {/* Main Content */}
                    <div className="relative z-10">
                        {children}
                    </div>
                </main>
            </div>
        </div>
    )
}
