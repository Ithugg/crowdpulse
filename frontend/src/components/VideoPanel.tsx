import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'
import { LEVEL, isAlerting } from '../format'
import type { ConfigMsg, StateMsg } from '../types'

export interface VideoHandle {
  drawFrame: (jpeg: Blob) => void
}

interface Props {
  config: ConfigMsg | null
  state: StateMsg | null
  connected: boolean
  error: string | null
}

/** Live frame on a canvas with the zones drawn on top as vector shapes, so they stay crisp at any size. */
export const VideoPanel = forwardRef<VideoHandle, Props>(function VideoPanel({ config, state, connected, error }, ref) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const boxRef = useRef<HTMLDivElement>(null)
  const busy = useRef(false)
  const [box, setBox] = useState({ w: 0, h: 0 })

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

  useEffect(() => {
    const el = boxRef.current
    if (!el) return
    const observer = new ResizeObserver(([entry]) => {
      setBox({ w: entry.contentRect.width, h: entry.contentRect.height })
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  // Largest rectangle with the frame's aspect ratio that fits the available space.
  const aspect = state ? state.frame.w / state.frame.h : 16 / 9
  const width = Math.max(0, Math.min(box.w, box.h * aspect))
  const height = width / aspect

  const source = config?.sources.find((s) => s.id === config.active_source)
  const live = Object.fromEntries((state?.zones ?? []).map((z) => [z.id, z]))
  const waiting = !state

  return (
    <div ref={boxRef} className="relative flex h-[56vw] max-h-[60vh] shrink-0 items-center justify-center lg:h-auto lg:max-h-none lg:min-h-0 lg:flex-1 lg:shrink">
      <div
        className="relative overflow-hidden rounded-lg border border-line bg-black"
        style={{ width, height }}
      >
        <canvas ref={canvasRef} className="block h-full w-full" />

        {!waiting && config && (
          <>
            <svg className="absolute inset-0 h-full w-full" viewBox="0 0 1 1" preserveAspectRatio="none" aria-hidden>
              {config.zones.map((zone) => {
                const level = live[zone.id]?.level ?? 'normal'
                return (
                  <polygon
                    key={zone.id}
                    points={zone.polygon.map(([x, y]) => `${x},${y}`).join(' ')}
                    fill={LEVEL[level].hex}
                    fillOpacity={!isAlerting(level) ? 0.04 : level === 'caution' ? 0.12 : 0.2}
                    stroke={LEVEL[level].hex}
                    strokeOpacity={0.9}
                    strokeWidth={isAlerting(level) ? 2.5 : 1.5}
                    vectorEffect="non-scaling-stroke"
                    strokeLinejoin="round"
                  />
                )
              })}
              {config.gates.map((gate) => (
                <line
                  key={gate.id}
                  x1={gate.line[0][0]} y1={gate.line[0][1]} x2={gate.line[1][0]} y2={gate.line[1][1]}
                  stroke="#45c4ff" strokeWidth={2} strokeDasharray="7 5" vectorEffect="non-scaling-stroke"
                />
              ))}
            </svg>
            {config.gates.map((gate) => {
              const g = state.gates.find((s) => s.id === gate.id)
              return (
                <div
                  key={gate.id}
                  className="absolute flex -translate-x-1/2 -translate-y-1/2 items-center gap-1.5 rounded border border-brand/50 bg-ground/85 px-1.5 py-0.5 text-[11px] font-medium text-brand backdrop-blur-sm"
                  style={{ left: `${((gate.line[0][0] + gate.line[1][0]) / 2) * 100}%`, top: `${((gate.line[0][1] + gate.line[1][1]) / 2) * 100}%` }}
                  title="People counted crossing this line, averaged over the last minute"
                >
                  <span>{gate.name}</span>
                  {g && <span className="num">{Math.round(g.in_per_min)}/min in</span>}
                </div>
              )
            })}
            {config.zones.map((zone) => {
              const z = live[zone.id]
              const level = z?.level ?? 'normal'
              const x = Math.min(...zone.polygon.map((p) => p[0]))
              const y = Math.min(...zone.polygon.map((p) => p[1]))
              return (
                <div
                  key={zone.id}
                  className={`absolute m-1.5 flex items-center gap-1.5 rounded border bg-ground/85 px-1.5 py-0.5 text-[11px] font-medium backdrop-blur-sm ${LEVEL[level].border}`}
                  style={{ left: `${x * 100}%`, top: `${y * 100}%` }}
                >
                  <span className={`h-1.5 w-1.5 rounded-full ${LEVEL[level].dot}`} />
                  <span>{zone.name}</span>
                  {z && <span className={`num ${LEVEL[level].text}`}>{z.density.toFixed(1)}</span>}
                  {z && z.speed_mps !== null && (
                    <span className="num flex items-center gap-1 border-l border-line-strong pl-1.5 text-muted" title="Average walking speed and direction of travel">
                      {z.heading_deg !== null && (
                        <svg viewBox="0 0 12 12" className="h-2.5 w-2.5 text-ink" style={{ transform: `rotate(${z.heading_deg}deg)` }} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                          <path d="M1.5 6h9M7 2.5 10.5 6 7 9.5" />
                        </svg>
                      )}
                      {z.speed_mps.toFixed(1)} m/s
                    </span>
                  )}
                </div>
              )
            })}

            <div className="absolute bottom-2 left-2 flex items-center gap-2 rounded bg-ground/85 px-2 py-1 text-[11px] backdrop-blur-sm">
              {state.mode === 'live' ? (
                <span className="flex items-center gap-1.5 font-semibold tracking-wide text-crit">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-crit" />
                  LIVE
                </span>
              ) : (
                <span className="font-semibold tracking-wide text-brand" title="Detections replayed from a precomputed cache">
                  REPLAY
                </span>
              )}
              <span className="text-muted">{source?.label}</span>
            </div>
            <div className="num absolute bottom-2 right-2 rounded bg-ground/85 px-2 py-1 text-[11px] text-muted backdrop-blur-sm">
              {state.total_count} in view
            </div>
          </>
        )}

        {waiting && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-sm text-muted">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-line-strong border-t-brand" />
            {connected ? 'Starting camera feed…' : 'Connecting to CrowdPulse server…'}
          </div>
        )}

        {error && (
          <div role="alert" className="animate-rise absolute left-1/2 top-3 -translate-x-1/2 rounded-md border border-crit/50 bg-ground/95 px-3 py-1.5 text-xs text-crit">
            {error}
          </div>
        )}
      </div>
    </div>
  )
})
