import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Annunciator } from './components/Annunciator'
import { CameraPanel, type CameraHandle } from './components/CameraPanel'
import { KeyBar, type Toggle } from './components/KeyBar'
import { LogPanel } from './components/LogPanel'
import { ResponsePanel } from './components/ResponsePanel'
import { ReportSheet, ScienceSheet } from './components/Sheets'
import { StatusLine } from './components/StatusLine'
import { TracePanel } from './components/TracePanel'
import { ZoneBoard } from './components/ZoneBoard'
import { isAlerting, isOpen, rank } from './format'
import { useCrowdSocket } from './hooks/useCrowdSocket'

const STRIP = 24 // height of a tile's title strip
const TRACE_MIN = 132 // the strip chart keeps at least this much height under the camera
const WIDE = 1024 // below this the console becomes one scrolling column

export default function App() {
  const camera = useRef<CameraHandle>(null)
  const commandLine = useRef<HTMLInputElement>(null)
  const onFrame = useCallback((jpeg: Blob) => camera.current?.drawFrame(jpeg), [])
  const { connected, config, state, alerts, plan, report, closeReport, error, send } = useCrowdSocket(onFrame)

  const [selected, setSelected] = useState<string | null>(null)
  const [science, setScience] = useState(false)

  // Space for the camera: the left column's width, and its height less the strip chart's minimum.
  const leftCol = useRef<HTMLDivElement>(null)
  const [space, setSpace] = useState({ width: 0, maxHeight: 0 })
  useEffect(() => {
    const el = leftCol.current
    if (!el) return
    const measure = () => {
      const wide = window.innerWidth >= WIDE
      setSpace({ width: el.clientWidth, maxHeight: wide ? Math.max(120, el.clientHeight - STRIP - TRACE_MIN - STRIP - 2) : Infinity })
    }
    const observer = new ResizeObserver(measure)
    observer.observe(el)
    window.addEventListener('resize', measure)
    return () => {
      observer.disconnect()
      window.removeEventListener('resize', measure)
    }
  }, [])

  // The selected zone: the densest one to begin with, and whichever zone raises an alert after that.
  useEffect(() => {
    if (!config || !state?.zones.length) return
    if (selected && config.zones.some((z) => z.id === selected)) return
    setSelected([...state.zones].sort((a, b) => b.density - a.density)[0].id)
  }, [config, state, selected])

  const newest = alerts[0]
  useEffect(() => {
    if (!newest || newest.kind === 'cleared' || !isAlerting(newest.level)) return
    // A new alert takes the selection only if it is at least as serious as the zone already selected.
    const current = live.current.state?.zones.find((z) => z.id === live.current.target?.id)
    if (!current || rank(newest.level) >= rank(current.level)) setSelected(newest.zone_id)
  }, [newest?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  const target = useMemo(() => {
    const index = config?.zones.findIndex((z) => z.id === selected) ?? -1
    return config && index >= 0 ? { id: config.zones[index].id, code: `Z${index + 1}`, name: config.zones[index].name } : null
  }, [config, selected])

  // ---- actions: the same set is reached from keys, buttons and the command line -----------------
  const live = useRef({ config, state, alerts, target })
  live.current = { config, state, alerts, target }

  const actions = useMemo(() => {
    const source = (n: number) => {
      const s = live.current.config?.sources[n - 1]
      if (!s?.available) return false
      send({ type: 'set_source', source_id: s.id })
      return true
    }
    const zone = (n: number) => {
      const z = live.current.config?.zones[n - 1]
      if (!z) return null
      setSelected(z.id)
      return z.id
    }
    const planFor = (zoneId?: string) => {
      const id = zoneId ?? live.current.target?.id
      if (id) send({ type: 'request_plan', zone_id: id })
    }
    const ack = () => {
      const alert = live.current.alerts.find(isOpen)
      if (alert) send({ type: 'ack_alert', alert_id: alert.id, status: 'acknowledged' })
    }
    const dispatch = () => {
      const alert = live.current.alerts.find((a) => a.kind !== 'cleared' && a.status !== 'dispatched')
      if (alert) send({ type: 'ack_alert', alert_id: alert.id, status: 'dispatched' })
    }
    const toggle = (which: Toggle, value?: boolean) => {
      const overlay = live.current.state?.overlay
      if (overlay) send({ type: 'set_overlay', [which]: value ?? !overlay[which] })
    }
    return {
      source, zone, planFor, ack, dispatch, toggle,
      report: () => send({ type: 'request_report' }),
      reset: () => send({ type: 'restart' }),
      science: () => setScience(true),
    }
  }, [send])

  const runCommand = useCallback(
    (text: string): string | null => {
      const toggles: Record<string, Toggle> = { MARKS: 'boxes', BOXES: 'boxes', HEAT: 'heatmap', GRID: 'grid', PRIVACY: 'privacy' }
      let zoneId: string | undefined
      for (const word of text.trim().toUpperCase().split(/\s+/).filter(Boolean)) {
        const cam = /^C(\d)$/.exec(word)
        const zn = /^Z(\d)$/.exec(word)
        if (cam) {
          if (!actions.source(Number(cam[1]))) return `No camera ${word}`
        } else if (zn) {
          const id = actions.zone(Number(zn[1]))
          if (!id) return `No zone ${word}`
          zoneId = id
        } else if (word === 'PLAN') actions.planFor(zoneId)
        else if (word === 'REPORT') actions.report()
        else if (word === 'ACK') actions.ack()
        else if (word === 'DISPATCH' || word === 'DISP') actions.dispatch()
        else if (word in toggles) actions.toggle(toggles[word])
        else if (word === 'RESET' || word === 'RESTART') actions.reset()
        else if (word === 'SCIENCE' || word === 'HELP') actions.science()
        else return `Unknown: ${word}`
      }
      return null
    },
    [actions],
  )

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey || e.repeat) return
      if (e.target instanceof HTMLInputElement || document.querySelector('dialog[open]')) return
      const key = e.key.toLowerCase()
      if (/^[1-9]$/.test(key)) actions.source(Number(key))
      else if (key === '/') {
        e.preventDefault()
        commandLine.current?.focus()
      } else if (key === 'p') actions.planFor()
      else if (key === 'i') actions.report()
      else if (key === 'a') actions.ack()
      else if (key === 'd') actions.dispatch()
      else if (key === 'b') actions.toggle('boxes')
      else if (key === 'h') actions.toggle('heatmap')
      else if (key === 'g') actions.toggle('grid')
      else if (key === 'v') actions.toggle('privacy')
      else if (key === 'r') actions.reset()
      else if (key === 's') actions.science()
      else if (key === 'arrowdown' || key === 'arrowup') {
        const { config, target } = live.current
        if (!config?.zones.length) return
        e.preventDefault()
        const at = config.zones.findIndex((z) => z.id === target?.id)
        const next = (at + (key === 'arrowdown' ? 1 : -1) + config.zones.length) % config.zones.length
        setSelected(config.zones[next].id)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [actions])

  return (
    <div className="app">
      <StatusLine config={config} state={state} connected={connected} />
      <Annunciator
        config={config}
        state={state}
        alerts={alerts}
        connected={connected}
        onAck={actions.ack}
        onDispatch={actions.dispatch}
        onPlan={actions.planFor}
      />

      <main className="tiles">
        <div className="col" ref={leftCol}>
          <CameraPanel
            ref={camera}
            config={config}
            state={state}
            connected={connected}
            error={error}
            width={space.width}
            maxHeight={space.maxHeight}
            selected={selected}
            onSelect={setSelected}
            onSource={(id) => send({ type: 'set_source', source_id: id })}
          />
          {config && <TracePanel config={config} state={state} selected={selected} />}
        </div>

        <div className="col">
          {config && <ZoneBoard config={config} state={state} selected={selected} onSelect={setSelected} onScience={actions.science} />}
          <ResponsePanel
            plan={plan}
            planCode={plan && config ? `Z${config.zones.findIndex((z) => z.id === plan.zone_id) + 1}` : null}
            target={target}
            onRequest={actions.planFor}
          />
          <LogPanel alerts={alerts} zones={config?.zones ?? []} onAck={(alertId, status) => send({ type: 'ack_alert', alert_id: alertId, status })} onReport={actions.report} />
        </div>
      </main>

      <KeyBar
        ref={commandLine}
        state={state}
        gridAvailable={config?.calibration.mode === 'ground'}
        onToggle={actions.toggle}
        onReset={actions.reset}
        onCommand={runCommand}
      />

      {report && <ReportSheet key={report.id} report={report} onClose={closeReport} />}
      {science && config && <ScienceSheet config={config} onClose={() => setScience(false)} />}
    </div>
  )
}
