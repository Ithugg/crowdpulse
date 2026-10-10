import { useEffect, useRef, type ReactNode } from 'react'
import type { ConfigMsg, ReportMsg } from '../types'

/** A modal document: used where the operator needs to read something in full and nothing else. */
function Sheet({ title, meta, tag, onClose, children, actions, keys }: { title: string; meta?: string; tag?: string; onClose: () => void; children: ReactNode; actions?: ReactNode; keys?: Record<string, () => void> }) {
  const dialog = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const el = dialog.current
    if (el && !el.open) el.showModal()
  }, [])

  return (
    <dialog
      ref={dialog}
      className="sheet"
      onClose={onClose}
      onClick={(e) => e.target === dialog.current && dialog.current?.close()}
      onKeyDown={(e) => {
        // The keycaps shown in the footer are real keys while the sheet is open.
        if (!e.ctrlKey && !e.metaKey && !e.altKey) keys?.[e.key.toLowerCase()]?.()
      }}
    >
      <div className="strip">
        <span className="title">{title}</span>
        {meta && <span className="num as-is">{meta}</span>}
        {tag && <span className="tag hollow push">{tag}</span>}
      </div>
      <div className="body scroll">{children}</div>
      <div className="foot">
        {actions}
        <button type="button" className="key" onClick={() => dialog.current?.close()}>
          <kbd>Esc</kbd>Close
        </button>
      </div>
    </dialog>
  )
}

function reportText(report: ReportMsg): string {
  return [
    report.title ?? 'Incident report',
    `Camera: ${report.camera}   Period: ${report.period.from} to ${report.period.to}`,
    '',
    report.summary ?? '',
    '',
    'Peak readings',
    ...report.zones.map((z) => `- ${z.name}: ${z.peak_density_per_m2} people/m² at ${z.peak_time} (${z.people_at_peak} people)`),
    '',
    'Timeline',
    ...(report.timeline ?? []).map((t) => `- ${t}`),
    '',
    'Recommendations',
    ...(report.recommendations ?? []).map((r) => `- ${r}`),
    '',
    `Written by ${report.origin === 'gemini' ? `Gemini (${report.model})` : 'CrowdPulse from the log (no AI)'}.`,
  ].join('\n')
}

