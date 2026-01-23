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
import { NavigationTabs, TabType } from '../components/NavigationTabs'

import { SetupWizard } from '../components/game/SetupWizard'
import { GameMenu } from '../components/game/GameMenu'


interface DashboardLayoutProps {
    children: React.ReactNode
    activeTab: string
    isConnected: boolean
    commandPaletteOpen: boolean
    setCommandPaletteOpen: (open: boolean) => void
    commands: any[]
    onDomainSelectFromGrid?: (domain: string | null) => void
    onDomainSelectFromSpace?: (domain: string | null) => void
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
    onDomainSelectFromGrid,
    onDomainSelectFromSpace,
    selectedDomain,
    onTabChange
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

                    {/* Navigation Tabs - Always visible */}
                    <div className="sticky top-20 z-[9997] bg-black/40 backdrop-blur-md">
                        <div className="container mx-auto">
                            <NavigationTabs
                                activeTab={activeTab as TabType}
                                onTabChange={(tab) => onTabChange?.(tab)}
                                selectedDomain={selectedDomain}
                                onClearDomain={() => onDomainSelectFromGrid?.(null)}
                            />
                        </div>
                    </div>

                    <main className={viewMode === 'cosmic' && activeTab === 'overview' && !selectedDomain ? "w-full h-screen pt-0 overflow-hidden bg-transparent" : "w-full min-h-screen"}>
                        {/* Overview Tab Handling */}
                        {activeTab === 'overview' && (
                            <>
                                {!selectedDomain ? (
                                    viewMode === 'cosmic' ? (
                                        <>
                                            <div className="fixed inset-0 z-0">
                                                <SolarSystemView
                                                    onDomainSelect={onDomainSelectFromSpace}
                                                    selectedDomain={selectedDomain}
                                                />
                                            </div>
                                        </>
                                    ) : (
                                        <GridView onDomainSelect={onDomainSelectFromGrid} />
                                    )
                                ) : (
                                    viewMode === 'cosmic' ? (
                                        <>
                                            <div className="fixed inset-0 z-0">
                                                <SolarSystemView
                                                    onDomainSelect={onDomainSelectFromSpace}
                                                    selectedDomain={selectedDomain}
                                                />
                                            </div>
                                        </>
                                    ) : (
                                        <div
                                            className="relative z-10 container mx-auto px-4 py-8 pt-24 h-screen max-h-screen overflow-y-auto custom-scrollbar cursor-default pb-24"
                                            onClick={() => onDomainSelectFromGrid?.(null)}
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
                            <div
                                className="fixed inset-0 z-10 pt-[120px] bg-black/40 backdrop-blur-sm animate-fade-in cursor-default"
                                onClick={(e) => {
                                    if (e.target === e.currentTarget && onTabChange) {
                                        onTabChange('overview');
                                    }
                                }}
                            >
                                <CosmicGraphView
                                    onNodeClick={(node) => {
                                        // Domain selection from graph navigates to heuristics tab
                                        if (onDomainSelectFromGrid && node.domain) onDomainSelectFromGrid(node.domain);
                                    }}
                                />
                            </div>
                        )}

                        {/* Cosmic Analytics View */}
                        {activeTab === 'analytics' && (
                            <div
                                className="fixed inset-0 z-10 pt-[120px] bg-black/80 backdrop-blur-md animate-fade-in cursor-default"
                                onClick={(e) => {
                                    if (e.target === e.currentTarget && onTabChange) {
                                        onTabChange('overview');
                                    }
                                }}
                            >
                                <CosmicAnalyticsView
                                    onNavigate={(tab, domain) => {
                                        onTabChange?.(tab);
                                        if (domain) {
                                            onDomainSelectFromGrid?.(domain);
                                        }
                                    }}
                                />
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
