import { useCallback, useEffect, useMemo, useRef, type CSSProperties } from 'react'
import { AlertFeed } from './components/AlertFeed'
import { ControlBar, OverlayToggles } from './components/ControlBar'
import { PlanPanel } from './components/PlanPanel'
import { ReportModal } from './components/ReportModal'
import { ScaleLegend } from './components/ScaleLegend'
import { TopBar } from './components/TopBar'
import { VideoPanel, type VideoHandle } from './components/VideoPanel'
import { ZoneCard } from './components/ZoneCard'
import { useCrowdSocket } from './hooks/useCrowdSocket'

export default function App() {
  const video = useRef<VideoHandle>(null)
  const onFrame = useCallback((jpeg: Blob) => video.current?.drawFrame(jpeg), [])
  const { connected, config, state, alerts, plan, report, closeReport, error, send } = useCrowdSocket(onFrame)

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
      } else if (key === 'v' && state) {
        send({ type: 'set_overlay', privacy: !state.overlay.privacy })
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
      <TopBar state={state} connected={connected}>
        <OverlayToggles
          state={state}
          onOverlay={(overlay) => send({ type: 'set_overlay', ...overlay })}
          onRestart={() => send({ type: 'restart' })}
        />
      </TopBar>

      <main className="grid min-h-0 flex-1 grid-cols-1 gap-3 overflow-y-auto p-3 lg:grid-cols-[minmax(0,1fr)_minmax(300px,380px)] lg:overflow-hidden">
        <div className="flex min-w-0 flex-col gap-3 lg:min-h-0">
          <VideoPanel ref={video} config={config} state={state} connected={connected} error={error} />
          <ControlBar config={config} onSource={(id) => send({ type: 'set_source', source_id: id })} />
          <div
            className="grid shrink-0 grid-cols-2 gap-3 lg:[grid-template-columns:repeat(var(--zones),minmax(0,1fr))]"
            style={{ '--zones': Math.max(config?.zones.length ?? 3, 1) } as CSSProperties}
          >
            {config?.zones.map((zone) => (
              <ZoneCard
                key={zone.id}
                zone={zone}
                state={zoneState[zone.id]}
                levels={config.levels}
                flowAvailable={config.flow && config.calibration.mode === 'ground'}
                gates={config.gates.filter((g) => g.zone_id === zone.id)}
                gateState={state?.gates ?? []}
              />
            ))}
          </div>
          {config && <ScaleLegend levels={config.levels} calibration={config.calibration} />}
        </div>

        <aside className="flex flex-col gap-3 lg:min-h-0">
          <PlanPanel plan={plan} hottestZone={hottestZone} onRequest={requestPlan} />
          <AlertFeed
            alerts={alerts}
            onAck={(alertId, status) => send({ type: 'ack_alert', alert_id: alertId, status })}
            onReport={() => send({ type: 'request_report' })}
          />
        </aside>
      </main>

      {report && <ReportModal key={report.id} report={report} onClose={closeReport} />}
    </div>
  )
}
