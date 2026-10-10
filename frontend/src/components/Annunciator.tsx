import { flowPattern, isAlerting, isOpen, levelLabel, outlook, rank } from '../format'
import type { AlertMsg, ConfigMsg, StateMsg } from '../types'

interface Props {
  config: ConfigMsg | null
  state: StateMsg | null
  alerts: AlertMsg[]
  connected: boolean
  onAck: () => void
  onDispatch: () => void
  onPlan: (zoneId: string) => void
}

/**
 * The one line an operator reads first. Quiet while every zone is below the action level; when a zone
 * crosses it, the band fills with the signal colour and flashes until someone acknowledges.
 */
export function Annunciator({ config, state, alerts, connected, onAck, onDispatch, onPlan }: Props) {
  if (!config || !state) {
    return (
      <div className="annunciator" role="status">
        {connected ? 'WAITING FOR THE CAMERA' : 'CONNECTING TO THE CROWDPULSE SERVER'}
      </div>
    )
  }

  const ranked = state.zones
    .map((z, i) => ({ z, code: `Z${i + 1}`, name: config.zones[i]?.name ?? z.id }))
    .sort((a, b) => rank(b.z.level) - rank(a.z.level) || b.z.density - a.z.density)
  const worst = ranked[0]
  const safeLimit = config.levels.find((l) => l.id === 'caution')?.min ?? 4

  if (!worst || !isAlerting(worst.z.level)) {
    return (
      <div className="annunciator" role="status" data-level="normal">
        <span className="lamp" />
        <span>NO ZONE ABOVE THE ACTION LEVEL OF {safeLimit} /m²</span>
        {worst && (
          <span className="num">
            HIGHEST {worst.code} {worst.name.toUpperCase()} {worst.z.density.toFixed(1)} /m²
          </span>
        )}
      </div>
    )
  }

  const zoneAlerts = alerts.filter((a) => a.zone_id === worst.z.id && a.kind !== 'cleared')
  const open = zoneAlerts.some(isOpen)
  const dispatched = zoneAlerts.length > 0 && zoneAlerts.every((a) => a.status === 'dispatched')
  const flow = worst.z.speed_mps !== null ? `${worst.z.speed_mps.toFixed(1)} m/s ${flowPattern(worst.z)}` : null

  return (
    <div className="annunciator" role="alert" data-alert="true" data-open={open} data-level={worst.z.level}>
      <span>{levelLabel(config.levels, worst.z.level).toUpperCase()}</span>
      <span>
        {worst.code} {worst.name.toUpperCase()}
      </span>
      <span className="num">{worst.z.density.toFixed(1)} /m²</span>
      <span>{outlook(worst.z, config.levels).text}</span>
      {flow && <span>{flow}</span>}
      <span style={{ marginLeft: 'auto', display: 'flex', gap: 14 }}>
        {open && (
          <button type="button" className="key" onClick={onAck}>
            <kbd>A</kbd>Acknowledge
          </button>
        )}
        {!dispatched && (
          <button type="button" className="key" onClick={onDispatch}>
            <kbd>D</kbd>Dispatch staff
          </button>
        )}
        <button type="button" className="key" onClick={() => onPlan(worst.z.id)}>
          <kbd>P</kbd>Plan
        </button>
      </span>
    </div>
  )
}
