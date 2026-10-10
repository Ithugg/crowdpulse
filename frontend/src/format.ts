import type { Level } from './types'

export const LEVEL: Record<Level, { label: string; text: string; bg: string; border: string; dot: string; hex: string }> = {
  green: { label: 'Normal', text: 'text-ok', bg: 'bg-ok/10', border: 'border-ok/30', dot: 'bg-ok', hex: '#3fd08f' },
  yellow: { label: 'Elevated', text: 'text-warn', bg: 'bg-warn/10', border: 'border-warn/40', dot: 'bg-warn', hex: '#f6b93b' },
  red: { label: 'Critical', text: 'text-crit', bg: 'bg-crit/10', border: 'border-crit/60', dot: 'bg-crit', hex: '#ff4f61' },
}

export function formatEta(seconds: number): string {
  if (seconds < 90) return `${Math.max(10, Math.round(seconds / 10) * 10)} s`
  return `${Math.round(seconds / 60)} min`
}

export function formatClock(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString([], { hour12: false })
}