/** Incident report for the current camera, written from the session's log. */
export function ReportSheet({ report, onClose }: { report: ReportMsg; onClose: () => void }) {
  const ready = report.status === 'ready'

  const copy = () => navigator.clipboard?.writeText(reportText(report))
  const save = () => {
    const url = URL.createObjectURL(new Blob([reportText(report)], { type: 'text/plain' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `crowdpulse-report-${report.period.to.replace(/:/g, '')}.txt`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <Sheet
      title="Incident report"
      meta={`${report.camera} · ${report.period.from} to ${report.period.to}`}
      tag={ready ? (report.origin === 'gemini' ? 'GEMINI' : 'FROM THE LOG, NO AI') : undefined}
      onClose={onClose}
      keys={ready ? { c: copy, s: save } : undefined}
      actions={
        ready && (
          <>
            <button type="button" className="key" onClick={copy}>
              <kbd>C</kbd>Copy
            </button>
            <button type="button" className="key" onClick={save}>
              <kbd>S</kbd>Save as text
            </button>
          </>
        )
      }
    >
      {!ready ? (
        <p className="cursor" aria-busy="true">Writing the report from the log</p>
      ) : (
        <>
          <h2>{report.title}</h2>
          <p style={{ marginTop: 6 }}>{report.summary}</p>

          <h3>Peak readings</h3>
          <table>
            <tbody>
              {report.zones.map((z) => (
                <tr key={z.name}>
                  <td>{z.name}</td>
                  <td className="num">{z.peak_density_per_m2.toFixed(1)} /m²</td>
                  <td className="num">{z.people_at_peak} people</td>
                  <td className="num">{z.peak_time}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3>Timeline</h3>
          <ul>
            {report.timeline?.map((entry, i) => (
              <li key={i} className="num">{entry}</li>
            ))}
          </ul>

          <h3>Recommendations</h3>
          <ul style={{ listStyle: 'square', paddingLeft: 16 }}>
            {report.recommendations?.map((entry, i) => <li key={i}>{entry}</li>)}
          </ul>
        </>
      )}
    </Sheet>
  )
}

/** Where every number on the console comes from, and what can be wrong with it. */
export function ScienceSheet({ config, onClose }: { config: ConfigMsg; onClose: () => void }) {
  const cal = config.calibration
  const minutes = Math.round(config.exposure_alert_s / 60)
  const safe = config.levels.find((l) => l.id === 'caution')?.min ?? 4

  return (
    <Sheet title="How CrowdPulse measures a crowd" onClose={onClose}>
      <h2>Density levels and where they come from</h2>
      <table style={{ marginTop: 8 }}>
        <thead>
          <tr>
            <th>Level</th>
            <th>People/m²</th>
            <th>What happens</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {config.levels.map((level, i) => {
            const next = config.levels[i + 1]
            return (
              <tr key={level.id} data-level={level.id}>
                <td style={{ color: 'var(--lv)', fontWeight: 700, whiteSpace: 'nowrap' }}>{level.label}</td>
                <td className="num" style={{ whiteSpace: 'nowrap' }}>{next ? (level.min === 0 ? `under ${next.min}` : `${level.min} to ${next.min}`) : `${level.min} and above`}</td>
                <td>{level.what}</td>
                <td className="quiet">{level.source}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p style={{ marginTop: 8 }}>
        A zone that stays above {safe} people/m² for more than {minutes} minutes raises an exposure alert. The {minutes} minutes
        is a CrowdPulse setting, not a published figure: the longer a crowd stays that dense, the more can go wrong.
      </p>

      <h3>How a reading is made</h3>
      <p>
        <b>People.</b> Each frame is searched for people with a pretrained YOLOv8 detector. No model was trained for this.
      </p>
      <p>
        <b>Scale.</b>{' '}
        {cal.mode === 'ground' ? (
          <>
            The camera calibrates itself. A standing adult is about 1.7 m tall, so how tall people appear at each height in the
            picture gives the camera's height and tilt, and from those the floor position of every person in metres. This camera
            was found to be {cal.cam_height_m} m high, looking {cal.tilt_deg}° down.
          </>
        ) : (
          <>
            On this camera people's feet are not visible, so the floor cannot be calibrated. Each person's distance is taken from
            how wide they appear, assuming shoulders about 0.5 m across. This is rougher than floor calibration.
          </>
        )}{' '}
        The one thing the video cannot tell us is the lens angle, assumed here to be {cal.hfov_deg}°.
      </p>
      <p>
        <b>Local density.</b> Around each person, neighbours are weighted by distance with a Gaussian kernel of radius 1 m, the
        local density measure used by Helbing, Johansson and Al-Abideen in their study of the 2006 Hajj crush. A zone's reading is
        its local peak (the 90th percentile of its people), because an average over a large area hides a dangerous pocket.
      </p>
      <p>
        <b>Movement.</b> On a fixed, calibrated camera people are followed between frames, which gives walking speed in metres
        per second and the direction of travel. Crowd pressure is density × the variance of velocity; Helbing and colleagues
        report turbulence beginning above 0.02 /s².
      </p>

      <h3>What can be wrong</h3>
      <ul style={{ listStyle: 'square', paddingLeft: 16 }}>
        <li>The lens assumption moves a density reading by roughly ±10 to 15%, and a zone's floor area by ±30% or more.</li>
        <li>The detector misses people who are hidden behind others, so readings run low in a packed crowd, exactly when it matters most.</li>
        <li>The forecast is a straight line through the last 30 to 60 seconds. It is an estimate, not a model of the crowd.</li>
        <li>Gate counts follow people with a simple tracker and have not been checked against a hand count.</li>
      </ul>

      <h3>Sources</h3>
      <ul className="quiet">
        <li>J. J. Fruin, Pedestrian Planning and Design.</li>
        <li>G. K. Still, Crowd Dynamics, PhD thesis, University of Warwick.</li>
        <li>Sports Grounds Safety Authority, Guide to Safety at Sports Grounds (the Green Guide).</li>
        <li>D. Helbing, A. Johansson, H. Z. Al-Abideen, The Dynamics of Crowd Disasters: An Empirical Study, Physical Review E 75, 2007.</li>
        <li>D. Helbing, P. Mukerji, Crowd Disasters as Systemic Failures: Analysis of the Love Parade Disaster, EPJ Data Science 1, 2012.</li>
      </ul>
    </Sheet>
  )
}
