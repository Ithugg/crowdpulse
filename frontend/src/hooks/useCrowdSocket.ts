import { useCallback, useEffect, useRef, useState } from 'react'
import type { AlertMsg, ClientMsg, ConfigMsg, PlanMsg, ServerMsg, StateMsg } from '../types'

const MAX_ALERTS = 60

/** One WebSocket: JSON text messages update React state, binary messages are JPEG frames handed to onFrame. */
export function useCrowdSocket(onFrame: (jpeg: Blob) => void) {
  const [connected, setConnected] = useState(false)
  const [config, setConfig] = useState<ConfigMsg | null>(null)
  const [state, setState] = useState<StateMsg | null>(null)
  const [alerts, setAlerts] = useState<AlertMsg[]>([])
  const [plan, setPlan] = useState<PlanMsg | null>(null)
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
            // Sent on connect and on every source switch: start that camera with a clean slate.
            setConfig(msg)
            setState(null)
            setAlerts([])
            setPlan(null)
            break
          case 'alert':
            setAlerts((prev) => [msg, ...prev].slice(0, MAX_ALERTS))
            break
          case 'plan':
            setPlan(msg)
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

  return { connected, config, state, alerts, plan, error, send }
}
