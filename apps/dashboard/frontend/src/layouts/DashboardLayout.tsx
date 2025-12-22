import React from 'react'
import Header from '../components/Header'
import { ParticleBackground } from '../components/ParticleBackground'
import { UfoCursor } from '../components/ui/UfoCursor'
import { NotificationPanel } from '../components/NotificationPanel'
import { CommandPalette } from '../components/CommandPalette'
import SolarSystemView from '../components/solar-system/SolarSystemView'
import { GridView } from '../components/overview/GridView'
import { CosmicGraphView } from '../components/cosmic-view/CosmicGraphView'
import { CosmicAnalyticsView } from '../components/cosmic-view/CosmicAnalyticsView'
import { useNotificationContext } from '../context/NotificationContext'
import { useCosmicSettings } from '../context/CosmicSettingsContext'


import { SetupWizard } from '../components/game/SetupWizard'
import { GameMenu } from '../components/game/GameMenu'


interface DashboardLayoutProps {
    children: React.ReactNode
    activeTab: string
    isConnected: boolean
    commandPaletteOpen: boolean
    setCommandPaletteOpen: (open: boolean) => void
    commands: any[]
    onDomainSelect?: (domain: string) => void
    onTabChange?: (tab: string) => void
    selectedDomain?: string | null
}

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({
    children,
    activeTab,
    isConnected,
    commandPaletteOpen,
    setCommandPaletteOpen,
    commands,
    onDomainSelect,
    selectedDomain
}) => {
    const notifications = useNotificationContext()
    const { viewMode } = useCosmicSettings()

    return (

        <>
            <SetupWizard />
            <div className="min-h-screen relative overflow-hidden transition-colors duration-500" style={{ backgroundColor: "var(--theme-bg-primary)" }}>
                <div className="absolute inset-0 z-0 opacity-100 pointer-events-none">
                    <ParticleBackground />
                </div>
                <UfoCursor />
                <GameMenu />

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
                        onOpenCommandPalette={() => setCommandPaletteOpen(true)}
                    />

                    <main className={viewMode === 'cosmic' && activeTab === 'overview' && !selectedDomain ? "w-full h-screen pt-0 overflow-hidden bg-transparent" : "w-full min-h-screen"}>
                        {/* Overview Tab Handling */}
                        {activeTab === 'overview' && (
                            <>
                                {!selectedDomain ? (
                                    viewMode === 'cosmic' ? (
                                        <>
                                            <div className="fixed inset-0 z-0">
                                                <SolarSystemView
                                                    onDomainSelect={onDomainSelect}
                                                    selectedDomain={selectedDomain}
                                                />
                                            </div>
                                        </>
                                    ) : (
                                        <GridView onDomainSelect={onDomainSelect} />
                                    )
                                ) : (
                                    viewMode === 'cosmic' ? (
                                        <>
                                            <div className="fixed inset-0 z-0">
                                                <SolarSystemView
                                                    onDomainSelect={onDomainSelect}
                                                    selectedDomain={selectedDomain}
                                                />
                                            </div>
                                        </>
                                    ) : (
                                        <div
                                            className="relative z-10 container mx-auto px-4 py-8 pt-24 h-screen max-h-screen overflow-y-auto custom-scrollbar cursor-default pb-24"
                                            onClick={() => onDomainSelect?.(null as any)}
                                        >
                                            <div
                                                className="glass-panel p-6 rounded-xl"
                                                onClick={(e) => e.stopPropagation()}
                                            >
                                                {children}
                                            </div>
                                        </div>
                                    )
                                )}
                            </>
                        )}

                        {/* Cosmic Views */}
                        {/* Cosmic Graph View */}
                        {activeTab === 'graph' && (
                            <div className="fixed inset-0 z-10 pt-[120px] bg-black/40 backdrop-blur-sm animate-fade-in">
                                <CosmicGraphView
                                    onNodeClick={(node) => {
                                        if (onDomainSelect && node.domain) onDomainSelect(node.domain);
                                    }}
                                />
                            </div>
                        )}

                        {/* Cosmic Analytics View */}
                        {activeTab === 'analytics' && (
                            <div className="fixed inset-0 z-10 pt-[120px] bg-black/80 backdrop-blur-md animate-fade-in">
                                <CosmicAnalyticsView />
                            </div>
                        )}

                        {/* Fallback for other tabs in cosmic mode - render them in a container */}
                        {activeTab !== 'overview' && activeTab !== 'graph' && activeTab !== 'analytics' && (
                            <div className="relative z-10 container mx-auto px-4 py-8 pt-24 h-full overflow-y-auto custom-scrollbar">
                                <div className="glass-panel p-6 rounded-xl min-h-[calc(100vh-150px)]">
                                    {children}
                                </div>
                            </div>
                        )}
                    </main>
                </div>
            </div>
        </>
    )
}
