import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'
import { LEVEL } from '../format'
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
    <div ref={boxRef} className="relative flex min-h-0 flex-1 items-center justify-center">
      <div
        className="relative overflow-hidden rounded-lg border border-line bg-black"
        style={{ width, height }}
      >
        <canvas ref={canvasRef} className="block h-full w-full" />

        {!waiting && config && (
          <>
            <svg className="absolute inset-0 h-full w-full" viewBox="0 0 1 1" preserveAspectRatio="none" aria-hidden>
              {config.zones.map((zone) => {
                const level = live[zone.id]?.level ?? 'green'
                return (
                  <polygon
                    key={zone.id}
                    points={zone.polygon.map(([x, y]) => `${x},${y}`).join(' ')}
                    fill={LEVEL[level].hex}
                    fillOpacity={level === 'green' ? 0.04 : level === 'yellow' ? 0.12 : 0.2}
                    stroke={LEVEL[level].hex}
                    strokeOpacity={0.9}
                    strokeWidth={level === 'red' ? 2.5 : 1.5}
                    vectorEffect="non-scaling-stroke"
                    strokeLinejoin="round"
                  />
                )
              })}
            </svg>
            {config.zones.map((zone) => {
              const z = live[zone.id]
              const level = z?.level ?? 'green'
              const x = Math.min(...zone.polygon.map((p) => p[0]))
              const y = Math.min(...zone.polygon.map((p) => p[1]))
              return (
                <div
                  key={zone.id}
                  className={`absolute m-1.5 flex items-center gap-1.5 rounded border bg-base/85 px-1.5 py-0.5 text-[11px] font-medium backdrop-blur-sm ${LEVEL[level].border}`}
                  style={{ left: `${x * 100}%`, top: `${y * 100}%` }}
                >
                  <span className={`h-1.5 w-1.5 rounded-full ${LEVEL[level].dot}`} />
                  <span>{zone.name}</span>
                  {z && <span className={`num ${LEVEL[level].text}`}>{z.density.toFixed(1)}</span>}
                </div>
              )
            })}

            <div className="absolute bottom-2 left-2 flex items-center gap-2 rounded bg-base/85 px-2 py-1 text-[11px] backdrop-blur-sm">
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
            <div className="num absolute bottom-2 right-2 rounded bg-base/85 px-2 py-1 text-[11px] text-muted backdrop-blur-sm">
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
          <div role="alert" className="animate-rise absolute left-1/2 top-3 -translate-x-1/2 rounded-md border border-crit/50 bg-base/95 px-3 py-1.5 text-xs text-crit">
            {error}
          </div>
        )}
      </div>
    </div>
  )
})
