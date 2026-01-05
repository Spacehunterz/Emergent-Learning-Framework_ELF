import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { usePlayerWeaponStore } from '../components/game/systems/PlayerWeaponStore';



interface GameState {
    score: number;
    level: number;

    unlockedCursors: string[];
    githubUser: {
        username: string;
        avatar_url?: string;
    } | null;
    isMenuOpen: boolean;
    isSetupOpen: boolean;
    isGameEnabled: boolean;
    activeShip: 'default' | 'star_ship' | 'drone' | 'glitch';
    activeTrail: 'none' | 'cyan' | 'star' | 'plasma' | 'fire';
    shields: number;
    viewMode: 'static' | 'cockpit';
    isGameOver: boolean;
    lastHitTime: number;
}

interface GameContextType extends GameState {
    setScore: (score: number) => void;
    addScore: (points: number) => void;
    damageShields: (amount: number) => void;
    rechargeShields: (amount: number) => void;
    resetShields: () => void;
    levelUp: () => void;

    toggleMenu: () => void;
    verifyStar: () => Promise<void>;
    checkAuth: () => Promise<void>;
    login: () => void;
    logout: () => void;
    setIsSetupOpen: (open: boolean) => void;
    toggleGameMode: () => void;
    setGameEnabled: (enabled: boolean) => void;
    setActiveShip: (ship: 'default' | 'star_ship' | 'drone' | 'glitch') => void;
    setActiveTrail: (trail: 'none' | 'cyan' | 'star' | 'plasma' | 'fire') => void;
    toggleViewMode: () => void;
    setGameOver: (isOver: boolean) => void;
    restartGame: () => void;
    lastHitTime: number;
    triggerPlayerHit: () => void;
}

const GameContext = createContext<GameContextType | undefined>(undefined);

