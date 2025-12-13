import { NodePaletteProps } from './types'

export default function NodePalette({ nodeTypes, onAddNode }: NodePaletteProps) {
  return (
    <div className="absolute top-2 left-2 flex space-x-2 z-10">
      {Object.entries(nodeTypes).map(([type, config]) => {
        const Icon = config.icon
        return (
          <button
            key={type}
            onClick={() => onAddNode(type)}
            className={`flex items-center space-x-1 px-2 py-1 ${config.color} text-white rounded text-xs font-medium hover:opacity-80 transition`}
          >
            <Icon className="w-3 h-3" />
            <span>{config.label}</span>
          </button>
        )
      })}
    </div>
  )
}
