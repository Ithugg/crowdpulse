import { LEVEL } from '../format'
import type { LevelInfo } from '../types'

interface Props {
  values: number[]
  levels: LevelInfo[]
  color: string
}

const W = 240
const H = 30

/** Last minute of density for one zone. The scale follows the data; a level line appears when it is in range. */
export function Sparkline({ values, levels, color }: Props) {
  const top = Math.max(1, ...values) * 1.25
  const y = (v: number) => H - 2 - (v / top) * (H - 4)
  const x = (i: number) => (values.length <= 1 ? W : (i / (values.length - 1)) * W)
  const line = values.map((v, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')

  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="mt-1 h-[26px] w-full [@media(max-height:820px)]:hidden" aria-hidden>
      {levels
        .filter((level) => level.min > 0 && level.min < top)
        .map((level) => (
          <line
            key={level.id}
            x1="0" x2={W} y1={y(level.min)} y2={y(level.min)}
            stroke={LEVEL[level.id].hex} strokeOpacity="0.5" strokeDasharray="3 4" vectorEffect="non-scaling-stroke"
          />
        ))}
      {values.length > 1 && (
        <>
          <path d={`${line} L${W},${H} L0,${H} Z`} fill={color} fillOpacity="0.12" />
          <path d={line} fill="none" stroke={color} strokeWidth="1.75" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        </>
      )}
    </svg>
  )
}
