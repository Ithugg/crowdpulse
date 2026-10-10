import { useEffect, useState } from 'react'
import type { PlanMsg } from '../types'

/** Voices load asynchronously in most browsers, so listen for them. */
function useVoices(): SpeechSynthesisVoice[] {
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([])
  useEffect(() => {
    if (!('speechSynthesis' in window)) return
    const load = () => setVoices(window.speechSynthesis.getVoices())
    load()
    window.speechSynthesis.addEventListener('voiceschanged', load)
    return () => window.speechSynthesis.removeEventListener('voiceschanged', load)
  }, [])
  return voices
}

/** One PA announcement with a key that reads it aloud using the computer's own speech engine. */
function Announcement({ label, lang, text }: { label: string; lang: string; text: string }) {
  const voices = useVoices()
  const [speaking, setSpeaking] = useState(false)
  const prefix = lang.slice(0, 2)
  // Prefer a voice installed on the computer, so playback still works with no network.
  const voice =
    voices.find((v) => v.lang === lang && v.localService) ??
    voices.find((v) => v.lang.startsWith(prefix) && v.localService) ??
    voices.find((v) => v.lang.startsWith(prefix))

  useEffect(() => () => window.speechSynthesis?.cancel(), [])

  const toggle = () => {
    window.speechSynthesis.cancel()
    if (speaking || !voice) {
      setSpeaking(false)
      return
    }
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.voice = voice
    utterance.lang = voice.lang
    utterance.rate = 0.95
    utterance.onend = utterance.onerror = () => setSpeaking(false)
    setSpeaking(true)
    window.speechSynthesis.speak(utterance)
  }

  return (
    <>
      <button
        type="button"
        className="key"
        onClick={toggle}
        disabled={!voice}
        aria-label={speaking ? `Stop the ${label} announcement` : `Read the ${label} announcement aloud`}
        title={voice ? `Read aloud (${voice.name})` : `No ${label} voice is installed on this computer`}
      >
        <kbd>
          <svg viewBox="0 0 10 10" width="8" height="8" fill="currentColor" style={{ display: 'inline-block' }} aria-hidden>
            {speaking ? <rect x="1" y="1" width="8" height="8" /> : <path d="M2 0.5v9l7.5-4.5z" />}
          </svg>
        </kbd>
        PA {label}
      </button>
      <p lang={lang}>{text}</p>
    </>
  )
}

interface Props {
  plan: PlanMsg | null
  /** Code of the zone the shown plan is for, e.g. Z4. */
  planCode: string | null
  target: { id: string; code: string; name: string } | null
  onRequest: (zoneId: string) => void
}

/** Staff instructions for one zone, written by Gemini (or the cached plan when Gemini cannot be reached). */
export function ResponsePanel({ plan, planCode, target, onRequest }: Props) {
  return (
    <section className="tile" style={{ flex: 1 }}>
      <div className="strip">
        <span className="title">Response</span>
        {plan && (
          <>
            {planCode && <span className="tag hollow">{planCode}</span>}
            <span>{plan.zone_name}</span>
          </>
        )}
        {plan?.status === 'ready' && (
          <span
            className="tag hollow"
            title={plan.origin === 'gemini' ? `Written by ${plan.model}` : 'Gemini could not be reached, so the pre-written plan is shown'}
          >
            {plan.origin === 'gemini' ? `GEMINI ${((plan.latency_ms ?? 0) / 1000).toFixed(1)} S` : 'CACHED PLAN'}
          </span>
        )}
        {plan?.rewriting && (
          <span className="tag hollow" title="A newer plan for this zone is being written; this one stays until it arrives">
            REWRITING
          </span>
        )}
        <button
          type="button"
          className="key push"
          disabled={!target || plan?.status === 'generating' || plan?.rewriting}
          onClick={() => target && onRequest(target.id)}
        >
          <kbd>P</kbd>
          {plan ? 'Rewrite' : target ? `Plan for ${target.code}` : 'Plan'}
        </button>
      </div>

      <div className="body scroll">
        {!plan && (
          <p className="quiet" style={{ maxWidth: '52ch' }}>
            No plan issued. When a zone crosses the action level of 4 people/m², the instructions for staff appear here: who does what,
            in order, with a PA announcement in English and Spanish.
          </p>
        )}

        {plan?.status === 'generating' && (
          <p className="cursor" aria-busy="true">
            Writing the plan for {plan.zone_name}
          </p>
        )}

        {plan?.status === 'ready' && (
          <>
            <h2 className="headline">{plan.headline}</h2>
            <ol className="steps">
              {plan.actions?.map((action, i) => (
                <li key={i}>
                  <span className="n">{i + 1}</span>
                  <span>
                    <span className="role">{action.role}</span> {action.instruction}
                  </span>
                </li>
              ))}
            </ol>
            {plan.pa_announcement && (
              <div className="pa">
                <Announcement label="EN" lang="en-US" text={plan.pa_announcement} />
                {plan.pa_announcement_es && <Announcement label="ES" lang="es-US" text={plan.pa_announcement_es} />}
              </div>
            )}
          </>
        )}
      </div>
    </section>
  )
}
