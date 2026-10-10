import { LEVEL, formatClock } from '../format'
import type { AlertMsg } from '../types'

const KIND_LABEL: Record<AlertMsg['kind'], string> = {
  level_change: 'Density',
  prediction: 'Forecast',
  exposure: 'Exposure',
  cleared: 'Cleared',
}

export function AlertFeed({ alerts }: { alerts: AlertMsg[] }) {
  return (
    <section className="flex min-h-0 flex-1 flex-col rounded-lg border border-line bg-panel">
      <header className="flex items-center justify-between border-b border-line px-3 py-2">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted">Alert feed</h2>
        <span className="num text-[11px] text-dim">{alerts.length}</span>
      </header>
      {alerts.length === 0 ? (
        <p className="px-3 py-4 text-xs leading-relaxed text-dim">
          No alerts. Every zone is below the safe limit.
        </p>
      ) : (
        <ol className="scroll-thin min-h-0 flex-1 overflow-y-auto" aria-live="polite">
          {alerts.map((alert) => (
            <li key={`${alert.id}-${alert.ts}`} className="animate-rise flex gap-2.5 border-b border-line/60 px-3 py-2 last:border-b-0">
              <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${LEVEL[alert.level].dot}`} />
              <div className="min-w-0 flex-1">
                <p className="text-[13px] leading-snug">{alert.message}</p>
                <p className="mt-0.5 flex gap-2 text-[11px] text-dim">
                  <span className="num">{formatClock(alert.ts)}</span>
                  <span className={alert.kind === 'prediction' ? 'text-warn' : ''}>{KIND_LABEL[alert.kind]}</span>
                </p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
