import { useEffect, useRef } from 'react'
import type { ReportMsg } from '../types'

function asText(report: ReportMsg): string {
  const lines = [
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
    `Written by ${report.origin === 'gemini' ? `Gemini (${report.model})` : 'CrowdPulse from the alert log (no AI)'}.`,
  ]
  return lines.join('\n')
}

const button =
  'rounded-md border border-line-strong px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:border-brand/60 hover:bg-brand/10 focus-visible:outline-2 focus-visible:outline-brand'

/** Incident report for the current camera, written from the session's alert log. */
export function ReportModal({ report, onClose }: { report: ReportMsg; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const el = dialog.current
    if (el && !el.open) el.showModal()
  }, [])

  const download = () => {
    const url = URL.createObjectURL(new Blob([asText(report)], { type: 'text/plain' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `crowdpulse-report-${report.period.to.replace(/:/g, '')}.txt`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <dialog
      ref={dialog}
      onClose={onClose}
      onClick={(e) => e.target === dialog.current && dialog.current?.close()}
      className="m-auto w-[min(640px,calc(100vw-32px))] rounded-xl border border-line-strong bg-panel p-0 text-ink backdrop:bg-black/60"
    >
      <div className="flex max-h-[min(80vh,720px)] flex-col">
        <header className="flex items-start justify-between gap-3 border-b border-line px-5 py-3.5">
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-muted">
              Incident report · {report.camera} · {report.period.from} to {report.period.to}
            </p>
            <h2 className="mt-0.5 text-base font-semibold leading-snug">
              {report.status === 'ready' ? report.title : 'Writing the report…'}
            </h2>
          </div>
          {report.status === 'ready' && (
            <span className={`shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-semibold ${report.origin === 'gemini' ? 'border-brand/40 bg-brand/10 text-brand' : 'border-line-strong text-muted'}`}>
              {report.origin === 'gemini' ? 'Gemini' : 'From the log, no AI'}
            </span>
          )}
        </header>

        <div className="scroll-thin min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-4 text-[13px] leading-relaxed">
          {report.status === 'generating' ? (
            <div className="space-y-2.5" aria-busy="true">
              {[94, 88, 72, 90, 60].map((w) => (
                <div key={w} className="skeleton h-3.5" style={{ width: `${w}%` }} />
              ))}
            </div>
          ) : (
            <>
              <p>{report.summary}</p>

              <section>
                <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted">Peak readings</h3>
                <table className="mt-1.5 w-full text-left">
                  <tbody>
                    {report.zones.map((z) => (
                      <tr key={z.name} className="border-t border-line/60">
                        <td className="py-1 pr-3">{z.name}</td>
                        <td className="num py-1 pr-3 text-right">{z.peak_density_per_m2.toFixed(1)} people/m²</td>
                        <td className="num py-1 pr-3 text-right text-muted">{z.people_at_peak} people</td>
                        <td className="num py-1 text-right text-muted">{z.peak_time}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>

              <section>
                <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted">Timeline</h3>
                <ul className="mt-1.5 space-y-1">
                  {report.timeline?.map((entry, i) => (
                    <li key={i} className="num text-[12px] text-ink">{entry}</li>
                  ))}
                </ul>
              </section>

              <section>
                <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted">Recommendations</h3>
                <ul className="mt-1.5 list-disc space-y-1 pl-4">
                  {report.recommendations?.map((entry, i) => <li key={i}>{entry}</li>)}
                </ul>
              </section>
            </>
          )}
        </div>

        <footer className="flex justify-end gap-2 border-t border-line px-5 py-3">
          {report.status === 'ready' && (
            <>
              <button type="button" className={button} onClick={() => navigator.clipboard?.writeText(asText(report))}>
                Copy
              </button>
              <button type="button" className={button} onClick={download}>
                Save as text
              </button>
            </>
          )}
          <button type="button" className={button} onClick={() => dialog.current?.close()}>
            Close
          </button>
        </footer>
      </div>
    </dialog>
  )
}
