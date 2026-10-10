import { useEffect, useState } from 'react'
import { LEVEL_COLOR, isAlerting, rank } from '../format'
import type { ConfigMsg, Level, StateMsg } from '../types'

/** The CrowdPulse mark: five bars that light up to the current overall level, so the logo is also a gauge. */
export function LevelMark({ level }: { level: Level }) {
  const lit = rank(level) + 1
  const colour = isAlerting(level) ? LEVEL_COLOR[level] : 'var(--color-ink)'
  return (
    <svg viewBox="0 0 19 16" width="28" height="23" role="img" aria-label={`Overall level: ${level}`}>
      {[0, 1, 2, 3, 4].map((i) => (
        <rect key={i} x={i * 4} y={12 - i * 3} width="3" height={4 + i * 3} fill={i < lit ? colour : 'var(--color-faint)'} />
      ))}
    </svg>
  )
}

function Clock() {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])
  return <time className="num">{now.toLocaleTimeString([], { hour12: false })}</time>
}

interface Props {
  config: ConfigMsg | null
  state: StateMsg | null
  connected: boolean
}

export function StatusLine({ config, state, connected }: Props) {
  const index = config ? config.sources.findIndex((s) => s.id === config.active_source) : -1
  const source = config?.sources[index]
  const cal = config?.calibration

  return (
    <header className="statusline">
      <div className="cell">
        <LevelMark level={state?.overall_level ?? 'normal'} />
        <span className="wordmark">CROWDPULSE</span>
      </div>
      <div className="cell">
        {source ? (
          <>
            <span className="tag">C{index + 1}</span>
            <span style={{ fontWeight: 700, letterSpacing: '0.05em' }}>{source.label.toUpperCase()}</span>
            {state &&
              (state.mode === 'drill' ? (
                <span className="tag" title="A drill: a scripted crowd on a virtual floor. No reading here is real.">
                  SIMULATED
                </span>
              ) : (
                <span className="tag hollow" title={state.mode === 'replay' ? 'Detections are played back from a precomputed cache' : 'Detections are computed live'}>
                  {state.mode === 'replay' ? 'REPLAY' : 'LIVE'}
                </span>
              ))}
          </>
        ) : (
          <span className="quiet">No camera</span>
        )}
      </div>
      <div className="cell" style={{ flex: 1 }} />
      <div className="cell">
        <span className="k">In view</span>
        <span className="num">{state ? state.total_count : '–'}</span>
      </div>
      <div className="cell" title="Frames analysed per second, and time per detection">
        <span className="k">Rate</span>
        <span className="num">{state ? `${state.fps.toFixed(0)} fps${state.mode === 'live' ? ` ${state.inference_ms} ms` : ''}` : '–'}</span>
      </div>
      {cal && (
        <div
          className="cell"
          title={
            config?.drill
              ? `A virtual camera ${cal.cam_height_m} m up, looking ${cal.tilt_deg}° down at a scripted crowd. Its pose was chosen, not measured.`
              : cal.mode === 'ground'
                ? `The camera calibrated itself from the people in view (average height 1.7 m as the ruler). Lens assumed ${cal.hfov_deg}° wide.`
                : `Feet are not visible, so distance comes from apparent body width (shoulders about 0.5 m). Lens assumed ${cal.hfov_deg}° wide.`
          }
        >
          <span className="k">Scale</span>
          <span className="num">{config?.drill ? 'simulated' : cal.mode === 'ground' ? `auto ${cal.cam_height_m} m ${cal.tilt_deg}°` : 'body size'}</span>
        </div>
      )}
      <div className="cell">
        <span className="lamp" style={{ background: connected ? 'var(--color-ok)' : 'var(--color-caution)' }} />
        <span className="k" style={connected ? undefined : { color: 'var(--color-caution)' }}>{connected ? 'Link' : 'No link'}</span>
      </div>
      <div className="cell">
        <Clock />
      </div>
    </header>
  )
}
