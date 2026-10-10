import type { Level } from './types'

interface LevelStyle {
  text: string
  bg: string
  border: string
  dot: string
  hex: string
}

const GREEN: LevelStyle = { text: 'text-ok', bg: 'bg-ok/10', border: 'border-ok/30', dot: 'bg-ok', hex: '#3fd08f' }

export const LEVEL: Record<Level, LevelStyle> = {
  normal: GREEN,
  busy: GREEN,
  caution: { text: 'text-warn', bg: 'bg-warn/10', border: 'border-warn/40', dot: 'bg-warn', hex: '#f6b93b' },
  danger: { text: 'text-danger', bg: 'bg-danger/10', border: 'border-danger/50', dot: 'bg-danger', hex: '#ff8a3d' },
  critical: { text: 'text-crit', bg: 'bg-crit/10', border: 'border-crit/60', dot: 'bg-crit', hex: '#ff4f61' },
}

export const LEVEL_ORDER: Level[] = ['normal', 'busy', 'caution', 'danger', 'critical']

/** True from the safe limit (caution) upwards: the levels staff must act on. */
export function isAlerting(level: Level): boolean {
  return LEVEL_ORDER.indexOf(level) >= 2
}

export function formatEta(seconds: number): string {
  if (seconds < 90) return `${Math.max(10, Math.round(seconds / 10) * 10)} s`
  return `${Math.round(seconds / 60)} min`
}

export function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60)
  return `${m}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`
}

export function formatClock(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString([], { hour12: false })
}
