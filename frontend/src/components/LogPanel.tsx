import { formatClock, isOpen } from '../format'
import type { AlertMsg, ZoneConfig } from '../types'

interface Props {
  alerts: AlertMsg[]
  zones: ZoneConfig[]
  onAck: (alertId: string, status: 'acknowledged' | 'dispatched') => void
  onReport: () => void
}

/** Every alert on this camera, newest first, with the staff response and how long it took. */
export function LogPanel({ alerts, zones, onAck, onReport }: Props) {
  const open = alerts.filter(isOpen).length
  // The A and D keys act on one alert each; only that row shows the keycap.
  const ackTarget = alerts.find(isOpen)?.id
  const dispatchTarget = alerts.find((a) => a.kind !== 'cleared' && a.status !== 'dispatched')?.id

  return (
    <section className="tile" style={{ flex: '0 0 auto', maxHeight: '30%' }}>
      <div className="strip">
        <span className="title">Log</span>
        <span>{alerts.length === 0 ? 'no alerts' : `${alerts.length} ${alerts.length === 1 ? 'alert' : 'alerts'}, ${open} open`}</span>
        <button type="button" className="key push" onClick={onReport} title="Write the incident report for this camera from the log">
          <kbd>I</kbd>Incident report
        </button>
      </div>

      {alerts.length === 0 ? (
        <p className="body quiet">Nothing logged on this camera. Alerts are listed here with keys to acknowledge them and dispatch staff.</p>
      ) : (
        <ol className="log scroll" aria-live="polite" style={{ flex: 1, minHeight: 0 }}>
          {alerts.map((alert) => {
            const index = zones.findIndex((z) => z.id === alert.zone_id)
            return (
              <li key={`${alert.id}-${alert.ts}`} data-level={alert.level}>
                <span className="when">{formatClock(alert.ts)}</span>
                <i className="lamp" />
                <span className="what" title={alert.message}>
                  {index >= 0 && <span className="tag hollow" style={{ marginRight: 6 }}>Z{index + 1}</span>}
                  {alert.message}
                </span>
                <span className="did">
                  {alert.kind === 'cleared' ? null : alert.status === 'dispatched' ? (
                    <span style={{ color: 'var(--color-ink)' }}>dispatched {alert.dispatch_s} s</span>
                  ) : (
                    <>
                      {alert.status === 'acknowledged' ? (
                        <span>ack {alert.ack_s} s</span>
                      ) : (
                        <button type="button" className="key" onClick={() => onAck(alert.id, 'acknowledged')}>
                          {alert.id === ackTarget && <kbd>A</kbd>}Ack
                        </button>
                      )}
                      <button type="button" className="key" onClick={() => onAck(alert.id, 'dispatched')}>
                        {alert.id === dispatchTarget && <kbd>D</kbd>}Dispatch
                      </button>
                    </>
                  )}
                </span>
              </li>
            )
          })}
        </ol>
      )}
    </section>
  )
}
