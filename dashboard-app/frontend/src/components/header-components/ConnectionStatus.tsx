interface ConnectionStatusProps {
  isConnected: boolean
}

export default function ConnectionStatus({ isConnected }: ConnectionStatusProps) {
  return (
    <div className={
      isConnected
        ? 'flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-400'
        : 'flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium bg-red-500/20 text-red-400'
    }>
      <span className={isConnected ? 'w-2 h-2 rounded-full bg-emerald-400 live-indicator' : 'w-2 h-2 rounded-full bg-red-400'} />
      <span>{isConnected ? 'Live' : 'Disconnected'}</span>
    </div>
  )
}
