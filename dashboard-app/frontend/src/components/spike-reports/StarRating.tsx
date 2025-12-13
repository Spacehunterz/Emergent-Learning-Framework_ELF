import { useState } from 'react'
import { Star } from 'lucide-react'
import { StarRatingProps } from './types'

export default function StarRating({ score, onChange, loading }: StarRatingProps) {
  const [hover, setHover] = useState<number | null>(null)

  return (
    <div className="flex items-center space-x-1">
      {[1, 2, 3, 4, 5].map(star => (
        <button
          key={star}
          onClick={(e) => { e.stopPropagation(); onChange?.(star) }}
          onMouseEnter={() => setHover(star)}
          onMouseLeave={() => setHover(null)}
          disabled={loading}
          className="transition-colors disabled:opacity-50"
        >
          <Star
            className={`w-4 h-4 ${
              (hover !== null ? star <= hover : star <= score)
                ? 'fill-amber-400 text-amber-400'
                : 'text-slate-500'
            }`}
          />
        </button>
      ))}
    </div>
  )
}