export const GameProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [state, setState] = useState<GameState>(() => ({
        score: 0,
        level: 1,
        unlockedCursors: ['default'],
        githubUser: null,
        isMenuOpen: false,
        isSetupOpen: false,
        isGameEnabled: false,
        activeShip: (localStorage.getItem('gameState_activeShip') as 'default' | 'star_ship' | 'drone' | 'glitch') || 'default',
        activeTrail: (localStorage.getItem('gameState_activeTrail') as 'none' | 'cyan' | 'star' | 'plasma' | 'fire') || 'none',
        shields: 100,
        viewMode: (localStorage.getItem('gameState_viewMode') as 'static' | 'cockpit') || 'cockpit',
        isGameOver: false,
        lastHitTime: 0
    }));

    // Fetch initial state from backend
    const checkAuth = useCallback(async () => {
        try {
            // 1. Check Auth Session
            const authRes = await fetch('http://localhost:8888/api/auth/me', { credentials: 'include' });
            const authData = await authRes.json();

            if (authData.is_authenticated) {
                // 2. Fetch Authoritative Game State
                const gameRes = await fetch('http://localhost:8888/api/game/state', { credentials: 'include' });
                const gameData = await gameRes.json();

                setState(prev => ({
                    ...prev,
                    githubUser: { username: authData.username, avatar_url: authData.avatar_url },
                    score: gameData.score,
                    level: gameData.level || 1,

                    unlockedCursors: gameData.unlocked_cursors || ['default'],
                }));
            }
        } catch (err) {
            console.error("Failed to sync game state:", err);
        }
    }, []);

    useEffect(() => {
        checkAuth();
    }, [checkAuth]);

    useEffect(() => {
        localStorage.setItem('gameState_activeShip', state.activeShip);
    }, [state.activeShip]);

    useEffect(() => {
        localStorage.setItem('gameState_activeTrail', state.activeTrail);
    }, [state.activeTrail]);

    useEffect(() => {
        localStorage.setItem('gameState_viewMode', state.viewMode);
    }, [state.viewMode]);

    useEffect(() => {
        if (state.activeShip !== 'default') {
            document.documentElement.classList.add('cosmic-cursor-hidden');
        } else {
            document.documentElement.classList.remove('cosmic-cursor-hidden');
        }
    }, [state.activeShip]);

    // Sync Score to Backend 
    const addScore = (points: number) => {
        setState(prev => {
            const newScore = prev.score + points;
            // Optimistic update
            fetch('http://localhost:8888/api/game/sync', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ score_delta: points })
            }).catch(console.error);

            return { ...prev, score: newScore };
        });
    };

    const setScore = (score: number) => {
        setState(prev => ({ ...prev, score }));
    };



    const verifyStar = async () => {
        try {
            const res = await fetch('http://localhost:8888/api/game/verify-star', { method: 'POST', credentials: 'include' });
            const data = await res.json();
            if (data.success) {
                await checkAuth(); // Refresh state
                alert(data.message);
            } else {
                alert(data.message);
            }
        } catch (e) {
            alert("Verification failed");
        }
    };

    const login = () => {
        window.location.href = 'http://localhost:8888/api/auth/login';
    };

    const logout = async () => {
        await fetch('http://localhost:8888/api/auth/logout', { method: 'POST', credentials: 'include' });
        setState(prev => ({
            ...prev,
            githubUser: null,

            score: 0
        }));
    };

    const toggleMenu = () => setState(prev => ({ ...prev, isMenuOpen: !prev.isMenuOpen }));
    const setIsSetupOpen = (open: boolean) => setState(prev => ({ ...prev, isSetupOpen: open }));
    const setGameEnabled = (enabled: boolean) => setState(prev => ({
        ...prev,
        isGameEnabled: enabled,
        isMenuOpen: enabled ? prev.isMenuOpen : false,
        isSetupOpen: enabled ? prev.isSetupOpen : false,
        isGameOver: enabled ? prev.isGameOver : false
    }));
    const toggleGameMode = () => setGameEnabled(!state.isGameEnabled);
    const setActiveShip = (ship: 'default' | 'star_ship' | 'drone' | 'glitch') => setState(prev => ({ ...prev, activeShip: ship }));
    const setActiveTrail = (trail: 'none' | 'cyan' | 'star' | 'plasma' | 'fire') => setState(prev => ({ ...prev, activeTrail: trail }));

    // Get Upgrades
    const shipUpgrades = usePlayerWeaponStore(s => s.shipUpgrades)
    const maxShields = 100 + (shipUpgrades?.shield || 0) * 25 // +25 per level

    const rechargeShields = (amount: number) => setState(prev => ({ ...prev, shields: Math.min(maxShields, prev.shields + amount) }));
    const resetShields = () => setState(prev => ({ ...prev, shields: maxShields }));
    const levelUp = () => setState(prev => ({ ...prev, level: prev.level + 1 }));

    const setGameOver = (isOver: boolean) => setState(prev => ({ ...prev, isGameOver: isOver }));

    const restartGame = () => setState(prev => ({
        ...prev,
        isGameOver: false,
        score: 0,
        level: 1,
        shields: maxShields
    }));

    // Update damage logic to trigger Game Over instead of disabling game
    const damageShields = (amount: number) => setState(prev => {
        const newShields = Math.max(0, prev.shields - amount);
        // Note: Actual Hull damage logic is in PlayerShip local state.
        // We need to synchronize them or move Hull to Context.
        // For now, let's keep Shield logic here.
        return { ...prev, shields: newShields };
    });

    return (
        <GameContext.Provider value={{
            ...state,
            setScore,
            addScore,

            toggleMenu,
            verifyStar,
            checkAuth,
            login,
            logout,
            setIsSetupOpen,
            toggleGameMode,
            setGameEnabled,
            setActiveShip,
            setActiveTrail,
            damageShields,
            rechargeShields,
            resetShields,
            levelUp,
            viewMode: state.viewMode,
            toggleViewMode: () => setState(prev => ({ ...prev, viewMode: prev.viewMode === 'static' ? 'cockpit' : 'static' })),
            isGameOver: state.isGameOver,
            setGameOver,
            restartGame,
            lastHitTime: state.lastHitTime,
            triggerPlayerHit: () => setState(prev => ({ ...prev, lastHitTime: Date.now() })),
            shields: state.shields
        }}>
            {children}
        </GameContext.Provider>
    );
};

export const useGame = () => {
    const context = useContext(GameContext);
    if (context === undefined) {
        throw new Error('useGame must be used within a GameProvider');
    }
    return context;
};
