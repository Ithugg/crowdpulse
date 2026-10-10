import { LEVEL, formatEta } from '../format'
import type { ZoneConfig, ZoneState } from '../types'
import { Sparkline } from './Sparkline'

interface Props {
  zone: ZoneConfig
  state: ZoneState | undefined
  thresholds: { warn: number; critical: number }
}

function outlook(z: ZoneState): { text: string; tone: string } {
  if (z.level === 'red') return { text: 'Critical now. Act immediately.', tone: 'text-crit' }
  if (z.eta_critical_s !== null) return { text: `Critical in ~${formatEta(z.eta_critical_s)}`, tone: 'text-warn' }
  if (z.trend_per_min > 0.3) return { text: `Rising +${z.trend_per_min.toFixed(1)} per min`, tone: 'text-muted' }
  if (z.trend_per_min < -0.3) return { text: `Easing ${z.trend_per_min.toFixed(1)} per min`, tone: 'text-muted' }
  return { text: 'Stable', tone: 'text-dim' }
}

export function ZoneCard({ zone, state, thresholds }: Props) {
  const level = state?.level ?? 'green'
  const style = LEVEL[level]
  const view = state ? outlook(state) : null

  return (
    <section
      className={`relative min-w-0 overflow-hidden rounded-lg border bg-panel p-3 transition-colors duration-300 ${
        level === 'red' ? 'animate-crit border-crit/60' : level === 'yellow' ? 'border-warn/35' : 'border-line'
      }`}
    >
      <span className={`absolute inset-y-0 left-0 w-[3px] ${style.dot}`} />
      <header className="flex items-center justify-between gap-2">
        <h3 className="truncate text-[13px] font-semibold">{zone.name}</h3>
        <span className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${style.bg} ${style.text}`}>
          {style.label}
        </span>
      </header>

      <div className="mt-1.5 flex items-baseline justify-between gap-2">
        <p className="flex items-baseline gap-1">
          <span className={`num text-[28px] font-semibold leading-none ${style.text}`}>
            {state ? state.density.toFixed(1) : '–'}
          </span>
          <span className="text-[11px] text-muted">people / m²</span>
        </p>
        <p className="num text-right text-[11px] leading-tight text-muted">
          {state?.count ?? 0} people
          <br />
          <span className="text-dim">~{zone.area_m2} m²</span>
        </p>
      </div>

      <div className="mt-1.5">
        <Sparkline values={state?.history ?? []} warn={thresholds.warn} critical={thresholds.critical} color={style.hex} />
      </div>

      <p className={`mt-1 truncate text-xs font-medium ${view?.tone ?? 'text-dim'}`}>{view?.text ?? 'Waiting for data'}</p>
    </section>
  )
}
