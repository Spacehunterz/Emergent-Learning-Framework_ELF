import React, { createContext, useContext, useRef } from 'react';
import { useCosmicSettings } from './CosmicSettingsContext';

interface CosmicAudioContextType {
    playHover: () => void;
    playClick: () => void;
    playTransition: () => void;
    playToggle: (on: boolean) => void;
}

const CosmicAudioContext = createContext<CosmicAudioContextType | undefined>(undefined);

export const CosmicAudioProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const { audioEnabled } = useCosmicSettings();

    const audioContextRef = useRef<AudioContext | null>(null);

    // Initialize AudioContext lazily
    const getAudioContext = () => {
        if (!audioContextRef.current) {
            audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
        }
        return audioContextRef.current;
    };

    const playTone = (freqStart: number, freqEnd: number, duration: number, type: OscillatorType = 'sine', vol: number = 0.1) => {
        if (!audioEnabled) return;

        try {
            const ctx = getAudioContext();
            if (ctx.state === 'suspended') ctx.resume();

            const osc = ctx.createOscillator();
            const gain = ctx.createGain();

            osc.type = type;
            osc.frequency.setValueAtTime(freqStart, ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(freqEnd, ctx.currentTime + duration);

            gain.gain.setValueAtTime(vol, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);

            osc.connect(gain);
            gain.connect(ctx.destination);

            osc.start();
            osc.stop(ctx.currentTime + duration);
        } catch (e) {
            console.error('Audio play failed', e);
        }
    };

    const playHover = () => {
        // High, very short blip - subtle
        playTone(800, 1200, 0.05, 'sine', 0.05);
    };

    const playClick = () => {
        // Standard interaction - soft chirp
        playTone(600, 300, 0.1, 'sine', 0.1);
    };

    const playToggle = (on: boolean) => {
        if (on) {
            // Power up: Rising pitch "Phaser charge"
            playTone(200, 600, 0.2, 'triangle', 0.1);
        } else {
            // Power down: Falling pitch
            playTone(600, 200, 0.2, 'triangle', 0.1);
        }
    };

    const playTransition = () => {
        // Sci-fi sweep
        playTone(400, 1000, 0.3, 'sine', 0.08);
    };

    return (
        <CosmicAudioContext.Provider value={{ playHover, playClick, playTransition, playToggle }}>
            {children}
        </CosmicAudioContext.Provider>
    );
};

export const useCosmicAudio = () => {
    const context = useContext(CosmicAudioContext);
    if (context === undefined) {
        throw new Error('useCosmicAudio must be used within a CosmicAudioProvider');
    }
    return context;
};
