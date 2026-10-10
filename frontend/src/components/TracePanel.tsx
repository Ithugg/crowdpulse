import { LEVEL_COLOR, isAlerting } from '../format'
import type { ConfigMsg, StateMsg } from '../types'

const W = 600
const H = 100
const SPAN = 59 // history holds up to 60 samples, one per second

/** Strip chart: the last minute of every zone's density against the level lines. */
export function TracePanel({ config, state, selected }: { config: ConfigMsg; state: StateMsg | null; selected: string | null }) {
  const zones = state?.zones ?? []
  const peak = Math.max(0, ...zones.flatMap((z) => z.history))
  // The action level is always on the chart, so the trace shows how far below it a zone is.
  const action = config.levels.find((l) => l.id === 'caution')?.min ?? 4
  const top = Math.max(action * 1.1, peak * 1.2)
  const y = (v: number) => H - (v / top) * H
  const lines = config.levels.filter((l) => l.min > 0 && l.min < top)

  return (
    <section className="tile" style={{ flex: 1 }}>
      <div className="strip">
        <span className="title">Trace</span>
        <span className="as-is">last 60 s, people/m²</span>
      </div>

      <div className="trace">
        <div className="trace-plot">
          <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" aria-hidden>
            <line x1="0" x2={W} y1={H} y2={H} stroke="var(--color-rule-strong)" vectorEffect="non-scaling-stroke" />
            <line x1="0" x2="0" y1="0" y2={H} stroke="var(--color-rule-strong)" vectorEffect="non-scaling-stroke" />
            {[1, 2].map((t) => (
              <line key={t} x1={(W * t) / 2} x2={(W * t) / 2} y1="0" y2={H} stroke="var(--color-rule)" vectorEffect="non-scaling-stroke" />
            ))}
            {lines.map((l) => (
              <line
                key={l.id}
                x1="0" x2={W} y1={y(l.min)} y2={y(l.min)}
                stroke={isAlerting(l.id) ? LEVEL_COLOR[l.id] : 'var(--color-rule-strong)'}
                strokeOpacity={isAlerting(l.id) ? 0.6 : 1}
                strokeDasharray={isAlerting(l.id) ? '6 4' : '2 4'}
                vectorEffect="non-scaling-stroke"
              />
            ))}
            {zones.map((z) => {
              if (z.history.length < 2) return null
              const start = SPAN - (z.history.length - 1)
              const d = z.history.map((v, i) => `${i === 0 ? 'M' : 'L'}${(((start + i) / SPAN) * W).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
              const chosen = z.id === selected
              return (
                <path
                  key={z.id}
                  d={d}
                  fill="none"
                  stroke={isAlerting(z.level) ? LEVEL_COLOR[z.level] : chosen ? 'var(--color-ink)' : 'var(--color-faint)'}
                  strokeWidth={chosen ? 2 : 1}
                  vectorEffect="non-scaling-stroke"
                />
              )
            })}
          </svg>

          <span className="ylab" style={{ top: 0 }}>{top.toFixed(1)}</span>
          {lines.map((l) => (
            <span key={l.id} className="ylab" style={{ top: `${(y(l.min) / H) * 100}%`, color: isAlerting(l.id) ? LEVEL_COLOR[l.id] : undefined }}>
              {l.min}
            </span>
          ))}
          {lines.filter((l) => isAlerting(l.id)).map((l) => (
            <span key={l.id} className="linelab" style={{ top: `${(y(l.min) / H) * 100}%`, color: LEVEL_COLOR[l.id] }}>
              {l.id === 'caution' ? 'ACTION LEVEL' : l.label.toUpperCase()}
            </span>
          ))}
          <span className="ylab" style={{ top: '100%' }}>0</span>
          <span className="xlab" style={{ left: 0 }}>−60 s</span>
          <span className="xlab" style={{ left: '50%', transform: 'translateX(-50%)' }}>−30 s</span>
          <span className="xlab" style={{ right: 0 }}>now</span>
        </div>

        <ul className="trace-list">
          {zones.map((z, i) => (
            <li key={z.id} data-level={z.level} data-alerting={isAlerting(z.level)} aria-current={z.id === selected}>
              <span>Z{i + 1}</span>
              <span>{z.density.toFixed(2)}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
