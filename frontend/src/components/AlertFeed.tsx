import { LEVEL, formatClock } from '../format'
import type { AlertMsg } from '../types'

const KIND_LABEL: Record<AlertMsg['kind'], string> = {
  level_change: 'Density',
  prediction: 'Forecast',
  exposure: 'Exposure',
  cleared: 'Cleared',
}

interface Props {
  alerts: AlertMsg[]
  onAck: (alertId: string, status: 'acknowledged' | 'dispatched') => void
  onReport: () => void
}

const actionButton =
  'rounded border border-line-strong px-1.5 py-0.5 text-[11px] font-medium text-ink transition-colors hover:border-brand/60 hover:bg-brand/10 focus-visible:outline-2 focus-visible:outline-brand'

/** Staff response to one alert: acknowledge it, then mark staff as dispatched. The server times both. */
function Response({ alert, onAck }: { alert: AlertMsg; onAck: Props['onAck'] }) {
  if (alert.kind === 'cleared') return null
  if (alert.status === 'dispatched') {
    return <span className="text-ok">Staff dispatched after {alert.dispatch_s} s</span>
  }
  return (
    <span className="ml-auto flex items-center gap-1.5">
      {alert.status === 'acknowledged' ? (
        <span className="text-muted">Acknowledged after {alert.ack_s} s</span>
      ) : (
        <button type="button" className={actionButton} onClick={() => onAck(alert.id, 'acknowledged')}>
          Acknowledge
        </button>
      )}
      <button type="button" className={actionButton} onClick={() => onAck(alert.id, 'dispatched')}>
        Dispatch staff
      </button>
    </span>
  )
}

export function AlertFeed({ alerts, onAck, onReport }: Props) {
  const open = alerts.filter((a) => a.kind !== 'cleared' && !a.status).length

  return (
    <section className="flex min-h-0 flex-1 flex-col rounded-lg border border-line bg-panel">
      <header className="flex items-center justify-between gap-2 border-b border-line px-3 py-2">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted">
          Alert feed
          {open > 0 && <span className="num ml-2 normal-case tracking-normal text-warn">{open} open</span>}
        </h2>
        <button type="button" className={actionButton} onClick={onReport} title="Write an incident report for this camera from the alert log">
          Incident report
        </button>
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
                <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-dim">
                  <span className="num">{formatClock(alert.ts)}</span>
                  <span className={alert.kind === 'prediction' ? 'text-warn' : ''}>{KIND_LABEL[alert.kind]}</span>
                  <Response alert={alert} onAck={onAck} />
                </p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
