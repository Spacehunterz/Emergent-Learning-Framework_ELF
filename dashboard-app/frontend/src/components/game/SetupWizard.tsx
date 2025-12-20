import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { AlertCircle, Check, Loader2, Sparkles, Wand2, X } from 'lucide-react'
import { useGame } from '../../context/GameContext'

const SETUP_API = '/api/setup'

interface SetupStatus {
    configured: boolean
    missing: string[]
    is_placeholder: boolean
}

export function SetupWizard() {
    const { isSetupOpen, setIsSetupOpen } = useGame()
    const [status, setStatus] = useState<SetupStatus | null>(null)
    const [clientId, setClientId] = useState('')
    const [clientSecret, setClientSecret] = useState('')
    const [isSaving, setIsSaving] = useState(false)
    const [saveError, setSaveError] = useState<string | null>(null)
    const [waitingForRestart, setWaitingForRestart] = useState(false)

    // Check status on mount (but don't open)
    useEffect(() => {
        checkStatus()
    }, [])

    const checkStatus = async () => {
        try {
            const res = await fetch(`${SETUP_API}/status`)
            if (res.ok) {
                const data = await res.json()
                setStatus(data)
                // Removed auto-open logic
            }
        } catch (e) {
            console.error("Failed to check setup status", e)
        }
    }

    const handleSave = async () => {
        setIsSaving(true)
        setSaveError(null)

        try {
            const res = await fetch(`${SETUP_API}/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    client_id: clientId,
                    client_secret: clientSecret
                })
            })

            const data = await res.json()
            if (res.ok && data.success) {
                setWaitingForRestart(true)
            } else {
                setSaveError(data.message || "Failed to save configuration")
            }
        } catch (e) {
            setSaveError("Network error saving configuration")
        } finally {
            setIsSaving(false)
        }
    }

    // Auto-Link Generator
    // Must match callback in backend!
    const callbackUrl = "http://localhost:8888/api/auth/callback"
    const createAppLink = `https://github.com/settings/applications/new?oauth_application[name]=Emergent%20Dashboard&oauth_application[homepage_url]=http://localhost:3001&oauth_application[callback_url]=${encodeURIComponent(callbackUrl)}`

    if (!status || status.configured) return null
    if (!isSetupOpen) return null

    return (
        <div className="fixed inset-0 z-[100001] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="w-full max-w-2xl bg-slate-900 border border-slate-700/50 rounded-2xl shadow-2xl overflow-hidden relative"
            >
                {/* Close Button */}
                <button
                    onClick={() => setIsSetupOpen(false)}
                    className="absolute top-4 right-4 p-2 text-slate-500 hover:text-white transition-colors"
                >
                    <X className="w-5 h-5" />
                </button>
                {/* Header */}
                <div className="bg-slate-800/50 p-6 border-b border-white/5 flex items-center gap-4">
                    <div className="p-3 rounded-lg bg-cyan-500/10 text-cyan-400">
                        <Wand2 className="w-6 h-6" />
                    </div>
                    <div>
                        <h2 className="text-xl font-bold text-white">Setup Required</h2>
                        <p className="text-sm text-slate-400">Configure GitHub Integration to enable all features</p>
                    </div>
                </div>

                {/* Content */}
                <div className="p-6 space-y-6">
                    {waitingForRestart ? (
                        <div className="text-center py-12 space-y-4">
                            <div className="w-16 h-16 mx-auto rounded-full bg-green-500/20 flex items-center justify-center text-green-400">
                                <Check className="w-8 h-8" />
                            </div>
                            <h3 className="text-xl font-medium text-white">Configuration Saved!</h3>
                            <p className="text-slate-300 max-w-md mx-auto">
                                Please <strong className="text-white">restart your backend server</strong> (Ctrl+C and run again) to apply the changes.
                            </p>
                            <div className="pt-4">
                                <button
                                    onClick={() => window.location.reload()}
                                    className="px-6 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-white transition-colors"
                                >
                                    I have restarted (Reload Page)
                                </button>
                            </div>
                        </div>
                    ) : (
                        <>
                            <div className="bg-amber-900/20 border border-amber-500/20 rounded-lg p-4 flex gap-3 text-amber-200">
                                <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
                                <div className="text-sm">
                                    <p className="font-medium">Missing Keys Detected</p>
                                    <ul className="list-disc list-inside opacity-80 mt-1">
                                        {status.missing.map(m => (
                                            <li key={m}>{m}</li>
                                        ))}
                                    </ul>
                                </div>
                            </div>

                            <div className="space-y-4">
                                <div>
                                    <h3 className="text-sm font-medium text-slate-400 mb-2">Step 1: Create GitHub App</h3>
                                    <a
                                        href={createAppLink}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="flex items-center gap-3 p-4 rounded-xl bg-slate-800 hover:bg-slate-750 border border-slate-700 hover:border-cyan-500/50 transition-all group"
                                    >
                                        <div className="p-2 rounded-lg bg-white/5 group-hover:bg-cyan-500/20 text-slate-300 group-hover:text-cyan-400 transition-colors">
                                            <Sparkles className="w-5 h-5" />
                                        </div>
                                        <div>
                                            <div className="font-medium text-white group-hover:text-cyan-400 transition-colors">Click here to generate OAuth App</div>
                                            <div className="text-xs text-slate-500">Opens GitHub with pre-filled settings</div>
                                        </div>
                                    </a>
                                </div>

                                <div>
                                    <h3 className="text-sm font-medium text-slate-400 mb-2">Step 2: Enter Credentials</h3>
                                    <div className="space-y-3">
                                        <div>
                                            <label className="text-xs text-slate-500 mb-1 block">Client ID</label>
                                            <input
                                                type="text"
                                                value={clientId}
                                                onChange={e => setClientId(e.target.value)}
                                                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500/50"
                                                placeholder="e.g. Ov23..."
                                            />
                                        </div>
                                        <div>
                                            <label className="text-xs text-slate-500 mb-1 block">Client Secret</label>
                                            <input
                                                type="text"
                                                value={clientSecret}
                                                onChange={e => setClientSecret(e.target.value)}
                                                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500/50"
                                                placeholder="e.g. 1a2b3c..."
                                            />
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {saveError && (
                                <div className="text-red-400 text-sm bg-red-900/20 p-3 rounded-lg border border-red-500/20">
                                    {saveError}
                                </div>
                            )}

                            <div className="flex justify-between pt-2 items-center">
                                <button
                                    onClick={() => {
                                        setClientId("mock")
                                        setClientSecret("mock")
                                        // Trigger auto-save effect or just call handleSave immediately next render? 
                                        // Setting state is async. Let's make a dedicated function or use raw values.
                                        // We can just call the api directly here but handleSave uses state.
                                        // Easier:
                                    }}
                                    className="text-xs text-slate-500 hover:text-slate-300 underline"
                                >
                                    Skip Setup (Demo Mode)
                                </button>

                                <div className="flex gap-3">
                                    {clientId === "mock" && (
                                        <div className="px-3 py-2 text-xs text-amber-400 bg-amber-500/10 rounded border border-amber-500/20 flex items-center gap-2">
                                            <AlertCircle className="w-3 h-3" />
                                            Demo Mode Active
                                        </div>
                                    )}

                                    <button
                                        onClick={handleSave}
                                        disabled={!clientId || !clientSecret || isSaving}
                                        className="px-6 py-2.5 bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 disabled:cursor-not-allowed text-black font-semibold rounded-lg transition-all flex items-center gap-2"
                                    >
                                        {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                                        {clientId === "mock" ? "Effectuate Demo Mode" : "Save Configuration"}
                                    </button>
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </motion.div>
        </div>
    )
}
