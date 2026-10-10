import { LEVEL } from '../format'
import type { PlanMsg } from '../types'
import { Announcement } from './Announcement'

interface Props {
  plan: PlanMsg | null
  hottestZone: { id: string; name: string } | null
  onRequest: (zoneId: string) => void
}

function Origin({ plan }: { plan: PlanMsg }) {
  if (plan.status !== 'ready') return null
  if (plan.origin === 'gemini') {
    const seconds = plan.latency_ms ? ` · ${(plan.latency_ms / 1000).toFixed(1)} s` : ''
    return (
      <span className="rounded border border-brand/40 bg-brand/10 px-1.5 py-0.5 text-[11px] font-semibold text-brand" title={plan.model ?? undefined}>
        Gemini{seconds}
      </span>
    )
  }
  return (
    <span className="rounded border border-line-strong px-1.5 py-0.5 text-[11px] font-semibold text-muted" title="Gemini was unreachable, so a pre-written plan is shown">
      Cached plan
    </span>
  )
}

export function PlanPanel({ plan, hottestZone, onRequest }: Props) {
  const target = plan ? { id: plan.zone_id, name: plan.zone_name } : hottestZone

  return (
    <section className="flex flex-col rounded-lg border border-line bg-panel lg:min-h-0 lg:flex-[1.7]">
      <header className="flex items-center justify-between gap-2 border-b border-line px-3 py-2">
        <h2 className="text-[13px] font-semibold">AI response plan</h2>
        {plan && <Origin plan={plan} />}
      </header>

      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-3 py-3">
        {!plan && (
          <p className="text-[13px] leading-relaxed text-muted">
            When a zone crosses the safe limit of 4 people/m², staff instructions appear here automatically: who does
            what, in order, with a PA announcement in English and Spanish.
          </p>
        )}

        {plan?.status === 'generating' && (
          <div aria-busy="true">
            <p className="text-sm text-muted">
              Writing a response plan for <span className="font-semibold text-ink">{plan.zone_name}</span>…
            </p>
            <div className="mt-3 space-y-2.5">
              {[92, 78, 85, 64].map((w) => (
                <div key={w} className="skeleton h-3.5" style={{ width: `${w}%` }} />
              ))}
            </div>
          </div>
        )}

        {plan?.status === 'ready' && (
          <div key={plan.id} className="animate-rise">
            <h3 className="text-base font-semibold leading-snug">{plan.headline}</h3>
            <p className="mt-1 flex items-center gap-1.5 text-xs text-muted">
              <span className={`h-2 w-2 rounded-full ${LEVEL[plan.level].dot}`} />
              {plan.zone_name}
            </p>

            <ol className="mt-3 space-y-2.5">
              {plan.actions?.map((action, i) => (
                <li key={i} className="flex gap-2.5">
                  <span className="num mt-px flex h-5 w-5 shrink-0 items-center justify-center rounded bg-raised text-[11px] font-semibold text-muted">
                    {i + 1}
                  </span>
                  <p className="text-[13px] leading-snug text-muted">
                    <span className="font-semibold text-ink">{action.role}.</span> {action.instruction}
                  </p>
                </li>
              ))}
            </ol>

            {plan.pa_announcement && (
              <div className="mt-3.5 space-y-2 rounded-md border border-line bg-raised px-3 py-2.5">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">PA announcement</p>
                <Announcement label="English" lang="en-US" text={plan.pa_announcement} />
                {plan.pa_announcement_es && <Announcement label="Español" lang="es-US" text={plan.pa_announcement_es} />}
              </div>
            )}
          </div>
        )}
      </div>

      <footer className="border-t border-line px-3 py-2">
        <button
          type="button"
          disabled={!target || plan?.status === 'generating'}
          onClick={() => target && onRequest(target.id)}
          className="btn w-full"
        >
          {plan ? 'Regenerate plan' : target ? `Generate plan for ${target.name}` : 'Generate plan'}
          <kbd>P</kbd>
        </button>
      </footer>
    </section>
  )
}
