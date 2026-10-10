import { LEVEL } from '../format'
import type { LevelInfo } from '../types'

const SCALE_MAX = 7 // people/m², one step past critical

/** Where a zone sits on the research density scale: coloured bands with a marker at the current value. */
export function DensityGauge({ density, levels }: { density: number; levels: LevelInfo[] }) {
  const position = Math.min(density / SCALE_MAX, 1) * 100

  return (
    <div className="mt-2" aria-hidden>
      <div className="relative h-1.5">
        <div className="flex h-full gap-px overflow-hidden rounded-full">
          {levels.map((level, i) => {
            const end = levels[i + 1]?.min ?? SCALE_MAX
            return (
              <span
                key={level.id}
                className={LEVEL[level.id].dot}
                style={{ width: `${((end - level.min) / SCALE_MAX) * 100}%`, opacity: level.id === 'normal' ? 0.3 : 0.6 }}
                title={`${level.label}: from ${level.min}/m². ${level.what}\nSource: ${level.source}`}
              />
            )
          })}
        </div>
        <span
          className="absolute -top-1 h-3.5 w-[3px] -translate-x-1/2 rounded-full bg-ink shadow-[0_0_0_2px_var(--color-panel)] transition-[left] duration-500"
          style={{ left: `${position}%` }}
        />
      </div>
      <div className="num relative mt-0.5 h-3 text-[10px] text-dim">
        {levels.slice(1).map((level) => (
          <span key={level.id} className="absolute -translate-x-1/2" style={{ left: `${(level.min / SCALE_MAX) * 100}%` }}>
            {level.min}
          </span>
        ))}
      </div>
    </div>
  )
}
