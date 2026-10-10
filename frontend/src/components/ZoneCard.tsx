import { LEVEL, formatDuration, formatEta, isAlerting } from '../format'
import type { GateConfig, GateState, LevelInfo, ZoneConfig, ZoneState } from '../types'
import { DensityGauge } from './DensityGauge'
import { Sparkline } from './Sparkline'

interface Props {
  zone: ZoneConfig
  state: ZoneState | undefined
  levels: LevelInfo[]
  flowAvailable: boolean // walking speed can be measured on this camera
  gates: GateConfig[] // gates that feed this zone
  gateState: GateState[]
}

const TURBULENCE_PRESSURE = 0.02 // 1/s², where crowd turbulence began in the Hajj study (Helbing et al. 2007)

/** How the people in the zone are moving: real walking speed, and whether they share a direction. */
function movement(z: ZoneState): { text: string; title: string } {
  if (z.speed_mps === null) return { text: 'flow: too few people', title: 'At least three people must be followed for a second to measure walking speed' }
  const pattern = z.speed_mps < 0.25 ? 'standing' : (z.alignment ?? 0) >= 0.7 ? 'one direction' : (z.alignment ?? 0) >= 0.4 ? 'mixed directions' : 'counter-flow'
  const title = `Average walking speed of the people followed in this zone, in real metres per second. Crowd pressure ${z.pressure?.toFixed(2)} /s² (density × variance of velocity, Helbing et al. 2007).`
  // Crowd pressure is only meaningful once people are packed together.
  if (isAlerting(z.level) && z.pressure !== null && z.pressure > TURBULENCE_PRESSURE) {
    return { text: `${z.speed_mps.toFixed(1)} m/s · turbulence risk`, title }
  }
  return { text: `${z.speed_mps.toFixed(1)} m/s · ${pattern}`, title }
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

export function ZoneCard({ zone, state, levels, flowAvailable, gates, gateState }: Props) {
  const level = state?.level ?? 'normal'
  const style = LEVEL[level]
  const info = levels.find((l) => l.id === level)
  const view = state ? outlook(state, levels) : null
  const flow = state && flowAvailable ? movement(state) : null

  return (
    <section
      className={`min-w-0 rounded-lg border bg-panel p-3 transition-colors duration-300 ${
        level === 'critical' ? 'animate-crit border-crit/60' : isAlerting(level) ? style.border : 'border-line'
      }`}
    >
      <header className="flex items-center justify-between gap-2">
        <h3 className="flex min-w-0 items-center gap-1.5 text-[13px] font-semibold">
          <span className={`h-2 w-2 shrink-0 rounded-full ${style.dot} ${level === 'critical' ? 'animate-pulse' : ''}`} />
          <span className="truncate">{zone.name}</span>
        </h3>
        <span
          className={`shrink-0 cursor-help rounded px-1.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${style.bg} ${style.text}`}
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
        <p className="num shrink-0 text-right text-[13px] font-medium leading-none">
          {state?.count ?? 0} <span className="text-[11px] font-normal text-muted">people</span>
        </p>
      </div>

      {zone.capacity && zone.area_m2 !== null ? (
        <p
          className="mt-1.5 cursor-help truncate text-[11px] text-muted"
          title={`Floor area measured from the camera calibration: ${Math.round(zone.area_m2)} m². Safe capacity = area × 4 people/m², the UK Green Guide safe limit = ${zone.capacity} people.`}
        >
          {Math.round(((state?.count ?? 0) / zone.capacity) * 100)}% of safe capacity ({zone.capacity})
          <span className="text-dim"> · {Math.round(zone.area_m2)} m²</span>
        </p>
      ) : (
        <p className="mt-1.5 cursor-help truncate text-[11px] text-dim" title="This zone is too far from the camera, or the floor is not visible, so its area cannot be measured reliably">
          Area not measured: no capacity figure
        </p>
      )}

      <DensityGauge density={state?.density ?? 0} levels={levels} />
      <Sparkline values={state?.history ?? []} levels={levels} color={style.hex} />

      <div className="mt-1 flex items-baseline justify-between gap-2">
        <p className={`truncate text-xs font-medium ${view?.tone ?? 'text-dim'}`}>{view?.text ?? 'Waiting for data'}</p>
        {flow && (
          <p className="shrink-0 cursor-help text-[11px] text-muted" title={flow.title}>
            {flow.text}
          </p>
        )}
      </div>
      {gates.map((gate) => {
        const g = gateState.find((s) => s.id === gate.id)
        if (!g) return null
        return (
          <p
            key={gate.id}
            className="mt-0.5 cursor-help text-[11px] leading-snug text-brand"
            title="People counted crossing the gate line, averaged over the last minute. The capacity time is a worst case: it assumes everyone who comes in through this gate stays in the zone."
          >
            {gate.name}: {Math.round(g.in_per_min)} in · {Math.round(g.out_per_min)} out /min
            {g.eta_full_s !== null && g.eta_full_s < 1800 && ` · full in ~${formatEta(g.eta_full_s)} if no one leaves`}
          </p>
        )
      })}
    </section>
  )
}
