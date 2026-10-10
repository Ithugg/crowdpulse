import { LEVEL, formatDuration, formatEta, isAlerting } from '../format'
import type { LevelInfo, ZoneConfig, ZoneState } from '../types'
import { DensityGauge } from './DensityGauge'
import { Sparkline } from './Sparkline'

interface Props {
  zone: ZoneConfig
  state: ZoneState | undefined
  levels: LevelInfo[]
}

function outlook(z: ZoneState, levels: LevelInfo[]): { text: string; tone: string } {
  const safeLimit = levels.find((l) => l.id === 'caution')?.min ?? 4
  if (isAlerting(z.level)) {
    return { text: `Above ${safeLimit}/m² for ${formatDuration(z.above_safe_s)}`, tone: LEVEL[z.level].text }
  }
  if (z.eta_s !== null && z.eta_level) {
    const label = levels.find((l) => l.id === z.eta_level)?.label ?? z.eta_level
    return { text: `${label} in ~${formatEta(z.eta_s)}`, tone: LEVEL[z.eta_level].text }
  }
  if (z.trend_per_min > 0.3) return { text: `Rising +${z.trend_per_min.toFixed(1)} per min`, tone: 'text-muted' }
  if (z.trend_per_min < -0.3) return { text: `Easing ${z.trend_per_min.toFixed(1)} per min`, tone: 'text-muted' }
  return { text: 'Stable', tone: 'text-dim' }
}

export function ZoneCard({ zone, state, levels }: Props) {
  const level = state?.level ?? 'normal'
  const style = LEVEL[level]
  const info = levels.find((l) => l.id === level)
  const view = state ? outlook(state, levels) : null

  return (
    <section
      className={`relative min-w-0 overflow-hidden rounded-lg border bg-panel p-3 transition-colors duration-300 ${
        level === 'critical' ? 'animate-crit border-crit/60' : isAlerting(level) ? style.border : 'border-line'
      }`}
    >
      <span className={`absolute inset-y-0 left-0 w-[3px] ${style.dot}`} />
      <header className="flex items-center justify-between gap-2">
        <h3 className="truncate text-[13px] font-semibold">{zone.name}</h3>
        <span
          className={`shrink-0 cursor-help rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${style.bg} ${style.text}`}
          title={info ? `${info.what}\nSource: ${info.source}` : undefined}
        >
          {info?.label ?? level}
        </span>
      </header>

      <div className="mt-1.5 flex items-end justify-between gap-2">
        <p className="flex items-baseline gap-1.5">
          <span className={`num text-[28px] font-semibold leading-none ${style.text}`}>
            {state ? state.density.toFixed(1) : '–'}
          </span>
          <span className="text-[11px] leading-tight text-muted" title="Peak local density inside the zone, measured on the ground plane (Helbing et al. 2007 kernel, R = 1 m)">
            people/m²
            <br />
            <span className="text-dim">local peak</span>
          </span>
        </p>
        <p className="num text-right text-[11px] leading-tight text-muted">
          {state?.count ?? 0} people
          <br />
          <span className="text-dim" title="Floor area of the zone, measured from the camera calibration">
            {zone.area_m2 !== null ? `${Math.round(zone.area_m2)} m² measured` : 'area not measured'}
          </span>
        </p>
      </div>

      <DensityGauge density={state?.density ?? 0} levels={levels} />
      <Sparkline values={state?.history ?? []} levels={levels} color={style.hex} />

      <p className={`mt-1 truncate text-xs font-medium ${view?.tone ?? 'text-dim'}`}>{view?.text ?? 'Waiting for data'}</p>
    </section>
  )
}
