import type { AlertMsg, Level, LevelInfo, ZoneState } from './types'

export const LEVEL_ORDER: Level[] = ['normal', 'busy', 'caution', 'danger', 'critical']

/** Shown for as long as a drill is on screen: nothing it reads is a measurement of a real place. */
export const DRILL_LABEL = 'DRILL: SIMULATED READINGS'

/** CSS colour for each level. Normal and busy have no colour of their own: colour is reserved for alerts. */
export const LEVEL_COLOR: Record<Level, string> = {
  normal: 'var(--color-ok)',
  busy: 'var(--color-ok)',
  caution: 'var(--color-caution)',
  danger: 'var(--color-danger)',
  critical: 'var(--color-critical)',
}

export function rank(level: Level): number {
  return LEVEL_ORDER.indexOf(level)
}

/** True from the action level (caution) upwards: the levels staff must act on. */
export function isAlerting(level: Level): boolean {
  return rank(level) >= 2
}

export function levelLabel(levels: LevelInfo[], level: Level): string {
  return levels.find((l) => l.id === level)?.label ?? level
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

/** What the zone is doing right now, in one operational phrase. */
export function outlook(z: ZoneState, levels: LevelInfo[]): { text: string; hot: boolean } {
  const safeLimit = levels.find((l) => l.id === 'caution')?.min ?? 4
  if (isAlerting(z.level)) return { text: `above ${safeLimit}/m² for ${formatDuration(z.above_safe_s)}`, hot: true }
  if (z.eta_s !== null && z.eta_level) {
    return { text: `${levelLabel(levels, z.eta_level).toLowerCase()} in ~${formatEta(z.eta_s)}`, hot: true }
  }
  if (z.trend_per_min > 0.3) return { text: `rising ${z.trend_per_min.toFixed(1)}/min`, hot: false }
  if (z.trend_per_min < -0.3) return { text: `easing ${Math.abs(z.trend_per_min).toFixed(1)}/min`, hot: false }
  return { text: 'steady', hot: false }
}

/** How the people in a zone are moving, from the tracker: shared direction, mixed, or against each other. */
export function flowPattern(z: ZoneState): string {
  if (z.speed_mps === null) return ''
  if (z.speed_mps < 0.25) return 'standing'
  const a = z.alignment ?? 0
  return a >= 0.7 ? 'one direction' : a >= 0.4 ? 'mixed directions' : 'counter-flow'
}

/** Alerts staff can still respond to. */
export function isOpen(alert: AlertMsg): boolean {
  return alert.kind !== 'cleared' && !alert.status
}
