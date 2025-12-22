import React, { createContext, useContext, useState, useEffect } from 'react';


type PerformanceMode = 'low' | 'medium' | 'high';
type ViewMode = 'cosmic' | 'grid';

interface CosmicSettings {
    trailsEnabled: boolean;
    audioEnabled: boolean;
    performanceMode: PerformanceMode;
    viewMode: ViewMode;
    setTrailsEnabled: (enabled: boolean) => void;
    setAudioEnabled: (enabled: boolean) => void;
    setPerformanceMode: (mode: PerformanceMode) => void;
    setViewMode: (mode: ViewMode) => void;
}

const CosmicSettingsContext = createContext<CosmicSettings | undefined>(undefined);

export const CosmicSettingsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {


    const [trailsEnabled, setTrailsEnabled] = useState<boolean>(() => {
        const saved = localStorage.getItem('cosmic_trailsEnabled');
        return saved !== null ? JSON.parse(saved) : true;
    });

    const [audioEnabled, setAudioEnabled] = useState<boolean>(() => {
        const saved = localStorage.getItem('cosmic_audioEnabled');
        return saved !== null ? JSON.parse(saved) : true;
    });

    const [performanceMode, setPerformanceMode] = useState<PerformanceMode>(() => {
        return (localStorage.getItem('cosmic_performanceMode') as PerformanceMode) || 'high';
    });

    const [viewMode, setViewMode] = useState<ViewMode>(() => {
        return (localStorage.getItem('cosmic_viewMode') as ViewMode) || 'grid';
    });



    useEffect(() => {
        localStorage.setItem('cosmic_trailsEnabled', JSON.stringify(trailsEnabled));
    }, [trailsEnabled]);

    useEffect(() => {
        localStorage.setItem('cosmic_audioEnabled', JSON.stringify(audioEnabled));
    }, [audioEnabled]);

    useEffect(() => {
        localStorage.setItem('cosmic_performanceMode', performanceMode);
    }, [performanceMode]);

    useEffect(() => {
        localStorage.setItem('cosmic_viewMode', viewMode);
    }, [viewMode]);

    return (
        <CosmicSettingsContext.Provider value={{
            trailsEnabled,
            audioEnabled,
            performanceMode,
            viewMode,
            setTrailsEnabled,
            setAudioEnabled,
            setPerformanceMode,
            setViewMode
        }}>
            {children}
        </CosmicSettingsContext.Provider>
    );
};

export const useCosmicSettings = () => {
    const context = useContext(CosmicSettingsContext);
    if (context === undefined) {
        throw new Error('useCosmicSettings must be used within a CosmicSettingsProvider');
    }
    return context;
};
