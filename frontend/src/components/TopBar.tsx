import { useEffect, useState } from 'react'
import { LEVEL } from '../format'
import type { Level, StateMsg } from '../types'

const OVERALL: Record<Level, string> = {
  normal: 'All zones normal',
  busy: 'Busy, monitoring',
  caution: 'Above the safe limit',
  danger: 'Danger: crowd in contact',
  critical: 'Critical density',
}

function Clock() {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])
  return <time className="num text-xs text-muted">{now.toLocaleTimeString([], { hour12: false })}</time>
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-right leading-tight">
      <p className="text-[10px] uppercase tracking-wider text-dim">{label}</p>
      <p className="num text-[13px] font-medium">{value}</p>
    </div>
  )
}

export function TopBar({ state, connected }: { state: StateMsg | null; connected: boolean }) {
  const level = state?.overall_level ?? 'normal'
  const style = LEVEL[level]

  return (
    <header className="flex h-12 shrink-0 items-center gap-4 border-b border-line bg-panel px-4">
      <div className="flex items-center gap-2">
        <svg viewBox="0 0 32 32" className="h-6 w-6" aria-hidden>
          <rect width="32" height="32" rx="7" fill="#101822" />
          <path d="M4 17h6l3-8 5 15 3-9h7" fill="none" stroke="#45c4ff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span className="text-[15px] font-semibold tracking-tight">CrowdPulse</span>
        <span className="hidden text-xs text-dim lg:inline">Crowd safety early warning</span>
      </div>

      <div
        className={`ml-2 flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold transition-colors duration-300 ${style.border} ${style.bg} ${style.text}`}
        role="status"
      >
        <span className={`h-2 w-2 rounded-full ${style.dot} ${level === 'critical' || level === 'danger' ? 'animate-pulse' : ''}`} />
        {state ? OVERALL[level] : 'Waiting for feed'}
      </div>

      <div className="ml-auto flex items-center gap-5">
        <Stat label="People in view" value={state ? String(state.total_count) : '–'} />
        <Stat label="Analysis" value={state ? `${state.fps.toFixed(0)} fps · ${state.mode === 'replay' ? 'replay' : `${state.inference_ms} ms`}` : '–'} />
        <div className="flex items-center gap-1.5 text-xs text-muted">
          <span className={`h-2 w-2 rounded-full ${connected ? 'bg-ok' : 'animate-pulse bg-crit'}`} />
          {connected ? 'Connected' : 'Reconnecting'}
        </div>
        <Clock />
      </div>
    </header>
  )
}
