import { forwardRef, useImperativeHandle, useRef } from 'react'
import { LEVEL_COLOR, isAlerting } from '../format'
import type { ConfigMsg, StateMsg } from '../types'

export interface CameraHandle {
  drawFrame: (jpeg: Blob) => void
}

interface Props {
  config: ConfigMsg | null
  state: StateMsg | null
  connected: boolean
  error: string | null
  /** Space the camera may use: the column's width and the height left after the strip chart's minimum. */
  width: number
  maxHeight: number
  selected: string | null
  onSelect: (zoneId: string) => void
  onSource: (sourceId: string) => void
}

/** Rotated arrow for the direction people are moving on screen (0 = right, 90 = down). */
export function Heading({ deg }: { deg: number }) {
  return (
    <svg viewBox="0 0 12 12" width="10" height="10" style={{ display: 'inline-block', transform: `rotate(${deg}deg)`, verticalAlign: '-1px' }} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="square" aria-hidden>
      <path d="M1.5 6h9M7 2.5 10.5 6 7 9.5" />
    </svg>
  )
}

/** The camera: source tabs in the title strip, the frame on a canvas, and the measurement drawn over it. */
export const CameraPanel = forwardRef<CameraHandle, Props>(function CameraPanel(
  { config, state, connected, error, width, maxHeight, selected, onSelect, onSource },
  ref,
) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const busy = useRef(false)

  useImperativeHandle(ref, () => ({
    drawFrame(jpeg: Blob) {
      if (busy.current) return // still decoding the previous frame: drop this one rather than queue up
      busy.current = true
      createImageBitmap(jpeg)
        .then((bitmap) => {
          const canvas = canvasRef.current
          if (canvas) {
            if (canvas.width !== bitmap.width || canvas.height !== bitmap.height) {
              canvas.width = bitmap.width
              canvas.height = bitmap.height
            }
            canvas.getContext('2d')?.drawImage(bitmap, 0, 0)
          }
          bitmap.close()
        })
        .catch(() => {})
        .finally(() => {
          busy.current = false
        })
    },
  }))

  // Largest plate with the frame's aspect ratio that fits the space.
  const aspect = state ? state.frame.w / state.frame.h : 16 / 9
  const plateW = Math.max(0, Math.min(width, maxHeight * aspect))
  const plateH = plateW / aspect
  const live = Object.fromEntries((state?.zones ?? []).map((z) => [z.id, z]))

  return (
    <section className="tile" style={{ flex: 'none' }}>
      <div className="strip" style={{ padding: 0, gap: 0 }}>
        <div className="tabs" role="group" aria-label="Camera source">
          {config?.sources.map((source, i) => (
            <button
              key={source.id}
              type="button"
              className="tab"
              disabled={!source.available}
              aria-pressed={source.id === config.active_source}
              title={source.available ? undefined : 'Video file not found in media/'}
              onClick={() => onSource(source.id)}
            >
              <kbd>{i + 1}</kbd>
              {source.label}
            </button>
          ))}
        </div>
      </div>

      <div className="stage" style={{ height: plateH }}>
        <div className="plate" style={{ width: plateW, height: plateH }}>
          <canvas ref={canvasRef} />

          {state && config && (
            <>
              <svg viewBox="0 0 1 1" preserveAspectRatio="none" aria-hidden>
                {config.zones.map((zone) => {
                  const level = live[zone.id]?.level ?? 'normal'
                  const alerting = isAlerting(level)
                  const chosen = zone.id === selected
                  return (
                    <polygon
                      key={zone.id}
                      points={zone.polygon.map(([x, y]) => `${x},${y}`).join(' ')}
                      fill={alerting ? LEVEL_COLOR[level] : 'none'}
                      fillOpacity={alerting ? 0.16 : 0}
                      stroke={alerting ? LEVEL_COLOR[level] : 'var(--color-ink)'}
                      strokeOpacity={alerting || chosen ? 1 : 0.45}
                      strokeWidth={alerting ? 2 : chosen ? 1.5 : 1}
                      vectorEffect="non-scaling-stroke"
                    />
                  )
                })}
                {config.gates.map((gate) => (
                  <line
                    key={gate.id}
                    x1={gate.line[0][0]} y1={gate.line[0][1]} x2={gate.line[1][0]} y2={gate.line[1][1]}
                    stroke="var(--color-measure)" strokeWidth={1.5} strokeDasharray="6 5" vectorEffect="non-scaling-stroke"
                  />
                ))}
              </svg>

              {config.zones.map((zone, i) => {
                const z = live[zone.id]
                const level = z?.level ?? 'normal'
                return (
                  <button
                    key={zone.id}
                    type="button"
                    className="block"
                    data-level={level}
                    data-alerting={isAlerting(level)}
                    aria-pressed={zone.id === selected}
                    style={{ left: `${Math.min(...zone.polygon.map((p) => p[0])) * 100}%`, top: `${Math.min(...zone.polygon.map((p) => p[1])) * 100}%` }}
                    onClick={() => onSelect(zone.id)}
                  >
                    Z{i + 1} {zone.name.toUpperCase()}
                    {z && (
                      <>
                        <br />
                        {z.density.toFixed(1)}
                        <span className="dim"> /m² </span>
                        {z.count}
                        <span className="dim"> ppl</span>
                        {z.speed_mps !== null && (
                          <>
                            {' '}
                            {z.heading_deg !== null && <Heading deg={z.heading_deg} />} {z.speed_mps.toFixed(1)}
                            <span className="dim"> m/s</span>
                          </>
                        )}
                      </>
                    )}
                  </button>
                )
              })}

              {config.gates.map((gate) => {
                const g = state.gates.find((s) => s.id === gate.id)
                return (
                  <span
                    key={gate.id}
                    className="block gate"
                    style={{ left: `${((gate.line[0][0] + gate.line[1][0]) / 2) * 100}%`, top: `${((gate.line[0][1] + gate.line[1][1]) / 2) * 100}%` }}
                    title="People counted crossing this line, averaged over the last minute"
                  >
                    {gate.name.toUpperCase()}
                    {g && ` ${Math.round(g.in_per_min)}/min in`}
                  </span>
                )
              })}

              <span className="hud" style={{ right: 6 }}>
                {state.total_count} in view
              </span>
            </>
          )}

          <i className="reg tl" />
          <i className="reg tr" />
          <i className="reg bl" />
          <i className="reg br" />

          {!state && (
            <p className="quiet cursor" style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              {connected ? 'Starting the camera' : 'Connecting to the CrowdPulse server'}
            </p>
          )}

          {error && (
            <p role="alert" className="block" style={{ left: '50%', top: 8, transform: 'translateX(-50%)', boxShadow: 'inset 0 0 0 1px var(--color-caution)', color: 'var(--color-caution)' }}>
              {error}
            </p>
          )}
        </div>
      </div>
    </section>
  )
})
