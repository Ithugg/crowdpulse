import { LEVEL_COLOR, flowPattern, formatEta, isAlerting, levelLabel, outlook } from '../format'
import type { ConfigMsg, GateState, LevelInfo, StateMsg, ZoneConfig, ZoneState } from '../types'
import { Heading } from './CameraPanel'

const SCALE_MAX = 7 // people/m², one step past critical
const TURBULENCE_PRESSURE = 0.02 // 1/s², where crowd turbulence began in the Hajj study (Helbing et al. 2007)

/** 0 to 7 people/m², ticked at every level boundary, with a pointer at the reading. */
function Ruler({ density, levels }: { density: number; levels: LevelInfo[] }) {
  const at = (v: number) => `${(Math.min(v, SCALE_MAX) / SCALE_MAX) * 100}%`
  const bounds = levels.slice(1).map((l) => l.min)

  return (
    <span className="ruler" aria-hidden>
      <span className="base" />
      {levels.filter((l) => isAlerting(l.id)).map((l, i, arr) => (
        <span key={l.id} className="band" style={{ left: at(l.min), width: `${(((arr[i + 1]?.min ?? SCALE_MAX) - l.min) / SCALE_MAX) * 100}%`, background: LEVEL_COLOR[l.id] }} />
      ))}
      {Array.from({ length: SCALE_MAX + 1 }, (_, v) => (
        <span key={v} className={bounds.includes(v) ? 'tick major' : 'tick'} style={{ left: v === SCALE_MAX ? 'calc(100% - 1px)' : at(v) }} />
      ))}
      {bounds.map((v) => (
        <span key={v} className="mark" style={{ left: at(v) }}>
          {v}
        </span>
      ))}
      <span className="pointer" style={{ left: at(density) }} />
    </span>
  )
}

interface RowProps {
  code: string
  zone: ZoneConfig
  z: ZoneState | undefined
  levels: LevelInfo[]
  chosen: boolean
  flowAvailable: boolean
  gates: { name: string; g: GateState | undefined }[]
  onSelect: () => void
}

function ZoneRow({ code, zone, z, levels, chosen, flowAvailable, gates, onSelect }: RowProps) {
  const level = z?.level ?? 'normal'
  const view = z ? outlook(z, levels) : null
  const turbulent = z && isAlerting(z.level) && z.pressure !== null && z.pressure > TURBULENCE_PRESSURE

  return (
    <button type="button" className="zone" data-level={level} aria-pressed={chosen} onClick={onSelect}>
      <span className={chosen ? 'tag' : 'tag hollow'}>{code}</span>

      <span className="zone-main">
        <span className="zone-head">
          <span className="zone-name">{zone.name}</span>
          <span className="zone-state" title={`${levels.find((l) => l.id === level)?.what}\nSource: ${levels.find((l) => l.id === level)?.source}`}>
            <i className="lamp" />
            {levelLabel(levels, level)}
          </span>
        </span>

        <Ruler density={z?.density ?? 0} levels={levels} />

        <span className="zone-detail">
          {!z || !view ? (
            'waiting for data'
          ) : (
            <>
              <span className={view.hot ? 'hot' : undefined}>{view.text}</span>
              {' · '}
              <span className="num">{z.count}</span> {z.count === 1 ? 'person' : 'people'}
              {zone.capacity !== null && zone.area_m2 !== null ? (
                <span title={`Floor area measured from the camera calibration: ${Math.round(zone.area_m2)} m². Capacity here = area × 4 people/m², the action level.`}>
                  {' · '}
                  <span className="num">{Math.round((z.count / zone.capacity) * 100)}%</span> of {zone.capacity} at 4/m²
                  {chosen && (
                    <>
                      {' · '}
                      <span className="num">{Math.round(zone.area_m2)}</span> m² measured
                    </>
                  )}
                </span>
              ) : (
                chosen && <span title="This zone is too far from the camera, or the floor is not visible, so its area cannot be measured reliably"> · area not measured</span>
              )}
              {flowAvailable && z.speed_mps !== null && (
                <span title={`Average walking speed of the people followed in this zone. Crowd pressure ${z.pressure?.toFixed(2)} /s² (density × variance of velocity, Helbing et al. 2007).`}>
                  {' · '}
                  {z.heading_deg !== null && <Heading deg={z.heading_deg} />} <span className="num">{z.speed_mps.toFixed(1)}</span> m/s{' '}
                  {turbulent ? <span className="hot">turbulence risk</span> : flowPattern(z)}
                </span>
              )}
              {gates.map(({ name, g }) =>
                g ? (
                  <span key={name} className="gate" title="People counted crossing the gate line, averaged over the last minute. The time to capacity is a worst case: it assumes nobody leaves.">
                    {' · '}
                    <b>{name}</b>: <span className="num">{Math.round(g.in_per_min)}</span> in, <span className="num">{Math.round(g.out_per_min)}</span> out /min
                    {chosen && g.eta_full_s !== null && g.eta_full_s < 1800 && `, full in ~${formatEta(g.eta_full_s)} if no one leaves`}
                  </span>
                ) : null,
              )}
            </>
          )}
        </span>
      </span>

      <span className="zone-value">
        <span className="num">{z ? z.density.toFixed(1) : '–'}</span>
        <span className="unit">/m²</span>
      </span>
    </button>
  )
}

interface Props {
  config: ConfigMsg
  state: StateMsg | null
  selected: string | null
  onSelect: (zoneId: string) => void
  onScience: () => void
}

/** Every zone as a row of live measurements. The selected row opens up; an alert selects its zone. */
export function ZoneBoard({ config, state, selected, onSelect, onScience }: Props) {
  const live = Object.fromEntries((state?.zones ?? []).map((z) => [z.id, z]))
  const flowAvailable = config.flow && config.calibration.mode === 'ground'

  return (
    <section className="tile" style={{ flex: 'none' }}>
      <div className="strip">
        <span className="title">Zones</span>
        <span className="as-is" style={{ textTransform: 'none', letterSpacing: 0 }}>local peak density, people/m²</span>
        <button type="button" className="key push" onClick={onScience} title="How these numbers are measured, and the research behind each level">
          <kbd>S</kbd>Science
        </button>
      </div>

      <div role="list">
        {config.zones.map((zone, i) => (
          <ZoneRow
            key={zone.id}
            code={`Z${i + 1}`}
            zone={zone}
            z={live[zone.id]}
            levels={config.levels}
            chosen={zone.id === selected}
            flowAvailable={flowAvailable}
            gates={config.gates.filter((g) => g.zone_id === zone.id).map((g) => ({ name: g.name, g: state?.gates.find((s) => s.id === g.id) }))}
            onSelect={() => onSelect(zone.id)}
          />
        ))}
      </div>

      <div className="legend num">
        {config.levels.map((level, i) => {
          const next = config.levels[i + 1]
          const range = next ? (level.min === 0 ? `<${next.min}` : `${level.min}–${next.min}`) : `≥${level.min}`
          return (
            <span key={level.id} title={`${level.what}\nSource: ${level.source}`}>
              <i className={isAlerting(level.id) ? 'sw' : 'sw hollow'} style={isAlerting(level.id) ? { background: LEVEL_COLOR[level.id] } : undefined} />
              {range} {level.label.toLowerCase()}
            </span>
          )
        })}
      </div>
    </section>
  )
}
