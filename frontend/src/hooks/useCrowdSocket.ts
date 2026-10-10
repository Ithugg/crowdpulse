import { useCallback, useEffect, useRef, useState } from 'react'
import type { AlertMsg, ClientMsg, ConfigMsg, PlanMsg, ReportMsg, ServerMsg, StateMsg } from '../types'

const MAX_ALERTS = 60

/** One WebSocket: JSON text messages update React state, binary messages are JPEG frames handed to onFrame. */
export function useCrowdSocket(onFrame: (jpeg: Blob) => void) {
  const [connected, setConnected] = useState(false)
  const [config, setConfig] = useState<ConfigMsg | null>(null)
  const [state, setState] = useState<StateMsg | null>(null)
  const [alerts, setAlerts] = useState<AlertMsg[]>([])
  const [plan, setPlan] = useState<PlanMsg | null>(null)
  const [report, setReport] = useState<ReportMsg | null>(null)
  const [error, setError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const onFrameRef = useRef(onFrame)
  onFrameRef.current = onFrame

  useEffect(() => {
    let closed = false
    let retry: ReturnType<typeof setTimeout> | undefined

    const connect = () => {
      const scheme = location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${scheme}://${location.host}/ws`)
      ws.binaryType = 'blob'
      wsRef.current = ws

      let activeSource: string | null = null
      let activeRun = 0
      ws.onopen = () => setConnected(true)
      ws.onclose = () => {
        setConnected(false)
        if (!closed) retry = setTimeout(connect, 1000)
      }
      ws.onmessage = (ev) => {
        if (typeof ev.data !== 'string') {
          onFrameRef.current(ev.data as Blob)
          return
        }
        const msg = JSON.parse(ev.data) as ServerMsg
        switch (msg.type) {
          case 'state':
            setState(msg)
            break
          case 'config':
            // Sent on connect, on every source switch, and when the calibration improves.
            // Only a different camera, a drill started over, or a fresh connection starts with a clean slate.
            setConfig(msg)
            if (msg.active_source !== activeSource || msg.run !== activeRun) {
              activeSource = msg.active_source
              activeRun = msg.run
              setState(null)
              setAlerts([])
              setPlan(null)
            }
            break
          case 'alert':
            setAlerts((prev) => [msg, ...prev].slice(0, MAX_ALERTS))
            break
          case 'alert_update':
            setAlerts((prev) => prev.map((a) => (a.id === msg.id ? { ...a, status: msg.status, ack_s: msg.ack_s, dispatch_s: msg.dispatch_s } : a)))
            break
          case 'plan':
            // While a newer plan for the same zone is being written, the one on screen stays: staff are
            // never left without instructions for the seconds Gemini takes.
            setPlan((shown) =>
              msg.status === 'generating' && shown?.status === 'ready' && shown.zone_id === msg.zone_id ? { ...shown, rewriting: true } : msg,
            )
            break
          case 'report':
            setReport(msg)
            break
          case 'error':
            setError(msg.message)
            break
        }
      }
    }

    connect()
    return () => {
      closed = true
      clearTimeout(retry)
      wsRef.current?.close()
    }
  }, [])

  useEffect(() => {
    if (!error) return
    const t = setTimeout(() => setError(null), 5000)
    return () => clearTimeout(t)
  }, [error])

  const send = useCallback((msg: ClientMsg) => {
    const ws = wsRef.current
    if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify(msg))
  }, [])

  const closeReport = useCallback(() => setReport(null), [])

  return { connected, config, state, alerts, plan, report, closeReport, error, send }
}
