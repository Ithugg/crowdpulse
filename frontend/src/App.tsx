import { useCallback, useEffect, useMemo, useRef } from 'react'
import { AlertFeed } from './components/AlertFeed'
import { ControlBar } from './components/ControlBar'
import { PlanPanel } from './components/PlanPanel'
import { ScaleLegend } from './components/ScaleLegend'
import { TopBar } from './components/TopBar'
import { VideoPanel, type VideoHandle } from './components/VideoPanel'
import { ZoneCard } from './components/ZoneCard'
import { useCrowdSocket } from './hooks/useCrowdSocket'

export default function App() {
  const video = useRef<VideoHandle>(null)
  const onFrame = useCallback((jpeg: Blob) => video.current?.drawFrame(jpeg), [])
  const { connected, config, state, alerts, plan, error, send } = useCrowdSocket(onFrame)

  const zoneState = useMemo(() => Object.fromEntries((state?.zones ?? []).map((z) => [z.id, z])), [state])

  // The zone a manually requested plan targets: the densest one right now.
  const hottestZone = useMemo(() => {
    if (!config || !state?.zones.length) return null
    const top = [...state.zones].sort((a, b) => b.density - a.density)[0]
    const zone = config.zones.find((z) => z.id === top.id)
    return zone ? { id: zone.id, name: zone.name } : null
  }, [config, state])

  const requestPlan = useCallback((zoneId: string) => send({ type: 'request_plan', zone_id: zoneId }), [send])

  // Demo-mode keyboard shortcuts. Refs keep the handler stable while state updates 15 times a second.
  const latest = useRef({ config, state, hottestZone, plan })
  latest.current = { config, state, hottestZone, plan }
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey || e.repeat) return
      const { config, state, hottestZone, plan } = latest.current
      const key = e.key.toLowerCase()
      if (/^[1-9]$/.test(key)) {
        const source = config?.sources[Number(key) - 1]
        if (source?.available) send({ type: 'set_source', source_id: source.id })
      } else if (key === 'r') {
        send({ type: 'restart' })
      } else if (key === 'b' && state) {
        send({ type: 'set_overlay', boxes: !state.overlay.boxes })
      } else if (key === 'h' && state) {
        send({ type: 'set_overlay', heatmap: !state.overlay.heatmap })
      } else if (key === 'p') {
        const zoneId = plan?.zone_id ?? hottestZone?.id
        if (zoneId) send({ type: 'request_plan', zone_id: zoneId })
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [send])

  return (
    <div className="flex h-full flex-col">
      <TopBar state={state} connected={connected} />

      <main className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_minmax(300px,380px)] gap-3 p-3">
        <div className="flex min-h-0 min-w-0 flex-col gap-3">
          <VideoPanel ref={video} config={config} state={state} connected={connected} error={error} />
          <ControlBar
            config={config}
            state={state}
            onSource={(id) => send({ type: 'set_source', source_id: id })}
            onOverlay={(overlay) => send({ type: 'set_overlay', ...overlay })}
            onRestart={() => send({ type: 'restart' })}
          />
          <div
            className="grid shrink-0 gap-3"
            style={{ gridTemplateColumns: `repeat(${Math.max(config?.zones.length ?? 3, 1)}, minmax(0, 1fr))` }}
          >
            {config?.zones.map((zone) => (
              <ZoneCard key={zone.id} zone={zone} state={zoneState[zone.id]} levels={config.levels} />
            ))}
          </div>
          {config && <ScaleLegend levels={config.levels} calibration={config.calibration} />}
        </div>

        <aside className="flex min-h-0 flex-col gap-3">
          <PlanPanel plan={plan} hottestZone={hottestZone} onRequest={requestPlan} />
          <AlertFeed alerts={alerts} />
        </aside>
      </main>
    </div>
  )
}
