import { useEffect, useState } from 'react'

interface Props {
  label: string
  lang: string // BCP 47 tag, e.g. "en-US"
  text: string
}

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

/** One PA announcement with a button that reads it aloud using the device's own speech engine. */
export function Announcement({ label, lang, text }: Props) {
  const voices = useVoices()
  const [speaking, setSpeaking] = useState(false)
  const prefix = lang.slice(0, 2)
  // Prefer a voice installed on the device, so playback still works with no network.
  const voice = voices.find((v) => v.lang === lang && v.localService) ?? voices.find((v) => v.lang.startsWith(prefix) && v.localService) ?? voices.find((v) => v.lang.startsWith(prefix))

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
    <div className="flex items-start gap-2.5">
      <button
        type="button"
        onClick={toggle}
        disabled={!voice}
        aria-label={speaking ? `Stop the ${label} announcement` : `Play the ${label} announcement`}
        title={voice ? `Read aloud (${voice.name})` : `No ${label} voice is installed on this device`}
        className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-line-strong text-ink transition-colors hover:border-brand/60 hover:bg-brand/10 focus-visible:outline-2 focus-visible:outline-brand disabled:cursor-not-allowed disabled:opacity-35"
      >
        <svg viewBox="0 0 12 12" className="h-2.5 w-2.5" fill="currentColor" aria-hidden>
          {speaking ? <rect x="2" y="2" width="8" height="8" rx="1" /> : <path d="M3 1.5v9l7.5-4.5z" />}
        </svg>
      </button>
      <p className="min-w-0 text-[13px] leading-snug">
        <span className="mr-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted">{label}</span>
        <span className="italic" lang={lang}>“{text}”</span>
      </p>
    </div>
  )
}
